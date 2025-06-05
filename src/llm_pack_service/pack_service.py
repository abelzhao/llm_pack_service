from enum import Enum
from fastapi import FastAPI
import logging
import os
import sys

from llm_pack_service.apis import chat, audio, image
from fastapi.middleware.cors import CORSMiddleware

# Configure logging for entire application
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "DEBUG").upper(),
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s - %(funcName)s] - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

app = FastAPI(title="LLM Pack Service")

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # Allow all origins for development; restrict in production
#     allow_credentials=True,
#     allow_methods=["*"],  # Allow all methods for development; restrict in production
#     allow_headers=["*"],  # Allow all headers for development; restrict in production
# )

app.include_router(chat.router)
app.include_router(audio.router)
app.include_router(image.router)

@app.get("/")
async def root():
    return {"message": "Hello from llm-pack-service!"}

def main():
    logging.debug(f"DOUBAO_API_KEY loaded: {'yes' if os.getenv('DOUBAO_API_KEY') else 'no'}")
    
    logging.info("Starting llm-pack-service...")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8808, log_level="info")
    logging.info("llm-pack-service started successfully.")


if __name__ == "__main__":
    main()
