

from enum import Enum
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from typing import Optional, List, Dict, AsyncGenerator, Union
import httpx
import json
import logging

from llm_pack_service.utils import Provider, Token  # Assuming utils.py contains the Provider and Token enums
from llm_pack_service.apis import nonstream, streamable

app = FastAPI(title="LLM Pack Service")

app.include_router(nonstream.router)
app.include_router(streamable.router)

@app.get("/")
async def root():
    return {"message": "Hello from llm-pack-service!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}





if __name__ == "__main__":
    import uvicorn
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    uvicorn.run(app, host="0.0.0.0", port=8808, log_level="info")
