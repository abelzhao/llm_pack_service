from enum import Enum
from typing import Union
from fastapi import APIRouter, Request, Body
from fastapi.responses import StreamingResponse, Response
import httpx
import json
import os
import logging


from .utils import Model, Provider, Token, Url
from .error import get_error_response

router = APIRouter(prefix="/api/v1", tags=["图像"])
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


@router.post("/text_gen_img", response_model=None)
async def text_gen_image(request: Request, size: ImgSize, watermark: bool, 
                         response_format: ResponseFormat, prompt: str = Body(), guidance_scale: float = 2.5) -> Union[StreamingResponse, Response]:
    """文本生成图像
    
    Args:
        request (Request): 请求对象
        size (ImgSize): 图像大小
        watermark (bool): 是否添加水印
        response_format (ResponseFormat): 响应格式
        guidance_scale (float): 引导比例
    Returns:
        Union[StreamingResponse, Response]: 图像生成结果
    """
    url = os.getenv("DOUBAO_TEXT_GENERATE_IMAGE_API_URL", "https://openspeech.bytedance.com/api/v3/auc/bigmodel/text2image")
    token = os.getenv("DOUBAO_TEXT_GENERATE_IMAGE_API_KEY", "4bbc2539-be5c-4838-96dc-1b943f65967a")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "model": os.getenv("DOUBAO_TEXT_GENERATE_IMAGE_MODEL", "doubao-seedream-3-0-t2i-250415"),
        "size": size.value,
        "watermark": watermark,
        "response_format": response_format.value,
        "guidance_scale": guidance_scale,
        "seed":123
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=data)
        response.raise_for_status()
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
