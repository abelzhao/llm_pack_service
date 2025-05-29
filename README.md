# LLM Pack Service

A Python service for managing and interacting with LLM packs.

## Features

- Streamable and non-streamable API endpoints
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

### API Endpoints

- `/nonstream`: Non-streaming API endpoint
- `/stream`: Streaming API endpoint

## Docker

Build the image:
```bash
docker build -t llm-pack-service .
```

Run the container:
```bash
docker-compose up
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
src/
├── llm_pack_service/
│   ├── apis/
│   │   ├── nonstream.py
│   │   ├── streamable.py
│   │   └── utils.py
│   ├── pack_service.py
│   └── __init__.py
└── service.py
