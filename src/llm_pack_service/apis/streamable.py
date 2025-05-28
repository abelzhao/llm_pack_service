from enum import Enum
from typing import List, Dict
from fastapi import APIRouter
from starlette.responses import StreamingResponse
import httpx
import json
import logging

from ..utils import Provider, Token  # Import from parent module

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
    print(f"Messages: {messages}, Provider: {provider}")
    
    return StreamingResponse(
        chat_generator(messages, provider),
        media_type="application/json"
    )

async def chat_generator(messages: List[Dict], provider: Provider):
    if provider == Provider.DEEPSEEK.value:
        url = "https://api.deepseek.com/chat/completions"
        headers = {
            "Content-Type": "application/json",
            'Accept': 'application/json',
            "Authorization": f"Bearer {Token.DEEPSEEK.value}"
        }
        model = "deepseek-chat"
        data = {
            "model": model,
            "messages": messages,
            "stream": True  # Set stream to true for streaming response
        }
        print(f"Request data: {data}")
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as client:
            response = await client.post(url, headers=headers, json=data)
            response.raise_for_status()
            async for chunk in response.aiter_lines():
                if not chunk.strip() or not chunk.startswith('data:'):
                    continue
                chunk_content = chunk.strip().removeprefix('data: ')
                if chunk_content == "[DONE]":
                    break
                try:
                    chunk_data = json.loads(chunk_content)
                    if 'choices' in chunk_data and chunk_data['choices']:
                        delta = chunk_data['choices'][0].get('delta', {})
                        logging.info(f"delta: {delta}\n")
                        yield json.dumps(delta, ensure_ascii=False)+"\n"
                    else:
                        logging.warning(f"Unexpected chunk format: {chunk_data}")
                except json.JSONDecodeError as e:
                    logging.warning(f"Failed to parse chunk: {chunk}, error: {e}")
                    continue
        
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
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as client:
            response = await client.post(url, headers=headers, json=data)
            response.raise_for_status()
            async for chunk in response.aiter_lines():
                if not chunk.strip() or not chunk.startswith('data:'):
                    continue
                chunk_content = chunk.strip().removeprefix('data: ')
                if chunk_content == "[DONE]":
                    break
                try:
                    chunk_data = json.loads(chunk_content)
                    if 'choices' in chunk_data and chunk_data['choices']:
                        delta = chunk_data['choices'][0].get('delta', {})
                        logging.info(f"delta: {delta}\n")
                        yield json.dumps(delta, ensure_ascii=False)+"\n"
                    else:
                        logging.warning(f"Unexpected chunk format: {chunk_data}")
                except json.JSONDecodeError as e:
                    logging.warning(f"Failed to parse chunk: {chunk}, error: {e}")
                    continue
        
    else:
        raise ValueError(f"Unsupported provider: {provider}. Supported providers are: {', '.join(p.value for p in Provider)}.")
