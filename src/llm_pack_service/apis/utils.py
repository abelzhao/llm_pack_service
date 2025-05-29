from enum import Enum
import os
from typing import Optional

class Provider(str, Enum):
    DEEPSEEK = "deepseek"
    DOUBAO = "doubao"

def get_env_token(key_name: str) -> str:
    """Get API token from environment variable with error handling"""
    token = os.getenv(key_name)
    if not token:
        raise ValueError(
            f"Missing {key_name} in environment variables. "
            f"Please set it in your .env file"
        )
    return token

class Token(str, Enum):
    DEEPSEEK = "sk-f805d0e28516492ab3a9b6c732c1e498" #get_env_token("DEEPSEEK_API_KEY")
    DOUBAO = "" # get_env_token("DOUBAO_API_KEY")
