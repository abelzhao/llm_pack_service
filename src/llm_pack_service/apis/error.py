from fastapi.responses import Response
import json

class TaskSubmissionError(Exception):
    """Custom exception for task submission failures"""
    pass

class TaskQueryError(Exception):
    """Custom exception for task query failures"""
    pass

def get_error_response(message: str) -> Response:
    """生成错误响应"""
    json_data = {
        "code": 0,
        "msg": message,
        "data": {},
        "status": 500
    }
    return Response(
        json.dumps(json_data),
        status_code=200,
        media_type="application/json"
    )