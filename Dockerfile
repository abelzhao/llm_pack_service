# Use official Python 3.11 image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Build arguments for tokens
ARG DEEPSEEK_TOKEN
ARG DOUBAO_TOKEN

# Environment variables
ENV DEEPSEEK_API_KEY=${DEEPSEEK_TOKEN}
ENV DOUBAO_API_KEY=${DOUBAO_TOKEN}

# Copy project files
COPY . .

# Install dependencies using uv pip
RUN pip install uv && \
    uv pip install -e .

# Expose the application port
EXPOSE 8808

# Run the application
CMD ["python", "-m", "llm_pack_service"]
