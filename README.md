# LLM Pack Service

A Python service for managing and interacting with LLM packs, supporting multiple providers and modes.

## Features

- Unified API endpoint supporting both Streamable and non-streamable responses
- Support for doubao and deepseek providers
- Both reason and non-reason modes
- Docker container support
- Pack management functionality

## Installation

```bash
pip install -e .
```

## Usage

Run the service:
```bash
python -m llm_pack_service
```

or 

```bash
uv run llm-pack
```

### API Endpoints

- `/chat`: Main chat endpoint supporting both streaming and non-streaming responses
  - Supports POST requests with JSON payload
  - Configuration options for provider and mode selection
- Additional endpoints in `/apis/` directory for specialized functionality

## Docker

Build the image:
```bash
docker build -t llm-pack-service .
```

Run the container:
```bash
docker-compose up
```

or in detached mode:

```bash
docker-compose up --build -d
```

## Development

Install development dependencies:
```bash
pip install -e ".[dev]"
```

Run tests:
```bash
pytest
```

## Project Structure

```
llm_pack_service/
├── __init__.py
├── __main__.py
├── pack_service.py
└── apis/
    ├── __init__.py
    ├── chat.py        # Main chat endpoint implementation
    ├── nonstream.py   # Non-streaming API handlers
    ├── streamable.py  # Streaming API handlers
    └── utils.py       # Shared utilities
```

## Configuration

Environment variables can be set in `.env` file:
- `PROVIDER`: Set default provider (doubao/deepseek)
- `MODE`: Set default mode (reason/non-reason)
