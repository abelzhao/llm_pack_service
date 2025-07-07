import os
import base64
import requests
from enum import Enum
from typing import Dict
from pydantic import BaseModel, Field


def get_env_token(key_name: str) -> str:
    """Get API token from environment variable with error handling"""
    token = os.getenv(key_name)
    if not token:
        raise ValueError(
            f"Missing {key_name} in environment variables. "
            f"Please set it in your .env file"
        )
    return token


class Provider(str, Enum):
    DEEPSEEK = "deepseek"
    DOUBAO = "doubao"


class Token(str, Enum):
    # DEEPSEEK = get_env_token("DEEPSEEK_API_KEY")
    DOUBAO = get_env_token("DOUBAO_API_KEY")


class Url(str, Enum):
    # DEEPSEEK = get_env_token("DEEPSEEK_API_URL")
    DOUBAO = get_env_token("DOUBAO_API_URL")


class Model(str, Enum):
    # DEEPSEEK = get_env_token("DEEPSEEK_MODEL").split(",")
    DOUBAO = get_env_token("DOUBAO_MODEL").split(",")
    
    
class ImageResponse(BaseModel):
    code: int = Field(..., description="Response status code")
    msg: str = Field(..., description="Response message")
    data: Dict = Field(..., description="Response data")
    status: int = Field(..., description="HTTP status code")


def url_to_base64(image_url):
    # 下载图片数据
    response = requests.get(image_url)
    response.raise_for_status()  # 检查请求是否成功
    
    # 获取图片二进制数据
    image_data = response.content
    
    # 转换为Base64编码字符串
    base64_str = base64.b64encode(image_data).decode('utf-8')
    
    # 自动识别图片格式
    # image_format = response.headers.get('Content-Type', 'image/jpeg').split('/')[-1]
    # if image_format not in ['jpeg', 'png', 'gif', 'webp']:
    #     image_format = 'jpeg'  # 默认格式
    
    # return f"data:image/{image_format};base64,{base64_str}"
    return base64_str