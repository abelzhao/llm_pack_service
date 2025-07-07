from enum import Enum
from typing import Union, Dict
from fastapi import APIRouter
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel, Field, field_validator
from .utils import Token, Url
import httpx
import json
import os
import logging
from volcengine import visual
from volcengine.visual.VisualService import VisualService
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
    req_key: str = Field("img2img_comic_style", description="Request key")
    sub_req_key: str = Field("img2img_comic_style_monet", description="Sub Request key")
    binary_data_base64: list[str] = Field([], description="Binary data in base64 format")
    image_urls: list[str] = Field(["http://localhost:8808/static/FFFFFFFF.png"], description="Image URLs")
    prompt: str = Field("", description="Prompt text")
    controlnet_args: ControlnetArgs = Field(ControlnetArgs(), description="Controlnet arguments")
    logo_info: LogoInfo = Field(LogoInfo(), description="Logo information")
    return_url: bool = Field("true", description="Return Url")

    class Config:
        extra = "allow"
    
    @field_validator('binary_data_base64', 'image_urls')
    def validate_image_sources(cls, v, info):
        logging.debug(f"{info = }")
        logging.debug(f"{v = }")
        if isinstance(v, list) and not v:  # Skip validation if field is empty
            return v
        # Get the other field value from context
        context = info.context
        if context:
            other_field = 'image_urls' if info.field_name == 'binary_data_base64' else 'binary_data_base64'
            other_value = context.get(other_field, [])
            if bool(v) and bool(other_value):
                raise ValueError("Either binary_data_base64 or image_urls must be provided, but not both")
        return v


class ImageResponse(BaseModel):
    code: int = Field(..., description="Response status code")
    msg: str = Field(..., description="Response message")
    data: Dict = Field(..., description="Response data")
    status: int = Field(..., description="HTTP status code")


@router.post("/img2img", response_model=ImageResponse)
async def image2image(req_json: RequestJson) -> Response:
    """图像到图像的API接口"""
    try:
        # Pass context to validators
        req_dict = req_json.model_dump()
        logging.debug(f"{req_dict = }")
        
        visual_service = VisualService()
        visual_service.set_ak(os.getenv("VOLCEENGINE_ACCESS_KEY"))
        visual_service.set_sk(os.getenv("VOLCEENGINE_SECRET_KEY"))
        
        resp = visual_service.cv_process(req_dict)
        
        return Response(
            json.dumps({
                "code": 1,
                "msg": "success",
                "data": resp,
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
