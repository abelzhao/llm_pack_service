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
# Install dependencies
COPY . /app/

RUN /venv/bin/pip install -i https://mirrors.aliyun.com/pypi/simple/ .


# ENV UV_HTTP_TIMEOUT=120
# RUN /venv/bin/uv sync --index-url https://mirrors.aliyun.com/pypi/simple/ && \
#     uv pip install .

# Expose application port
EXPOSE 8808

# Set Python path and run the application
ENV PYTHONPATH=/app
CMD ["/venv/bin/uvicorn", "llm_pack_service:app", "--host", "0.0.0.0", "--port", "8808"]
