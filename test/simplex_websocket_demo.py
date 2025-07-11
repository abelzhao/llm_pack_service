import json
import time
import uuid
import requests


def submit_task():

    submit_url = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/submit"

    task_id = str(uuid.uuid4())

    headers = {
        "X-Api-App-Key": appid,
        "X-Api-Access-Key": token,
        "X-Api-Resource-Id": "volc.bigasr.auc",
        "X-Api-Request-Id": task_id,
        "X-Api-Sequence": "-1"
    }

    request = {
        "user": {
            "uid": "2101349786"
        },
        "audio": {
            "url": file_url,
            "format": "mp3",
            "codec": "raw",
            "rate": 16000,
            "bits": 16,
            "channel": 1
        },
        "request": {
            "model_name": "bigmodel",
            # "enable_itn": True,
            # "enable_punc": True,
            # "enable_ddc": True,
            "show_utterances": True,
            # "enable_channel_split": True,
            # "vad_segment": True,
            # "enable_speaker_info": True,
            "corpus": {
                # "boosting_table_name": "test",
                "correct_table_name": "",
                "context": ""
            }
        }
    }
    print(f'Submit task request headers: \n{json.dumps(headers, indent=2)}\n')
    print(f'Submit task request: \n{json.dumps(request, indent=2)}\n')
    response = requests.post(submit_url, data=json.dumps(request), headers=headers)
    print(f'Submit task response headers: \n{response.headers}\n')
    if 'X-Api-Status-Code' in response.headers and response.headers["X-Api-Status-Code"] == "20000000":
        print(f'Submit task response header X-Api-Status-Code: {response.headers["X-Api-Status-Code"]}')
        print(f'Submit task response header X-Api-Message: {response.headers["X-Api-Message"]}')
        x_tt_logid = response.headers.get("X-Tt-Logid", "")
        print(f'Submit task response header X-Tt-Logid: {response.headers["X-Tt-Logid"]}\n')
        return task_id, x_tt_logid
    else:
        print('\nSubmit task failed\n')
        exit(1)
    return task_id


def query_task(task_id, x_tt_logid):
    query_url = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/query"

    headers = {
        "X-Api-App-Key": appid,
        "X-Api-Access-Key": token,
        "X-Api-Resource-Id": "volc.bigasr.auc",
        "X-Api-Request-Id": task_id,
        "X-Tt-Logid": x_tt_logid  # 固定传递 x-tt-logid
    }

    response = requests.post(query_url, json.dumps({}), headers=headers)

    if 'X-Api-Status-Code' in response.headers:
        print(f'Query task response header X-Api-Status-Code: {response.headers["X-Api-Status-Code"]}')
        print(f'Query task response header X-Api-Message: {response.headers["X-Api-Message"]}')
        print(f'Query task response header X-Tt-Logid: {response.headers["X-Tt-Logid"]}\n')
    else:
        print(f'Query task failed and the response headers are: {response.headers}')
        exit(1)
    return response


def main():
    task_id, x_tt_logid = submit_task()
    while True:
        query_response = query_task(task_id, x_tt_logid)
        code = query_response.headers.get('X-Api-Status-Code', "")
        if code == '20000000':  # task finished
            print(json.dumps(query_response.json())+"\n")
            print("SUCCESS!")
            exit(0)
        elif code != '20000001' and code != '20000002':  # task failed
            print("FAILED!")
            exit(1)
        time.sleep(1)

# 需要使用在线url，推荐使用TOS
file_url = "http://8.137.149.26:8808/api/v1/tw?file_name=./test/output.mp3"
# 填入控制台获取的app id和access token
appid = "5722492847"
token = "yI2H5ccfp_oP8kgtDLtAUtLhPiDpdKd0"

if __name__ == '__main__':
    main()
