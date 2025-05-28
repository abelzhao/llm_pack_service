

from enum import Enum
from fastapi import FastAPI
from typing import Optional, List, Dict, AsyncGenerator, Union
import httpx
import json
import logging

app = FastAPI(title="LLM Pack Service")

class Provider(str, Enum):
    DEEPSEEK = "deepseek"
    DOUBAO = "doubao"

class Token(str, Enum):
    DEEPSEEK = "sk-b1b011aead2742079b36b28603e255b3"
    DOUBAO = "07d33001-ac22-4ede-baaa-e3f91587f1b1"


@app.get("/")
async def root():
    return {"message": "Hello from llm-pack-service!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}



@app.post("/llm_chat", response_model=None)
async def llm_chat(messages: List[Dict], provider: Provider, stream: Optional[bool] = False):
    """对外提供大模型聊天服务

    Args:
        messages (List[Dict]): 聊天的消息结构体
        provider (str): 大模型提供商
        stream (Optional[bool]): 是否开启流式返回，默认为False
    Returns:
        当stream=True时: 返回流式响应 (AsyncGenerator[Dict, None])
        当stream=False时: 返回单个响应 (Dict)
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
            "stream": stream
        }
        print(f"Request data: {data}")
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as client:
            response = await client.post(url, headers=headers, json=data)
            if stream:
                async for chunk in response.aiter_bytes():
                    if chunk:
                        chunk_data = json.loads(chunk.decode('utf-8'))
                        yield chunk_data['choices'][0]['delta']
            else:
                response.raise_for_status()
                yield response.json()['choices'][0]['message']
                return
        
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
            "stream": stream
        }
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as client:
            response = await client.post(url, headers=headers, json=data)
            if stream:
                async for chunk in response.aiter_bytes():
                    if chunk:
                        chunk_data = json.loads(chunk.decode('utf-8'))
                        yield chunk_data['choices'][0]['delta']
            else:
                response.raise_for_status()
                yield response.json()['choices'][0]['message']
                return
        
    else:
        raise ValueError(f"Unsupported provider: {provider}. Supported providers are: {', '.join(p.value for p in Provider)}.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8808, log_level="info")
