from enum import Enum
from typing import Union
from fastapi import APIRouter
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel, Field, validator
import httpx
import json
import os
import logging
from dotenv import load_dotenv
from .error import get_error_response

# load env
load_dotenv()

router = APIRouter(prefix="/api/v1", tags=["图像生成图像"])
JSON_MEDIA_TYPE = "application/json"


class ControlnetArgs(BaseModel):
    type: str = Field(...)
    strength: float = Field(...)
    binary_data_index: float = Field(...)
    
class LogoInfo(BaseModel):
    add_logo: bool = False
    position: int = 0
    language: int = 0
    logo_text_content: str = ""

class RequestJson(BaseModel):
    """图像到图像的请求体"""
    req_key: str = Field(...)
    binary_data_base64: list[str] = Field(...)
    image_urls: list[str] = Field(...)
    prompt: str = Field(...)
    controlnet_args: ControlnetArgs = Field(...)

    class Config:
        extra = "allow"
    
    @validator('binary_data_base64', 'image_urls')
    def validate_image_sources(cls, v, values):
        binary_data = values.get('binary_data_base64', [])
        image_urls = values.get('image_urls', [])
        if bool(binary_data) == bool(image_urls):  # Both empty or both non-empty
            raise ValueError("Either binary_data_base64 or image_urls must be provided, but not both")
        return v

    
@router.post("/image2image", response_class=None)
async def image2image(request_json: RequestJson) -> Response:
    """图像到图像的API接口"""
    # 1. 发送请求到图像生成服务
    # 2. 等待服务返回结果
    # 3. 返回结果
    # 4. 处理异常
    pass
