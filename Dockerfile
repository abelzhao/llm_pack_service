FROM docker.1ms.run/python:3.11-slim as builder

WORKDIR /app

# Install build dependencies and clean up
RUN echo "deb http://mirrors.aliyun.com/debian/ bullseye main non-free contrib" > /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian-security/ bullseye-security main" >> /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -y build-essential python3-dev gcc && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy all files needed for build
COPY . /app/

# Install dependencies
RUN pip install -i https://mirrors.aliyun.com/pypi/simple/ .

# Expose application port
EXPOSE 8808

# Run the application
CMD ["uvicorn", "llm_pack_service:app", "--host", "0.0.0.0", "--port", "8808"]
