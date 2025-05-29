from enum import Enum
from fastapi import FastAPI
import logging

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

def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logging.info("Starting llm-pack-service...")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8808, log_level="info")


if __name__ == "__main__":
    main()
