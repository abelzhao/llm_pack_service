from enum import Enum
from typing import List, Dict
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import httpx
import json
import logging
from fastapi import HTTPException

from .utils import Provider, Token  # Import from parent module

router = APIRouter(prefix="/streamable", tags=["流式APIs"])

@router.post("/chat")
async def chat(messages: List[Dict], provider: Provider):
    """对外提供大模型聊天服务

    Args:
        messages (List[Dict]): 聊天的消息结构体
        provider (str): 大模型提供商
    Returns:
        返回list响应 (AsyncGenerator[Dict, None])
    例如:
        {
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"}
            ],
            "provider": "deepseek"
        }
    返回:
        

    """
    
    # Log messages and provider
    logging.info(f"Messages: {messages}, Provider: {provider}")
    
    return StreamingResponse(
        chat_generator(messages, provider),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # 禁用Nginx缓冲
            "Connection": "keep-alive",
            "Transfer-Encoding": "chunked"
        }
    )
    
def trans_chunk(chunk: str) -> str:
    """转换chunk为字符串"""
    try:
        if not chunk.strip() or chunk.strip() == "data: [DONE]":
            return ""
        if chunk.startswith("data: "):
            chunk = chunk[6:]
        chunk_data = json.loads(chunk)
        if 'choices' in chunk_data and chunk_data['choices']:
            delta = chunk_data['choices'][0].get('delta', {})
            return f"data: {json.dumps(delta, ensure_ascii=False)}\n\n"
        else:
            logging.warning(f"Unexpected chunk format: {chunk_data}")
            return ""
    except json.JSONDecodeError as e:
        logging.warning(f"Failed to parse chunk: {chunk}, error: {e}")
        return ""

async def chat_generator(messages: List[Dict], provider: Provider):
    if provider == Provider.DEEPSEEK.value:
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Token.DEEPSEEK.value}"
        }
        model = "deepseek-chat"
        data = {
            "model": model,
            "messages": messages,
            "stream": True
        }
        logging.info(f"Request data:\n{data}\n")
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as client:
            try:
                async with client.stream("POST", url, json=data) as response:
                    response.raise_for_status()
                    async for chunk in response.aiter_lines():
                        new_chunk = trans_chunk(chunk)
                        if new_chunk:
                            logging.info("new chunk:\n"+new_chunk)
                            yield new_chunk
            except httpx.ReadTimeout:
                logging.error("请求超时，请重试")
                yield f"data: [Done]\n\n"
            except httpx.RequestError as e:
                logging.error(f"网络错误: {e}")
                yield f"data: [Done]\n\n"
        
    elif provider == Provider.DOUBAO.value:
        url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
        headers = {
            "Content-Type": "application/json",
            'Accept': 'application/json',
            "Authorization": f"Bearer {Token.DOUBAO.value}"
        }
        model = "Doubao-1.5-pro-32k-250115"
        data = {
            "model": model,
            "messages": messages,
            "stream": True  # Set stream to true for streaming response
        }
        # logging.info(f"Request data: {data}")
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as client:
            response = await client.post(url, headers=headers, json=data)
            # response.raise_for_status()
            async for chunk in response.aiter_raw():
                yield chunk
        
    else:
        raise ValueError(f"Unsupported provider: {provider}. Supported providers are: {', '.join(p.value for p in Provider)}.")
