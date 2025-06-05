from enum import Enum
from typing import Union, Optional
from fastapi import APIRouter, Request, Body, Query, HTTPException
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel, Field
import httpx
import json
import os
import logging


from .utils import Model, Provider, Token, Url
from .error import get_error_response



router = APIRouter(prefix="/api/v1", tags=["文字生成图像"])
JSON_MEDIA_TYPE = "application/json"

class ImgSize(str, Enum):
    S_1024_1024="1024x1024"
    S_864_1152="864x1152"
    S_1152_864="1152x864"
    S_1280_720="1280x720"
    S_720_1280="720x1280"
    S_832_1248="832x1248"
    S_1248_832="1248x832"
    S_1512_648="1512x648"
    
class ResponseFormat(str, Enum):
    URL = "url"
    B64JSON = "b64_json"
    
class ImageRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=1000)
    size: str
    watermark: bool
    response_format: str
    guidance_scale: Optional[float] = Field(2.5, ge=0.0, le=10.0)


@router.post("/t2i", response_model=None)
async def text_gen_image(
    request: ImageRequest = Body(...)
) -> Union[StreamingResponse, Response]:
    """文本生成图像
    
    Args:
        request (ImageRequest): 图像生成请求参数
    Returns:
        Union[StreamingResponse, Response]: 图像生成结果
    """
    prompt = request.prompt
    size = request.size
    watermark = request.watermark
    response_format = request.response_format
    guidance_scale = request.guidance_scale
    # Validate size
    valid_sizes = [e.value for e in ImgSize]
    if size not in valid_sizes:
        return get_error_response(
            f"Invalid size. Must be one of: {', '.join(valid_sizes)}"
        )
    
    # Validate response_format
    valid_formats = [e.value for e in ResponseFormat]
    if response_format not in valid_formats:
        return get_error_response(
            f"Invalid response_format. Must be one of: {', '.join(valid_formats)}"
        )
    
    # Validate guidance_scale
    if guidance_scale < 0 or guidance_scale > 10:
        return get_error_response(
            "guidance_scale must be between 0.0 and 10.0"
        )

    logging.debug(f"Image generation request - prompt: {prompt}, size: {size}, watermark: {watermark}, format: {response_format}, guidance: {guidance_scale}")
    url = os.getenv("DOUBAO_TEXT_GENERATE_IMAGE_API_URL", "https://ark.cn-beijing.volces.com/api/v3/text2image/generate")
    token = os.getenv("DOUBAO_TEXT_GENERATE_IMAGE_API_KEY", "4bbc2539-be5c-4838-96dc-1b943f65967a")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    data = {
        "model": os.getenv("DOUBAO_TEXT_GENERATE_IMAGE_MODEL", "doubao-seedream-3-0-t2i-250415"),
        "size": size,
        "watermark": watermark,
        "response_format": response_format,
        "guidance_scale": guidance_scale,
        "seed":123,
        "prompt": prompt
    }
    logging.debug(f"Request data: {data}")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=data)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            return get_error_response(f"HTTP error occurred: {e.response.status_code} - url: {url} - data: {data}")
        data = response.json()
        logging.debug(f"Response data: {data}")
        if response_format == ResponseFormat.URL:
            image_url = data.get("image_url")
            if not image_url:
                return get_error_response("Image URL not found in response")
            return Response(
                json.dumps({"image_url": image_url}),
                status_code=200,
                media_type=JSON_MEDIA_TYPE
            )
        elif response_format == ResponseFormat.B64JSON:
            b64_image = data.get("b64_json")
            if not b64_image:
                return get_error_response("Base64 image not found in response")
            return Response(
                json.dumps({"b64_json": b64_image}),
                status_code=200,
                media_type=JSON_MEDIA_TYPE
            )
        else:
            return get_error_response(f"Unsupported response format: {response_format}")
