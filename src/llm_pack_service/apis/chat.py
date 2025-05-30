from enum import Enum
from typing import List, Dict, Union
from fastapi import APIRouter
from fastapi.responses import StreamingResponse, Response
import httpx
import json
import logging
from fastapi import HTTPException

from .utils import Provider, Token  # Import from parent module

DONE_MARKER = "[DONE]"

router = APIRouter(prefix="/api/v1", tags=["对话"])

def trans_chunk(chunk: str) -> str:
    """转换chunk为字符串"""
    try:
        if not chunk.strip():
            return ""
        if chunk.strip() == f"data: {DONE_MARKER}":
            return json.dumps({"isDone":True})
        if chunk.startswith("data: "):
            chunk = chunk[6:]
        chunk_data = json.loads(chunk)
        if 'choices' in chunk_data and chunk_data['choices']:
            delta = chunk_data['choices'][0].get('delta', {})
            return f"{json.dumps(delta, ensure_ascii=False)}\n\n"
        else:
            logging.warning(f"Unexpected chunk format: {chunk_data}")
            return ""
    except json.JSONDecodeError as e:
        logging.warning(f"Failed to parse chunk: {chunk}, error: {e}")
        return ""
    
async def stream_generator(url: str, headers: Dict, data: Dict):
    """流生成器

    Args:
        url (str): 模型地址
        headers (Dict): 请求头
        data (Dict): 请求数据

    Returns:
        _type_: _description_

    Yields:
        _type_: _description_
    """
    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as client:
        async with client.stream("POST", url, headers=headers, json=data) as response:
            response.raise_for_status()
            async for chunk in response.aiter_lines():
                new_chunk = trans_chunk(chunk)
                if new_chunk:
                    yield new_chunk
                    
async def nonstream_generator(url: str, headers: Dict, data: Dict):
    """非流生成器

    Args:
        url (str): 模型地址
        headers (Dict): 请求头
        data (Dict): 请求数据

    Returns:
        _type_: _description_

    Yields:
        _type_: _description_
    """
    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as client:
        response = await client.post(url, headers=headers, json=data)
        # async with client.post(url, headers=headers, json=data) as response:
        response.raise_for_status()
        data = response.json()['choices'][0]['message']
        return data

@router.post("/chat", response_model=None)
async def chat(messages: List[Dict], provider: Provider, stream: bool, model: str, reason:bool) -> Union[StreamingResponse, Response]:
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
        url = "https://api.deepseek.com/chat/completions"
        token = Token.DEEPSEEK.value
    elif provider == Provider.DOUBAO.value:
        url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
        token = Token.DOUBAO.value
        
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
    
    if stream:
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
    else:
        try:
            data = await nonstream_generator(url, headers, data)
            json_data = {
                "code": 1,
                "msg": "success",
                "data": data,
                "status":200
            }
            return Response(
                json.dumps(json_data),
                status_code=200,
                media_type='application/json'
            )
            
        except Exception as e:
            return Response(
                f"获取数据失败: {e}",
                status_code=404,
                media_type='application/json'
            )
    
    
    

        
        
    
    