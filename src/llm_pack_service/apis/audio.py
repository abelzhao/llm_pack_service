from typing import Union
from fastapi import APIRouter, UploadFile, Request
from fastapi.responses import StreamingResponse, Response
import httpx
import json
import logging
import asyncio
import uuid
import tempfile
import os
import aiofiles


from .error import get_error_response, TaskSubmissionError, TaskQueryError

router = APIRouter(prefix="/api/v1", tags=["语音转文字"])

JSON_MEDIA_TYPE = "application/json"

@router.get("/tw", response_model=None)
async def temp_mp3(file_name: str = "./test/data/audio_01.mp3") -> Union[StreamingResponse, Response]:
    """把file_name所在的文件以音频形式返回
    """
    if not file_name.endswith('.mp3'):
        return get_error_response("Invalid file type - .mp3 file required")
    try:
        async with aiofiles.open(file_name, 'rb') as f:
            audio_data = await f.read()
            return StreamingResponse(
                iter([audio_data]),
                media_type="audio/mp3"  # Adjust based on actual output format
            )
    except FileNotFoundError:
        return get_error_response(f"File {file_name} not found")
    
    
async def submit_task(request_data):
    """提交语音任务"""
    logging.debug("Submitting task to AUC API")
    submit_url = os.getenv("DOUBAO_AUC_API_SUBMIT_URL", "https://openspeech.bytedance.com/api/v3/auc/bigmodel/submit")
    logging.debug(f'submit_url: {submit_url}')
    task_id = str(uuid.uuid4())
    headers = {
        "X-Api-App-Key": os.getenv("X_Api_App_Id", "5722492847"),
        "X-Api-Access-Key": os.getenv("X_Api_Access_Token", "yI2H5ccfp_oP8kgtDLtAUtLhPiDpdKd0"),
        "X-Api-Resource-Id": "volc.bigasr.auc",
        "X-Api-Request-Id": task_id,
        "X-Api-Sequence": "-1"
    }
    
    logging.debug(f'Submit task request headers: \n{json.dumps(headers, indent=2)}\n')
    logging.debug(f'Submit task request data: \n{json.dumps(request_data, indent=2)}\n')
    
    async with httpx.AsyncClient() as client:
        response = await client.post(submit_url, json=request_data, headers=headers)
        logging.debug(f'Submit task response headers: \n{response.headers}\n')
        if 'X-Api-Status-Code' in response.headers and response.headers["X-Api-Status-Code"] == "20000000":
            logging.debug(f'Submit task response header X-Api-Status-Code: {response.headers["X-Api-Status-Code"]}')
            logging.debug(f'Submit task response header X-Api-Message: {response.headers["X-Api-Message"]}')
            x_tt_logid = response.headers.get("X-Tt-Logid", "")
            logging.debug(f'Submit task response header X-Tt-Logid: {x_tt_logid}\n')
            return task_id, x_tt_logid
        else:
            logging.debug('Submit task failed\n')
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
        response = await client.post(query_url, json={}, headers=headers)
        logging.debug(f'Query task response headers: \n{response.headers}\n')
        if 'X-Api-Status-Code' in response.headers:
            logging.debug(f'Query task response header X-Api-Status-Code: {response.headers["X-Api-Status-Code"]}')
            logging.debug(f'Query task response header X-Api-Message: {response.headers["X-Api-Message"]}')
            logging.debug(f'Query task response header X-Tt-Logid: {response.headers["X-Tt-Logid"]}\n')
        else:
            logging.debug(f'Query task failed and the response headers are: {response.headers}')
            raise TaskSubmissionError("Task query failed: X-Api-Status-Code not in response headers")    
        if response.status_code != 200:
            raise TaskQueryError("Task query failed with non-200 status code")
        return response
    
def del_file(file_path: str):
    """删除文件"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logging.debug(f"Deleted temporary file: {file_path}")
        else:
            logging.debug(f"File not found for deletion: {file_path}")
    except Exception as e:
        logging.error(f"Error deleting file {file_path}: {str(e)}")


@router.post("/auc", response_model=None)
async def auc(request: Request, audio: UploadFile) -> Union[StreamingResponse, Response]:
    """语音聊天接口"""
    # Validate audio file
    if not audio.content_type.startswith('audio/'):
        return get_error_response("Invalid file type - audio file required")
    
    # Read audio data
    try:
        audio_data = await audio.read()
        temp_audio_path = f"/tmp/{uuid.uuid4()}.mp3"
        async with aiofiles.open(temp_audio_path, 'wb') as temp_file:
            await temp_file.write(audio_data)
    except Exception as e:
        logging.error(f"Error creating temporary audio file: {str(e)}")
        return get_error_response(f"Error saving audio file: {str(e)}")
    
    try:
        if logging.getLogger().isEnabledFor(logging.DEBUG):
            temp_audio_url = "http://8.137.149.26:8808/api/v1/tw?file_name=./test/output.mp3"
        else:
            temp_audio_url = f"{request.url.scheme}://{request.url.netloc}/api/v1/tw?file_name={temp_audio_path}"
        logging.debug(f"temp_audio_url: {temp_audio_url}")
    except Exception as e:
        return get_error_response(f"Error generating file URL: {str(e)}")
        
    data = {
        "user": {
            "uid": os.getenv("X_Api_App_Uid","2101349786")
        },
        "audio": {
            "url": temp_audio_url,
            "format": "mp3",
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
        # delete temp_file
        del_file(temp_audio_path)
        return get_error_response(str(e))
    
    while True:
        try:
            query_response = await query_task(task_id, x_tt_logid)  # 查询任务状态
            code = query_response.headers.get('X-Api-Status-Code', "")
            if code == '20000000':
                logging.debug('Query task success')
                query_result = query_response.json()
                if 'result' not in query_result or 'text' not in query_result['result']:
                    logging.error("Query result does not contain expected 'result' or 'text'")
                    del_file(temp_audio_path)
                    return get_error_response("Invalid task result format")
                del_file(temp_audio_path)
                resp_data = {
                    "code": 1,
                    "msg": 'success',
                    "data": query_result['result']['text'],
                    "status": 200
                }
                return Response(
                    json.dumps(resp_data),
                    media_type="application/json"
                )
            elif code != '20000001' and code != '20000002':
                logging.error(f"Task failed with code: {code}")
                del_file(temp_audio_path)
                return get_error_response("Task failed")
            await asyncio.sleep(3)
        except TaskQueryError as e:
            del_file(temp_audio_path)
            return get_error_response(str(e))
