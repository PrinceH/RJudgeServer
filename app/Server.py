# -*- coding:utf-8 -*-
import websocket
import queue
import redis
import json
import sys
import os
import signal
import time
import pickle
from JudgeService import JudgeService
re = redis.Redis(host='redis', port=6379, db=1,password="admin123")
try:
    import thread
except ImportError:
    import _thread as thread
def on_message(ws, message):
    global re
    data = json.loads(message)
    if data["type"] == "submission":
        print("{} There are new submissions".format(data["submission_id"]))
        re.lpush("judge",json.dumps(data))
    elif data["type"] == "query_task_number":
        ws.send(json.dumps({"task_number":re.llen("judge")}))
def on_error(ws, error):
    print(error)

def on_close(ws):
    print("### closed ###")

def on_open(ws):
    def run(*args):
        global re
        time.sleep(1)
        while True:
            if re.llen("judge") > 0:
                data = json.loads(re.lpop("judge").decode())
                judger = JudgeService(
                    language_config=data["language_config"],
                    test_case_id=data["test_case_id"],
                    submission_id=data["submission_id"],
                    src=data["src"],
                    max_memory=data["max_memory"],
                    max_cpu_time=data["max_cpu_time"]
                )
                print(judger._run())
    thread.start_new_thread(run, ())

if __name__ == "__main__":

    websocket.enableTrace(True)
    ws = websocket.WebSocketApp("ws://{}/websocket/judge".format(os.getenv("SERVER_ADDRESS")),
                              on_message = on_message,
                              on_error = on_error,
                              on_close = on_close)
    ws.on_open = on_open
    thread.start_new_thread(ws.run_forever(), ())