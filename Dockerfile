FROM docker.1ms.run/python:3.11-slim as builder

WORKDIR /app

# Copy all files needed for build
COPY . /app/

# Install dependencies
RUN pip install -i https://mirrors.aliyun.com/pypi/simple/ .

# Expose application port
EXPOSE 8808

# Run the application
CMD ["uvicorn", "llm_pack_service:app", "--host", "0.0.0.0", "--port", "8808"]