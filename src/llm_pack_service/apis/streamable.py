from enum import Enum
from typing import List, Dict
from fastapi import APIRouter
from fastapi.responses import StreamingResponse, Response
import httpx
import json
import logging
from fastapi import HTTPException

from .utils import Provider, Token  # Import from parent module

DONE_MARKER = "[DONE]"

router = APIRouter(prefix="/streamable", tags=["流式APIs"])

@router.post("/chat")
async def chat(messages: List[Dict], model:str, reason:bool, provider: Provider) -> StreamingResponse:
    """对外提供大模型聊天服务

    Args:
        messages (List[Dict]): 聊天的消息结构体
        mode str: 聊天的消息结构体
        reason bool: 聊天的消息结构体
        provider (str): 大模型提供商
    Returns:
        返回list响应 (AsyncGenerator[Dict, None])
    例如:
        {
            "messages": [
                {"role": "system", "content": "你的角色是产品经理"},
                {"role": "user", "content": "请自我介绍下"}
            ],
            "provider": "deepseek"
        }
    返回:
        

    """
    
    # Log messages and provider
    logging.info(f"Messages: {messages}, Provider: {provider}")
    
    return StreamingResponse(
        chat_generator(messages, model, reason, provider),
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
        if not chunk.strip():
            return ""
        if chunk.strip() == f"data: {DONE_MARKER}":
            return f"{DONE_MARKER}"
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

async def chat_generator(messages: List[Dict], model:str, reason:bool, provider: Provider):
    if provider == Provider.DEEPSEEK.value:
        url = "https://api.deepseek.com/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Token.DEEPSEEK.value}"
        }
        # model = "deepseek-chat"
        data = {
            "model": model,
            "messages": messages,
            "stream": True
        }
        logging.info(f"Request data:\n{data}\n")
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as client:
            try:
                async with client.stream("POST", url, headers=headers, json=data) as response:
                    response.raise_for_status()
                    async for chunk in response.aiter_lines():
                        new_chunk = trans_chunk(chunk)
                        if new_chunk:
                            logging.info("new chunk:\n"+new_chunk)
                            yield new_chunk
            except Exception as e:
                logging.error(f"未知错误: {e}")
                yield f"{DONE_MARKER}"
        
    elif provider == Provider.DOUBAO.value:
        url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Token.DOUBAO.value}"
        }
        # model = "deepseek-r1-250120"
        data = {
            "model": model,
            "messages": messages,
            "stream": True
        }
        logging.info(f"Request data:\n{data}\n")
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as client:
            try:
                async with client.stream("POST", url, headers=headers, json=data) as response:
                    response.raise_for_status()
                    async for chunk in response.aiter_lines():
                        new_chunk = trans_chunk(chunk)
                        if new_chunk:
                            logging.info("new chunk:\n"+new_chunk)
                            yield new_chunk
            except Exception as e:
                logging.error(f"未知错误: {e}")
                yield f"{DONE_MARKER}"
        
    else:
        raise ValueError(f"Unsupported provider: {provider}. Supported providers are: {', '.join(p.value for p in Provider)}.")
