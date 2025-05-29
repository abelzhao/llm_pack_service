from enum import Enum

class Provider(str, Enum):
    DEEPSEEK = "deepseek"
    DOUBAO = "doubao"

class Token(str, Enum):
    DEEPSEEK = "sk-b1b011aead2742079b36b28603e255b3"
    DOUBAO = "07d33001-ac22-4ede-baaa-e3f91587f1b1"