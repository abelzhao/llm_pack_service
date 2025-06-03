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
import os


from .error import get_error_response, TaskSubmissionError, TaskQueryError

router = APIRouter(prefix="/api/v1", tags=["语音"])

JSON_MEDIA_TYPE = "application/json"

@router.get("/tw", response_model=None)
async def temp_mp3(request: Request, file_name: str = "./test/output.mp3") -> Union[StreamingResponse, Response]:
    """把file_name所在的文件以音频形式返回
    """
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
    
    
async def submit_task(request_data: Dict[str, Union[str, Dict, list]]):
    """提交语音任务"""
    submit_url = os.getenv("DOUBAO_AUC_API_SUBMIT_URL", "https://openspeech.bytedance.com/api/v3/auc/bigmodel/submit")
    logging.info(f'submit_url: {submit_url}')

    task_id = str(uuid.uuid4())
    
    headers = {
        "X-Api-App-Key": os.getenv("X_Api_App_Id", "5722492847"),
        "X-Api-Access-Key": os.getenv("X_Api_Access_Token", "yI2H5ccfp_oP8kgtDLtAUtLhPiDpdKd0"),
        "X-Api-Resource-Id": "volc.bigasr.auc",
        "X-Api-Request-Id": task_id,
        "X-Api-Sequence": "-1"
    }
    
    logging.info(f'Submit task request headers: \n{json.dumps(headers, indent=2)}\n')
    logging.info(f'Submit task request data: \n{json.dumps(request_data, indent=2)}\n')
    
    async with httpx.AsyncClient() as client:
        response = await client.post(submit_url, json=json.dumps(request_data), headers=headers)
        print(f'Submit task response headers: \n{response.headers}\n')
        if 'X-Api-Status-Code' in response.headers and response.headers["X-Api-Status-Code"] == "20000000":
            logging.info(f'Submit task response header X-Api-Status-Code: {response.headers["X-Api-Status-Code"]}')
            logging.info(f'Submit task response header X-Api-Message: {response.headers["X-Api-Message"]}')
            x_tt_logid = response.headers.get("X-Tt-Logid", "")
            logging.info(f'Submit task response header X-Tt-Logid: {x_tt_logid}\n')
            return task_id, x_tt_logid
        else:
            print('\nSubmit task failed\n')
            raise TaskSubmissionError("Task submission failed: X-Api-Status-Code not in response headers")
    
    return task_id


async def query_task(task_id, x_tt_logid):
    query_url = os.getenv("DOUBAO_AUC_API_QUERY_URL", "https://openspeech.bytedance.com/api/v3/auc/bigmodel/query")
    headers = {
        "X-Api-App-Key": os.getenv("X_Api_App_Id", "5722492847"),
        "X-Api-Access-Key": os.getenv("X_Api_Access_Token", "yI2H5ccfp_oP8kgtDLtAUtLhPiDpdKd0"),
        "X-Api-Resource-Id": "volc.bigasr.auc",
        "X-Api-Request-Id": task_id,
        "X-Tt-Logid": x_tt_logid  # 固定传递 x-tt-logid
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(query_url, json.dumps({}), headers=headers)
        if 'X-Api-Status-Code' in response.headers:
            logging.info(f'Query task response header X-Api-Status-Code: {response.headers["X-Api-Status-Code"]}')
            logging.info(f'Query task response header X-Api-Message: {response.headers["X-Api-Message"]}')
            logging.info(f'Query task response header X-Tt-Logid: {response.headers["X-Tt-Logid"]}\n')
        else:
            logging.info(f'Query task failed and the response headers are: {response.headers}')
            raise TaskSubmissionError("Task query failed: X-Api-Status-Code not in response headers")        
        if response.status_code != 200:
            raise TaskQueryError("Task query failed with non-200 status code")
        return response


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
            temp_file.write(audio_data)
            temp_audio_path = temp_file.name
    except Exception as e:
        return get_error_response(f"Error saving audio file: {str(e)}")
    
    try:
        # temp_audio_url = f"{request.url.scheme}://{request.url.netloc}/api/v1/tw?file_name={temp_audio_path}"
        temp_audio_url = "http://8.137.149.26:8808/api/v1/tw?file_name=./test/output.mp3"
        logging.info(f"temp_audio_url: {temp_audio_url}")
    except Exception as e:
        return get_error_response(f"Error generating file URL: {str(e)}")
        
    data = {
        "user": {
            "uid": os.getenv("X_Api_App_Uid","2101349786")
        },
        "audio": {
            "url": temp_audio_url,
            "format": "mp3",  # Adjust based on actual audio format
            "codec": "raw",
            "rate": 16000,
            "bits": 16,
            "channel": 1
        },
        "request": {
            "model_name": "bigmodel",
            # Additional parameters can be added here
            "show_utterances": True,
            "corpus": {
                # "boosting_table_name": "test",
                "correct_table_name": "",
                "context": ""
            }
        }
    }
    
    try:
        task_id, x_tt_logid = await submit_task(data)  # 提交任务
    except TaskSubmissionError as e:
        return get_error_response(str(e))
    
    while True:
        try:
            query_response = await query_task(task_id, x_tt_logid)  # 查询任务状态
            code = query_response.headers.get('X-Api-Status-Code', "")
            if code == '20000000':
                logging.info('Query task success')
                return Response(
                    content=json.dumps(data),
                    media_type="application/json"
                )
            elif code != '20000001' and code != '20000002':
                logging.error(f"Task failed with code: {code}")
                return get_error_response("Task failed")
            await asyncio.sleep(1)  # 等待一段时间后重试
        except TaskQueryError as e:
            return get_error_response(str(e))
