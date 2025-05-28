

from enum import Enum
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
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
async def llm_chat(messages: List[Dict], provider: Provider):
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


async def llm_streaming_chat_generator(messages: List[Dict], provider: Provider):
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
                        result = json.dumps(chunk_data['choices'][0]['delta'], ensure_ascii=False)+"\n"
                        logging.info(f"Yielding chunk: {result}")
                        yield result
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
                        yield json.dumps(chunk_data['choices'][0]['delta'], ensure_ascii=False)+"\n"
                    else:
                        logging.warning(f"Unexpected chunk format: {chunk_data}")
                except json.JSONDecodeError as e:
                    logging.warning(f"Failed to parse chunk: {chunk}, error: {e}")
                    continue
        
    else:
        raise ValueError(f"Unsupported provider: {provider}. Supported providers are: {', '.join(p.value for p in Provider)}.")
    
    
@app.post("/llm_streaming_chat")
async def llm_streaming_chat(messages: List[Dict], provider: Provider):
    # Log messages and provider
    print(f"Messages: {messages}, Provider: {provider}")
    
    async def logging_generator():
        async for chunk in llm_streaming_chat_generator(messages, provider):
            logging.info(f"Sending chunk to client: {chunk}")
            yield chunk
    
    return StreamingResponse(
        logging_generator(),
        media_type="application/json"
    )

if __name__ == "__main__":
    import uvicorn
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    uvicorn.run(app, host="0.0.0.0", port=8808, log_level="info")
