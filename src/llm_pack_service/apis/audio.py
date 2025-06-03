from enum import Enum
from typing import AsyncGenerator, Dict, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
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

from .utils import Provider, Token, Url, Model  # Import from parent module

JSON_MEDIA_TYPE = "application/json"

router = APIRouter(prefix="/api/v1", tags=["语音"])

# Protocol constants from simplex_websocket_demo_stream.py
PROTOCOL_VERSION = 0b0001
FULL_CLIENT_REQUEST = 0b0001
AUDIO_ONLY_REQUEST = 0b0010
FULL_SERVER_RESPONSE = 0b1001
SERVER_ACK = 0b1011
SERVER_ERROR_RESPONSE = 0b1111
NO_SEQUENCE = 0b0000
POS_SEQUENCE = 0b0001
NEG_SEQUENCE = 0b0010
NEG_WITH_SEQUENCE = 0b0011
JSON_SERIALIZATION = 0b0001
GZIP_COMPRESSION = 0b0001

def generate_header(
        message_type=FULL_CLIENT_REQUEST,
        message_type_specific_flags=NO_SEQUENCE,
        serial_method=JSON_SERIALIZATION,
        compression_type=GZIP_COMPRESSION,
        reserved_data=0x00
):
    """Generate WebSocket protocol header"""
    header = bytearray()
    header_size = 1
    header.append((PROTOCOL_VERSION << 4) | header_size)
    header.append((message_type << 4) | message_type_specific_flags)
    header.append((serial_method << 4) | compression_type)
    header.append(reserved_data)
    return header

def generate_before_payload(sequence: int):
    """Generate sequence number for payload"""
    before_payload = bytearray()
    before_payload.extend(sequence.to_bytes(4, 'big', signed=True))
    return before_payload

def parse_response(res: bytes) -> Dict:
    """Parse WebSocket response"""
    protocol_version = res[0] >> 4
    header_size = res[0] & 0x0f
    message_type = res[1] >> 4
    message_type_specific_flags = res[1] & 0x0f
    serialization_method = res[2] >> 4
    message_compression = res[2] & 0x0f
    reserved = res[3]
    header_extensions = res[4:header_size * 4]
    payload = res[header_size * 4:]
    
    result = {'is_last_package': False}
    
    if message_type_specific_flags & 0x01:
        seq = int.from_bytes(payload[:4], "big", signed=True)
        result['payload_sequence'] = seq
        payload = payload[4:]

    if message_type_specific_flags & 0x02:
        result['is_last_package'] = True

    if message_type == FULL_SERVER_RESPONSE:
        payload_size = int.from_bytes(payload[:4], "big", signed=True)
        payload_msg = payload[4:]
    elif message_type == SERVER_ACK:
        seq = int.from_bytes(payload[:4], "big", signed=True)
        result['seq'] = seq
        if len(payload) >= 8:
            payload_size = int.from_bytes(payload[4:8], "big", signed=False)
            payload_msg = payload[8:]
    elif message_type == SERVER_ERROR_RESPONSE:
        code = int.from_bytes(payload[:4], "big", signed=False)
        result['code'] = code
        payload_size = int.from_bytes(payload[4:8], "big", signed=False)
        payload_msg = payload[8:]
    else:
        return result

    if payload_msg:
        if message_compression == GZIP_COMPRESSION:
            payload_msg = gzip.decompress(payload_msg)
        if serialization_method == JSON_SERIALIZATION:
            payload_msg = json.loads(str(payload_msg, "utf-8"))
        elif serialization_method != NO_SERIALIZATION:
            payload_msg = str(payload_msg, "utf-8")
        result['payload_msg'] = payload_msg
        result['payload_size'] = payload_size

    return result

def get_error_response(message: str) -> Response:
    """Generate error response"""
    json_data = {
        "code": 0,
        "msg": message,
        "data": {},
        "status": 404
    }
    return Response(
        json.dumps(json_data),
        status_code=200,
        media_type=JSON_MEDIA_TYPE
    )

async def audio_stream_generator(audio_data: bytes, ws_url: str, headers: Dict, segment_size: int = 1000) -> AsyncGenerator[Dict, None]:
    """Generate audio streaming response"""
    reqid = str(uuid.uuid4())
    seq = 1
    
    # Initial request
    request_params = {
        "user": {"uid": "test"},
        "audio": {
            'format': 'wav',
            "sample_rate": 16000,
            "bits": 16,
            "channel": 1,
            "codec": "raw",
        },
        "request": {
            "model_name": "bigmodel",
            "enable_punc": True,
        }
    }
    
    payload_bytes = gzip.compress(json.dumps(request_params).encode())
    full_client_request = bytearray(generate_header(message_type_specific_flags=POS_SEQUENCE))
    full_client_request.extend(generate_before_payload(sequence=seq))
    full_client_request.extend(len(payload_bytes).to_bytes(4, 'big'))
    full_client_request.extend(payload_bytes)

    try:
        async with websockets.connect(ws_url, extra_headers=headers) as ws:
            await ws.send(full_client_request)
            res = await ws.recv()
            result = parse_response(res)
            
            # Process audio chunks
            data_len = len(audio_data)
            offset = 0
            while offset < data_len:
                chunk = audio_data[offset:offset+segment_size]
                last = offset + segment_size >= data_len
                seq += 1
                if last:
                    seq = -seq
                
                payload_bytes = gzip.compress(chunk)
                audio_only_request = bytearray(generate_header(
                    message_type=AUDIO_ONLY_REQUEST,
                    message_type_specific_flags=POS_SEQUENCE if not last else NEG_WITH_SEQUENCE
                ))
                audio_only_request.extend(generate_before_payload(sequence=seq))
                audio_only_request.extend(len(payload_bytes).to_bytes(4, 'big'))
                audio_only_request.extend(payload_bytes)
                
                await ws.send(audio_only_request)
                res = await ws.recv()
                result = parse_response(res)
                yield result
                
                offset += segment_size
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        yield {"error": str(e)}

@router.post("/sauc")
async def sauc(audio_data: bytes, provider: str, model: str) -> Union[StreamingResponse, Response]:
    """语音识别服务接口
    
    Args:
        audio_data: 音频数据 (WAV格式)
        provider: 服务提供商
        model: 模型名称
        
    Returns:
        StreamingResponse或错误Response
    """
    if provider == Provider.DOUBAO.value:
        url = Url.DOUBAO.value
        token = Token.DOUBAO.value
    else:
        return get_error_response(f"不支持的提供商: {provider}")
    
    headers = {
        "X-Api-Resource-Id": "volc.bigasr.sauc.duration",
        "X-Api-Access-Key": "",
        "X-Api-App-Key": "",
        "X-Api-Request-Id": str(uuid.uuid4())
    }
    
    try:
        return StreamingResponse(
            audio_stream_generator(audio_data, url, headers),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive"
            }
        )
    except Exception as e:
        return get_error_response(f"语音识别错误: {e}")
