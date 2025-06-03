from enum import Enum
import os
from typing import Optional
import json
from fastapi.responses import Response

def get_error_response(message: str) -> Response:
    """生成错误响应"""
    json_data = {
        "code": 0,
        "msg": message,
        "data": {},
        "status": 404
    }
    return Response(
        json.dumps(json_data),
        status_code=200,
        media_type="application/json"
    )

class Provider(str, Enum):
    DEEPSEEK = "deepseek"
    DOUBAO = "doubao"

def get_env_token(key_name: str) -> str:
    """Get API token from environment variable with error handling"""
    token = os.getenv(key_name)
    if not token:
        raise ValueError(
            f"Missing {key_name} in environment variables. "
            f"Please set it in your .env file"
        )
    return token

class Token(str, Enum):
    DEEPSEEK = get_env_token("DEEPSEEK_API_KEY")
    DOUBAO = get_env_token("DOUBAO_API_KEY")
    
    
class Url(str, Enum):
    DEEPSEEK = get_env_token("DEEPSEEK_API_URL")
    DOUBAO = get_env_token("DOUBAO_API_URL")
    
    
class Model(str, Enum):
    DEEPSEEK = get_env_token("DEEPSEEK_MODEL").split(",")
    DOUBAO = get_env_token("DOUBAO_MODEL").split(",")
