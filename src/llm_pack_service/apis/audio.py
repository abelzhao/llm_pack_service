from enum import Enum
from typing import AsyncGenerator, Dict, Optional, Union
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, UploadFile, Request
from fastapi.responses import StreamingResponse, Response
import httpx
import json
import logging
import asyncio
import websockets
import uuid
import gzip
import time
from datetime import datetime
from io import BytesIO
import wave
import tempfile

from .utils import get_error_response  # Import only needed function

JSON_MEDIA_TYPE = "application/json"

router = APIRouter(prefix="/api/v1", tags=["语音"])

@router.get("/tw", response_model=None)
async def temp_mp3(request: Request, file_name: str = "./test/output.mp3") -> Union[StreamingResponse, Response]:
    """把file_name所在的文件以音频形式返回
    """
    # 检查file_name是否mp3文件
    if not file_name.endswith('.mp3'):
        return get_error_response("Invalid file type - .mp3 file required")
    try:
        with open(file_name, 'rb') as f:
            audio_data = f.read()
            return StreamingResponse(
                iter([audio_data]),
                media_type="audio/mp3"  # Adjust based on actual output format
            )
    except FileNotFoundError:
        return get_error_response(f"File {file_name} not found")
    
    
async def submit_task(
    audio_url: str,
    model_name: str = "bigmodel",
    uid: str = "fake_uid"
) -> Dict:
    """提交语音任务"""
    submit_url = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/submit"
    
    task_id = str(uuid.uuid4())
    
    headers = {
        "X-Api-App-Key": INTERNAL_TOKEN,
        "X-Api-Access-Key": INTERNAL_TOKEN,
        "X-Api-Resource-Id": "volc.bigasr.auc",
        "X-Api-Request-Id": task_id,
        "X-Api-Sequence": "-1"
    }
    
    request_data = {
        "user": {
            "uid": uid
        },
        "audio": {
            "url": audio_url,
            "format": "mp3",
            "codec": "raw",
            "rate": 16000,
            "bits": 16,
            "channel": 1
        },
        "request": {
            "model_name": model_name,
            # Additional parameters can be added here
        }
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(submit_url, json=request_data, headers=headers)
        
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to submit task: {response.text}")
    
    

@router.post("/auc", response_model=None)
async def auc(request: Request, audio: UploadFile) -> Union[StreamingResponse, Response]:
    """语音聊天接口"""
    # Validate audio file
    if not audio.content_type.startswith('audio/'):
        return get_error_response("Invalid file type - audio file required")

    # Read audio data
    try:
        audio_data = await audio.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
            temp_audio.write(audio_data)
            temp_audio_path = temp_file.name
    except Exception as e:
        return get_error_response(f"Error saving audio file: {str(e)}")
    
    try:
        temp_audio_url = f"{request.url.scheme}://{request.url.netloc}/api/v1/tw?file_name={temp_audio_path}"
        logging.info(f"temp_audio_url: {temp_audio_url}")
    except Exception as e:
        return get_error_response(f"Error generating file URL: {str(e)}")
        
    data = {
        "user": {
            "uid": "fake_uid"
        },
        "audio": {
            "url": temp_file_url,
            "format": "mp3",  # Adjust based on actual audio format
            "codec": "raw",
            "rate": 16000,
            "bits": 16,
            "channel": 1
        },
        "request": {
            "model_name": "bigmodel",
            # Additional parameters can be added here
        }
    }
    return Response(
        content=json.dumps(data),
        media_type=JSON_MEDIA_TYPE
    )


    # Process audio data here (placeholder)
    # You would typically send to a speech recognition service
    processed_data = audio_data  # Placeholder - replace with actual processing

    # Return streaming response
    return StreamingResponse(
        iter([processed_data]),
        media_type="audio/wav"  # Adjust based on actual output format
    )
