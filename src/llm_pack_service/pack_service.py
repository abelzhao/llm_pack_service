from enum import Enum
from fastapi import FastAPI
import logging
import os
import sys

from llm_pack_service.apis import nonstream, streamable, chat

# Configure logging for entire application
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

app = FastAPI(title="LLM Pack Service")

app.include_router(nonstream.router)
app.include_router(streamable.router)
app.include_router(chat.router)

@app.get("/")
async def root():
    return {"message": "Hello from llm-pack-service!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

def main():
    # Verify environment variables loaded
    logging.info(f"DEEPSEEK_API_KEY loaded: {'yes' if os.getenv('DEEPSEEK_API_KEY') else 'no'}")
    logging.info(f"DOUBAO_API_KEY loaded: {'yes' if os.getenv('DOUBAO_API_KEY') else 'no'}")
    
    logging.info("Starting llm-pack-service...")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8808, log_level="error")


if __name__ == "__main__":
    main()
