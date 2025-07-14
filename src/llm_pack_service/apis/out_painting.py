import os
import io
import json
import base64
import logging
from PIL import Image
from fastapi import APIRouter
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List
from .utils import ImageResponse
from .error import get_error_response
from fastapi.responses import Response
from volcengine.visual.VisualService import VisualService # type: ignore

# load env
load_dotenv()


router = APIRouter(prefix="/api/v1", tags=["智能图像"])
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


class OutPaintingRatio(BaseModel):
    """图像扩展尺寸配置"""
    top: float = Field(0.1, gt=0, le=1, description="上方扩展像素数")
    bottom: float = Field(0.1, gt=0, le=1, description="下方扩展像素数")
    left: float = Field(0.1, gt=0, le=1, description="左侧扩展像素数")
    right: float = Field(0.1, gt=0, le=1, description="右侧扩展像素数")


class RequestJson(BaseModel):
    """智能扩图的请求体"""
    image_urls: List[str] = Field([
            "https://img.saihuitong.com/2900/img/104581/large/18e2b244234.jpg"
        ], description="图片URLs")
    custom_prompt: str = Field("", description="提示词")
    out_painting_ratio: OutPaintingRatio = Field(OutPaintingRatio(top=.1, bottom=.1, left=.1, right=.1), 
                                                 description="图像扩展尺寸")


@router.post("/out_painting", response_model=ImageResponse)
async def handle_out_painting(req_json: RequestJson) -> Response:
    """智能扩图的API接口"""
    try:
        # Pass context to validators
        # req_json = req_json.model_dump()
        logging.debug(f"{req_json = }")
        
        req_dict = {
            "req_key": "i2i_outpainting",
            "image_urls": req_json.image_urls,
            "scale": 7.0,
            "seed": 3,
            "custom_prompt": req_json.custom_prompt,
            "return_url": True,
            "steps": 30             
        }
        req_dict.update(req_json.out_painting_ratio.model_dump())
        logging.debug(f"{req_dict = }")
        
        visual_service = VisualService()
        visual_service.set_ak(os.getenv("VOLCEENGINE_ACCESS_KEY"))
        visual_service.set_sk(os.getenv("VOLCEENGINE_SECRET_KEY"))
        
        resp = visual_service.cv_process(req_dict)
        
        return Response(
            json.dumps({
                "code": 1,
                "msg": "success",
                "data": {
                        "image_urls":resp["data"]["image_urls"]
                    },
                "status": 200
            }),
            media_type="application/json"
        )
    except Exception as e:
        return get_error_response(str(e))
