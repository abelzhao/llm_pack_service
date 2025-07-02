FROM gcc:latest as builder

# Set up apt sources and install Python 3.11
RUN echo "deb http://mirrors.aliyun.com/debian/ bookworm main non-free contrib" > /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian-security/ bookworm-security main" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian/ bookworm-updates main non-free contrib" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian/ bookworm-backports main non-free contrib" >> /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -y build-essential python3.11 python3.11-dev python3-pip python3.11-venv && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    ln -s /usr/bin/python3.11 /usr/bin/python && \
    python -m venv /venv

# Copy all files needed for build
WORKDIR /app

RUN /venv/bin/pip install -i https://mirrors.aliyun.com/pypi/simple/ uv 

# Install dependencies
COPY . /app/
RUN /venv/bin/uv sync 

# Expose application port
EXPOSE 8808

# Run the application
CMD ["uvicorn", "llm_pack_service:app", "--host", "0.0.0.0", "--port", "8808"]
