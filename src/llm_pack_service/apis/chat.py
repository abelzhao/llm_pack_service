from enum import Enum
from typing import List, Dict, Union, AsyncGenerator, Optional, Tuple
import fastapi
from fastapi.responses import StreamingResponse, Response
from fastapi import HTTPException, APIRouter
from fastapi import UploadFile, File, Form
from pydantic import BaseModel
import httpx
import json
import logging
import ast
from .utils import Model, Provider, Token, Url
from .error import get_error_response
import tempfile
import configparser

router = APIRouter(prefix="/api/v1", tags=["对话"])

JSON_MEDIA_TYPE = "application/json"

config = configparser.ConfigParser()
config.read("model_config.ini")
print(f"Config loaded: {config.sections()}")


def trans_chunk(chunk: str) -> Tuple:
    """转换chunk为字符串"""
    try:
        if not chunk.strip():
            return "", "empty"
        if chunk.strip() == "data: [DONE]":
            return {"isDone": "True"}, "end"
        if chunk.startswith("data: "):
            chunk = chunk[6:]
        chunk_data = json.loads(chunk)
        chunk_short = {}
        if len(chunk_data['choices'])>0:
            chunk_short = chunk_data['choices'][0].get('delta', {})
            chunk_short["usage"] = chunk_data["usage"]    
            return chunk_short, "content"
        else:
            return "", "empty"
    except json.JSONDecodeError as e:
        logging.warning(f"Failed to parse chunk: {chunk}, error: {e}")
        return "", "empty"

async def stream_generator(url: str, headers: Dict, data: Dict) -> AsyncGenerator[str, None]:
    """流生成器

    Args:
        url (str): 模型地址
        headers (Dict): 请求头
        data (Dict): 请求数据

    Yields:
        str: streaming response in JSON format
    """
    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as client:
        async with client.stream("POST", url, headers=headers, json=data) as response:
            response.raise_for_status()
            role = ""
            _token_num = 0
            async for chunk in response.aiter_lines():
                new_chunk, _position = trans_chunk(chunk)
                if new_chunk:
                    role = new_chunk.get("role", role)
                    new_chunk["role"] = role
                    yield "data: " + json.dumps(new_chunk, ensure_ascii=False)+"\n\n"

async def nonstream_generator(url: str, headers: Dict, data: Dict) -> Dict:
    """非流生成器

    Args:
        url (str): 模型地址
        headers (Dict): 请求头
        data (Dict): 请求数据

    Returns:
        Dict: 封装的json回答

    """
    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as client:
        response = await client.post(url, headers=headers, json=data)
        response.raise_for_status()
        data = response.json()['choices'][0]['message']
        return data

class ChatMessage(BaseModel):
    role: str
    content: str
    
class ReqJson(BaseModel):
    """纯文本的请求体"""
    messages: List[ChatMessage]
    files: List[str] = []
    
ModelSection = Enum("ModelSection", {section.upper():section.lower() for section in config.sections()})
Thinking = Enum("Thinking", {"enabled": "enabled", "disabled": "disabled", "auto": "auto"})

def _build_messages(_messages: List[Dict], _files: List[str], model: str) -> List[Dict]:
    """Construct the messages list with file handling if needed"""
    if config[model]["multi_modal"] != "true" or not _files or not _messages:
        return _messages
        
    if _messages[-1]["role"] != "user":
        raise ValueError(f"模型 {model} 多模态输入时，最后一条消息必须是用户消息")
        
    _last_message_content = [
        {
            "image_url": {"url": url},
            "type": "image_url"
        } for url in _files
    ]
    _last_message_content.append({
        "text": _messages[-1]["content"],
        "type": "text"
    })
    return _messages[:-1] + [{
        "role": "user",
        "content": _last_message_content
    }]

async def handle_stream_response(url: str, headers: Dict, data: Dict) -> StreamingResponse:
    """Handle streaming response generation"""
    return StreamingResponse(
        stream_generator(url, headers, data),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
            "Transfer-Encoding": "chunked"
        }
    )

async def handle_nonstream_response(url: str, headers: Dict, data: Dict) -> Response:
    """Handle non-streaming response generation"""
    data = await nonstream_generator(url, headers, data)
    return Response(
        json.dumps({
            "code": 1,
            "msg": "success",
            "data": data,
            "status": 200
        }),
        status_code=200,
        media_type=JSON_MEDIA_TYPE
    )

@router.post("/chat", response_model=None)
async def chat(req_json: ReqJson,
                model: ModelSection,
                stream: bool = True,
                thinking: Optional[Thinking] = None,
                max_tokens: int = 4096
            ) -> Union[StreamingResponse, Response]:
    """对外提供大模型聊天服务"""
    try:
        req_dict = req_json.dict()
        _messages = req_dict.get("messages", [])
        _files = req_dict.get("files", [])
        logging.debug(f"Received messages: {_messages}")
        logging.debug(f"Received files: {_files}")
    except Exception as e:
        return get_error_response(f"请求格式错误，请检查输入数据：{e}")

    model_name = model.value.lower()
    if model_name not in config.sections():
        return get_error_response(f"模型 {model_name} 不在 DouBao 支持的模型列表中: {config.sections()}")

    if config[model_name]["multi_modal"] == "false" and _files:
        return get_error_response(f"模型 {model_name} 不支持多模态输入，请换一个模型：{config.sections()}")

    try:
        messages = _build_messages(_messages, _files, model_name)
    except ValueError as e:
        return get_error_response(str(e))

    thinking_obj = {
        "type": thinking.value,
    } if config[model_name]["thinking"] == "true" else None

    max_tokens = min(max_tokens, 16000)
    
    data = {
        "model": "-".join([model_name, config[model_name]["version"]]),
        "messages": messages,
        "stream": stream,
        "thinking": thinking_obj,
        "max_tokens": max_tokens
    }
    
    if stream:
        data.update({
            "stream_options": {
                "include_usage": True,
                "chunk_include_usage": True
            }
        })
    
    logging.debug(f"Request data:\n {data}\n")
    
    url = Url.DOUBAO.value
    token = Token.DOUBAO.value
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    try:
        if stream:
            return await handle_stream_response(url, headers, data)
        return await handle_nonstream_response(url, headers, data)
    except Exception as e:
        return get_error_response(f"Error processing request: {e}")
            

@router.get("/chat_model_list") 
async def chat_model_list() -> Response:
    """获取模型列表"""
    return Response(
        json.dumps({
            "code": 1,
            "msg": "success",
            "data": {section: dict(config[section]) for section in config.sections()},
            "status": 200
        }),
        status_code=200,
        media_type=JSON_MEDIA_TYPE
    )
