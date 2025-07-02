from enum import Enum
from typing import Union, Dict
from fastapi import APIRouter
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel, Field, validator
from .utils import Token, Url
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
    type: str = Field("canny", description="Type of controlnet")
    strength: float = Field(0.6, description="Strength of controlnet")
    binary_data_index: int = Field(0, description="Binary data index")
    
class LogoInfo(BaseModel):
    add_logo: bool = False
    position: int = 0
    language: int = 0
    logo_text_content: str = ""

class RequestJson(BaseModel):
    """图像到图像的请求体"""
    req_key: str = Field("high_aes_scheduler_svr_controlnet_v2.0", description="Request key")
    binary_data_base64: list[str] = Field([], description="Binary data in base64 format")
    image_urls: list[str] = Field([], description="Image URLs")
    prompt: str = Field("", description="Prompt text")
    controlnet_args: ControlnetArgs = Field(ControlnetArgs(), description="Controlnet arguments")
    logo_info: LogoInfo = Field(LogoInfo(), description="Logo information")

    class Config:
        extra = "allow"
    
    @validator('binary_data_base64', 'image_urls')
    def validate_image_sources(cls, v, values):
        binary_data = values.get('binary_data_base64', [])
        image_urls = values.get('image_urls', [])
        if bool(binary_data) == bool(image_urls):  # Both empty or both non-empty
            raise ValueError("Either binary_data_base64 or image_urls must be provided, but not both")
        return v

    
class ImageResponse(BaseModel):
    code: int = Field(..., description="Response status code")
    msg: str = Field(..., description="Response message")
    data: Dict = Field(..., description="Response data")
    status: int = Field(..., description="HTTP status code")

@router.post("/image2image", response_model=ImageResponse)
async def image2image(request_json: RequestJson) -> Response:
    """图像到图像的API接口"""
    try:
        # TODO: Implement actual image2image processing
        # For now return a mock response
        return Response(
            json.dumps({
                "code": 1,
                "msg": "success",
                "data": {
                    "image_url": "https://example.com/generated-image.jpg",
                    "status": "completed"
                },
                "status": 200
            }),
            media_type="application/json"
        )
    except Exception as e:
        return Response(
            json.dumps({
                "code": 0,
                "msg": str(e),
                "data": {},
                "status": 500
            }),
            status_code=500,
            media_type="application/json"
        )
