from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import httpx
import json
import asyncio

app = FastAPI()

# 目标API的URL（替换为实际地址）
UPSTREAM_API_URL = "https://hx.dcloud.net.cn/Tutorial/StartedTutorial"

async def process_stream(extract_field: str):
    """
    流式处理函数：
    1. 连接上游API获取流
    2. 提取指定字段
    3. 生成处理后的数据块
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("GET", UPSTREAM_API_URL) as upstream_response:
            # 检查上游响应状态
            upstream_response.raise_for_status()
            
            # 按行迭代流数据（适用于JSON行格式）
            async for chunk in upstream_response.aiter_lines():
                if not chunk.strip():  # 跳过空行
                    continue
                
                try:
                    data = json.loads(chunk)
                    # 提取目标字段（支持嵌套字段如"user.address"）
                    target_value = data
                    for key in extract_field.split('.'):
                        target_value = target_value.get(key)
                        if target_value is None:
                            break
                    
                    if target_value is not None:
                        # 生成处理后的JSON行
                        processed = {extract_field: target_value}
                        yield json.dumps(processed) + "\n"
                    
                except (json.JSONDecodeError, KeyError, TypeError):
                    # 跳过无效数据块
                    continue

@app.get("/proxy-stream")
async def proxy_stream(field: str = "data"):
    """流式代理端点"""
    return StreamingResponse(
        content=process_stream(field),
        media_type="application/x-ndjson"  # NDJSON格式
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9900)