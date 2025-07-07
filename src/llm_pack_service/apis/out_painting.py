import os
import sys
import hmac
import json
import httpx
import hashlib
import logging
import configparser
import datetime
from datetime import timezone
from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel, validator
from fastapi.responses import Response
from dotenv import load_dotenv
from .error import get_error_response

# load env
load_dotenv()


router = APIRouter(prefix="/api/v1", tags=["智能扩图"])
JSON_MEDIA_TYPE = "application/json"


def expand_image_with_mask(image_path, top, bottom, left, right):
    """
    扩展图像并生成对应的mask
    :param image_path: 输入图像路径
    :param top: 上方扩展像素数
    :param bottom: 下方扩展像素数
    :param left: 左侧扩展像素数
    :param right: 右侧扩展像素数
    :return: (扩展后图像base64, 对应mask base64)
    """
    # 打开原始图像
    original_img = Image.open(image_path)
    width, height = original_img.size
    
    # 计算新尺寸
    new_width = width + left + right
    new_height = height + top + bottom
    
    # 创建扩展后的图像
    expanded_img = Image.new('RGB', (new_width, new_height), (255, 255, 255))
    expanded_img.paste(original_img, (left, top))
    
    # 创建mask (原始区域为黑色0，扩展区域为白色255)
    mask = Image.new('L', (new_width, new_height), 255)
    mask.paste(0, (left, top, left + width, top + height))
    
    # 转换为base64
    buffered = io.BytesIO()
    expanded_img.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    buffered = io.BytesIO()
    mask.save(buffered, format="PNG")
    mask_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    return img_base64, mask_base64


class RequestJson(BaseModel):
    """智能扩图的请求体"""
    req_key: str = Field("i2i_outpainting", description="请求Key")
    binary_data_base64: list[str] = Field([], description="二进制BASE64图片")
    image_urls: list[str] = Field([], description="图片URLs")
    scale: int = Field(7, description="取值范围[1, 20]，影响文本描述的程度")
    seed: int = Field(0, description="随机种子")


@router.post("/out_painting", response_model=ImageResponse)
async def handle_out_painting(req_json: RequestJson) -> Response:
    """智能扩图的API接口"""
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