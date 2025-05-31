# Use official Python 3.11 image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install dependencies using uv pip
RUN pip install uv && \
    uv pip install -e .

# Expose the application port
EXPOSE 8808

# Run the application
CMD ["uvicorn", "llm_pack_service:app", "--host", "0.0.0.0", "--port", "8808"]
