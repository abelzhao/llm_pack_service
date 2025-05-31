from enum import Enum
from typing import List, Dict, Union, AsyncGenerator
from fastapi import APIRouter
from fastapi.responses import StreamingResponse, Response
import httpx
import json
import logging
from fastapi import HTTPException
import ast

from .utils import Provider, Token, Url, Model  # Import from parent module

JSON_MEDIA_TYPE = "application/json"


router = APIRouter(prefix="/api/v1", tags=["对话"])

def trans_chunk(chunk: str) -> Union[Dict, str]:
    """转换chunk为字符串"""
    try:
        if not chunk.strip():
            return ""
        if chunk.strip() == "data: [DONE]":
            return {"isDone":True}
        if chunk.startswith("data: "):
            chunk = chunk[6:]
        chunk_data = json.loads(chunk)
        if 'choices' in chunk_data and chunk_data['choices']:
            delta = chunk_data['choices'][0].get('delta', {})
            return delta
        else:
            logging.warning(f"Unexpected chunk format: {chunk_data}")
            return ""
    except json.JSONDecodeError as e:
        logging.warning(f"Failed to parse chunk: {chunk}, error: {e}")
        return ""

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
            async for chunk in response.aiter_lines():
                new_chunk = trans_chunk(chunk)
                if new_chunk:
                    role = new_chunk.get("role", role)
                    new_chunk["role"] = role
                    yield json.dumps(new_chunk)

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
    
def get_error_response(message: str) -> Response:
    """生成错误响应"""
    json_data = {
        "code": 0,
        "msg": message,
        "data": {},
        "status": 404
    }
    return Response(
        json.dumps(json_data),
        status_code=200,
        media_type=JSON_MEDIA_TYPE
    )

@router.post("/chat", response_model=None)
async def chat(messages: List[Dict], provider: str, stream: bool, model: str, reason:bool) -> Union[StreamingResponse, Response]:
    """对外提供大模型聊天服务
    Args:
        messages (List[Dict]): 聊天的消息结构体
        provider (str): 大模型提供商
        model str: 模型名称
        stream bool: 是否流式返回
        reason bool: 是否做推理
        
    Returns:
        要么StreamingResponse，要么Response
        
    """
    if provider == Provider.DEEPSEEK.value:
        url = Url.DEEPSEEK.value
        token = Token.DEEPSEEK.value
        if model not in ast.literal_eval(Model.DEEPSEEK.value):
            return get_error_response(f"模型 {model} 不在 DeepSeek 支持的模型列表中: {Model.DEEPSEEK.value}")
    elif provider == Provider.DOUBAO.value:
        url = Url.DOUBAO.value
        token = Token.DOUBAO.value
        if model not in ast.literal_eval(Model.DOUBAO.value):
            return get_error_response(f"模型 {model} 不在 DouBao 支持的模型列表中: {Model.DOUBAO.value}")
    else:
        return get_error_response(f"不支持的提供商: {provider}")
        
    headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
    
    data = {
            "model": model,
            "messages": messages,
            "stream": stream
        }
    
    logging.info(f"Request data:\n{data}\n")
    
    if (provider == Provider.DEEPSEEK.value and reason and "reasoner" not in model) or \
        (provider == Provider.DOUBAO.value and reason and "r1" not in model):
        json_data = {
            "code": 0,
            "msg": f"{model} 不支持推理模式",
            "data": {},
            "status": 404
        }
        return Response(
            json.dumps(json_data),
            status_code=200,
            media_type=JSON_MEDIA_TYPE
        )
    
    if (provider == Provider.DEEPSEEK.value and not reason and "reasoner" in model) or \
        (provider == Provider.DOUBAO.value and not reason and "r1" in model):
        json_data = {
            "code": 0,
            "msg": f"{model} 支持了推理模式",
            "data": {},
            "status": 404
        }
        return Response(
            json.dumps(json_data),
            status_code=200,
            media_type=JSON_MEDIA_TYPE
        )
    
    if stream:
        try:
            return StreamingResponse(
                stream_generator(url, headers, data),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no",  # 禁用Nginx缓冲
                    "Connection": "keep-alive",
                    "Transfer-Encoding": "chunked"
                }
            )
        except Exception as e:
            get_error_response(f"Streaming error: {e}")
    else:
        try:
            data = await nonstream_generator(url, headers, data)
            json_data = {
                "code": 1,
                "msg": "success",
                "data": data,
                "status": 200
            }
            return Response(
                json.dumps(json_data),
                status_code=200,
                media_type=JSON_MEDIA_TYPE
            )
        except Exception as e:
            get_error_response(f"Non-streaming error: {e}")
            

@router.get("/chat_model_list") 
async def chat_model_list() -> Response:
    """获取模型列表"""
    return Response(
        json.dumps({
            "code": 1,
            "msg": "success",
            "data": {
                "deepseek": Model.DEEPSEEK.value,
                "doubao": Model.DOUBAO.value
            },
            "status": 200
        }),
        status_code=200,
        media_type=JSON_MEDIA_TYPE
    )
