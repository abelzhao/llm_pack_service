from enum import Enum
from typing import List, Dict
from fastapi import APIRouter
import httpx
import json
import logging

from ..utils import Provider, Token  # Import from parent module

router = APIRouter(prefix="/nonstream", tags=["非流式APIs"])

@router.post("/chat", response_model=None)
async def chat(messages: List[Dict], provider: Provider):
    """对外提供大模型聊天服务

    Args:
        messages (List[Dict]): 聊天的消息结构体
        provider (str): 大模型提供商
    Returns:
        返回单个响应 (Dict)
    例如:
        {
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"}
            ],
            "provider": "deepseek"
        }
    返回:
        {
            "role": "assistant",
            "content": "Hello! How can I assist you today? 😊"
        }

    """
    if provider == Provider.DEEPSEEK.value:
        url = "https://api.deepseek.com/chat/completions"
        headers = {
            "Content-Type": "application/json",
            'Accept': 'application/json',
            "Authorization": f"Bearer {Token.DEEPSEEK.value}"
        }
        model = "deepseek-chat"
        # Log messages and provider
        print(f"Messages: {messages}, Provider: {provider}")
        data = {
            "model": model,
            "messages": messages,
            "stream": False  # Set stream to false for non-streaming response
        }
        print(f"Request data: {data}")
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as client:
            response = await client.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()['choices'][0]['message']
        
    elif provider == Provider.DOUBAO.value:
        url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
        headers = {
            "Content-Type": "application/json",
            'Accept': 'application/json',
            "Authorization": f"Bearer {Token.DOUBAO.value}"
        }
        model = "doubao-1.5-pro-32k-250115"
        data = {
            "model": model,
            "messages": messages,
            "stream": False  # Set stream to false for non-streaming response
        }
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as client:
            response = await client.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()['choices'][0]['message']
        
    else:
        raise ValueError(f"Unsupported provider: {provider}. Supported providers are: {', '.join(p.value for p in Provider)}.")
