import logging
import os
import sys
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from llm_pack_service.apis import chat, audio, text2image, outpainting, image2image
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# load env
load_dotenv()

# Configure logging for entire application
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "DEBUG").upper(),
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s - %(funcName)s] - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

app = FastAPI(title="LLM Pack Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("ALLOW_ORIGIN")],  # Allow all origins for development; restrict in production
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods for development; restrict in production
    allow_headers=["*"],  # Allow all headers for development; restrict in production
)

app.include_router(chat.router)
app.include_router(audio.router)
app.include_router(text2image.router)
app.include_router(outpainting.router)
app.include_router(image2image.router)


# 挂载静态文件
app.mount('/static', StaticFiles(directory='static'), name='static')


@app.get("/")
async def root():
    return {"message": "Hello from llm-pack-service!"}


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.4"}


def main():
    # Test environment variables
    logging.info("Environment Variables Test:")
    logging.info(f"LOG_LEVEL: {os.getenv('LOG_LEVEL')}")
    logging.info(f"ALLOW_ORIGIN: {os.getenv('ALLOW_ORIGIN')}")
    logging.info(f"DOUBAO_API_KEY: {'*****' if os.getenv('DOUBAO_API_KEY') else 'Not Found'}")
    
    logging.info("Starting llm-pack-service...")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8808, log_level="info")


if __name__ == "__main__":
    main()
