import os
import sys
import hmac
import json
import httpx
import hashlib
import logging
import configparser
import datetime
from datetime import timezone
from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel, validator
from fastapi.responses import Response
from dotenv import load_dotenv
from .error import get_error_response

# load env
load_dotenv()


router = APIRouter(prefix="/api/v1", tags=["智能扩图"])
JSON_MEDIA_TYPE = "application/json"


method = 'POST'
host = 'visual.volcengineapi.com'
region = 'cn-north-1'
endpoint = 'https://visual.volcengineapi.com'
service = 'cv'


def sign(key, msg):
    return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()


def get_signature_key(key, dateStamp, regionName, serviceName):
    kDate = sign(key.encode('utf-8'), dateStamp)
    kRegion = sign(kDate, regionName)
    kService = sign(kRegion, serviceName)
    kSigning = sign(kService, 'request')
    return kSigning


def format_query(parameters):
    request_parameters_init = ''
    for key in sorted(parameters):
        request_parameters_init += key + '=' + parameters[key] + '&'
    request_parameters = request_parameters_init[:-1]
    return request_parameters


def sign_headers(access_key, secret_key, service, req_query, req_body):
    if access_key is None or secret_key is None:
        print('No access key is available.')
        sys.exit()

    t = datetime.datetime.now(timezone.utc)
    logging.debug('t = \n'+ str(t))
    current_date = t.strftime('%Y%m%dT%H%M%SZ')
    logging.debug('current_date = \n'+ current_date)
    # current_date = '20210818T095729Z'
    date_stamp = t.strftime('%Y%m%d') # Date w/o time, used in credential scope
    logging.debug('date_stamp = \n'+ date_stamp)
    canonical_uri = '/'
    signed_headers = 'content-type;host;x-content-sha256;x-date'
    payload_hash = hashlib.sha256(req_body.encode('utf-8')).hexdigest()
    content_type = 'application/json'
    canonical_headers = 'content-type:' + content_type + '\n' + 'host:' + host + \
        '\n' + 'x-content-sha256:' + payload_hash + \
        '\n' + 'x-date:' + current_date + '\n'
    canonical_request = method + '\n' + canonical_uri + '\n' + req_query + \
        '\n' + canonical_headers + '\n' + signed_headers + '\n' + payload_hash
    # print(canonical_request)
    algorithm = 'HMAC-SHA256'
    credential_scope = date_stamp + '/' + region + '/' + service + '/' + 'request'
    string_to_sign = algorithm + '\n' + current_date + '\n' + credential_scope + '\n' + hashlib.sha256(
        canonical_request.encode('utf-8')).hexdigest()
    logging.debug(f'string_to_sign = \n {string_to_sign}')
    signing_key = get_signature_key(secret_key, date_stamp, region, service)
    logging.debug(f'signing_key = \n:{signing_key}')
    
    signature = hmac.new(signing_key, (string_to_sign).encode(
        'utf-8'), hashlib.sha256).hexdigest()
    logging.debug(f'Signature = {signature}')

    authorization_header = algorithm + ' ' + 'Credential=' + access_key + '/' + \
        credential_scope + ', ' + 'SignedHeaders=' + \
        signed_headers + ', ' + 'Signature=' + signature
    # print(authorization_header)
    headers = {'X-Date': current_date,
               'Authorization': authorization_header,
               'X-Content-Sha256': payload_hash,
               'Content-Type': content_type
               }
    logging.debug('Request Headers = ' + json.dumps(headers))
    return headers


config = configparser.ConfigParser()
config.read("model_config.ini")


class OutpaintingRequest(BaseModel):
    binary_data_base64: Optional[List[str]] = None
    image_urls: Optional[List[str]] = None
    custom_prompt: str = ""

    class Config:
        extra = "allow"
        
    @validator('binary_data_base64', 'image_urls')
    def validate_image_sources(cls, v, values):
        binary_data = values.get('binary_data_base64', [])
        image_urls = values.get('image_urls', [])
        if bool(binary_data) == bool(image_urls):  # Both empty or both non-empty
            raise ValueError("Either binary_data_base64 or image_urls must be provided, but not both")
        return v


@router.post("/outpainting", response_model=None)
async def handle_outpainting(request: OutpaintingRequest) -> Response:

    query_params = {
        'Action': 'CVProcess',
        'Version': '2022-08-31',
    }
    formatted_query = format_query(query_params)

    body_params = {
        "req_key": "i2i_outpainting",
        "image_urls": request.image_urls,
        "return_url": True
    }
    formatted_body = json.dumps(body_params)

    access_key = os.getenv("VOLCEENGINE_ACCESS_KEY")
    secret_key = os.getenv("VOLCEENGINE_SECRET_KEY")

    formatted_headers = sign_headers(access_key, secret_key, service,
                                     formatted_query, formatted_body)
    request_url = endpoint + '?' + formatted_query

    logging.debug('\nBEGIN REQUEST++++++++++++++++++++++++++++++++++++')
    logging.debug('Request URL = ' + request_url)
    logging.debug('Request Headers = ' + json.dumps(formatted_headers))
    logging.debug('Request Body = ' + formatted_body)
    logging.debug('ACCESS_KEY = ' + access_key)
    logging.debug('SECRET_KEY = ' + secret_key)

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as client:
            response = await client.post(request_url, headers=formatted_headers,
                                        data=formatted_body)
            response.raise_for_status()
            data = response.json()
            logging.debug('Response Body = ' + json.dumps(data))
            return Response(content=json.dumps(data), media_type=JSON_MEDIA_TYPE)
    except httpx.HTTPStatusError as e:
        return get_error_response(f"HTTP {e.response.status_code} Error: {e.response.text}")
