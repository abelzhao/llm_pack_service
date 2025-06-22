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

class ReqJson(BaseModel):
    """纯文本的请求体"""
    prompt: str

T2iImageSizes = Enum("T2iImageSizes", {tis:tis for tis in ['1024x1024','864x1152','1152x864','1280x720',
                                                       '720x1280','832x1248','1248x832','1512x648']})
ResponseFormat = Enum("ResponseFormat", {rf:rf for rf in ['url', 'b64_json']})
# WaterMark = Enum("WaterMark", {wm:wm for wm in ['true','false']})

@router.post("/t2i", response_model=None)
async def text_gen_image(
    req_json: ReqJson,
    size: T2iImageSizes,
    response_format: ResponseFormat,
    guidance_scale: float = 2.5,
    watermark: bool = False
) -> Union[StreamingResponse, Response]:
    """文本生成图像
    Args:
        reqjson ReqJson: 请求体，包含消息和文件
        size T2iImageSizes: 图片大小
        response_format ResponseFormat: 返回格式
        guidance_scale: float: 自由度
        watermark bool: 是否水印
    Returns:
        Union[StreamingResponse, Response]: 图像生成结果
    """
    try:
        req_dict = dict(req_json)
        prompt = req_dict['prompt']
    except Exception as e:
        return get_error_response(f"请求格式错误，请检查输入数据：{e}")
    url = os.getenv("DOUBAO_TEXT_GENERATE_IMAGE_API_URL", "https://ark.cn-beijing.volces.com/api/v3/images/generations")
    token = os.getenv("DOUBAO_TEXT_GENERATE_IMAGE_API_KEY", "4bbc2539-be5c-4838-96dc-1b943f65967a")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    data = {
        "model": os.getenv("DOUBAO_TEXT_GENERATE_IMAGE_MODEL", "doubao-seedream-3-0-t2i-250415"),
        "size": size.value,
        "response_format": response_format.value,
        "watermark": True,
        "guidance_scale": guidance_scale,
        "seed":123,
        "prompt": prompt
    }
    logging.debug(f"Request data: {json.dumps(data)}")
    timeout = httpx.Timeout(60.0, connect=30.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(url, headers=headers, json=data)
            response.raise_for_status()
        # except httpx.HTTPStatusError as e:
        #     return get_error_response(f"HTTP error occurred: {e.response.status_code} - url: {url} - data: {data}")
        except httpx.ConnectTimeout:
            return get_error_response("Connection to image generation service timed out")
        except httpx.ReadTimeout:
            return get_error_response("Image generation service response timed out")
        except httpx.RequestError as e:
            return get_error_response(f"Request to image generation service failed: {str(e)}")
        data = response.json()
        logging.debug(f"Response data: {data}")
        logging.debug(f"{response_format}, {ResponseFormat.url.value}")
        if response_format == ResponseFormat.url:
            try:
                resp_data = {
                    "image_url": data["data"][0]["url"],
                    "usage": data["usage"]
                }
            except Exception as e:
                return get_error_response(f"image_url not found in {data}")
            return Response(
                json.dumps(resp_data),
                status_code=200,
                media_type=JSON_MEDIA_TYPE
            )
        elif response_format == ResponseFormat.b64_json:
            try:
                resp_data = {
                    "b64_json": data["data"][0]["b64_json"],
                    "usage": data["usage"]
                }
            except Exception as e:
                return get_error_response(f"image_url not found in {data}")
            return Response(
                json.dumps(resp_data),
                status_code=200,
                media_type=JSON_MEDIA_TYPE
            )
        else:
            return get_error_response(f"Unsupported response format: {response_format}")
