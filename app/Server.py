# -*- coding:utf-8 -*-
import psutil
import websocket
import redis
import json
import socket
import os
import time

from JudgeService import JudgeService
re = redis.Redis(host='redis', port=6379, db=1,password="admin123")
queue_name = "{}_judge".format(socket.gethostname())
try:
    import thread
except ImportError:
    import _thread as thread
def on_message(ws, message):
    global re
    data = json.loads(message)
    if data["type"] == "judge":
        print("{} There are new submissions".format(data["submission_id"]))
        re.lpush(queue_name,json.dumps(data))
def on_error(ws, error):
    print(error)

def on_close(ws):
    print(ws)
    print("### closed ###")

def on_open(ws):
    def run(*args):
        global re
        time.sleep(1)
        while True:
            if re.llen(queue_name) > 0:
                data = json.loads(re.rpop(queue_name).decode())
                judger = JudgeService(
                    language_config=data["language_config"],
                    test_case_id=data["test_case_id"],
                    submission_id=data["submission_id"],
                    src=data["src"],
                    max_memory=data["max_memory"],
                    max_cpu_time=data["max_cpu_time"],
                    is_spj=data['is_spj']
                )
                ws.send(json.dumps({'type':'judging','hostname': socket.gethostname(), 'judge_status_id': data['judge_status_id']}))
                result = {'type': "judged", 'judge_status_id': data['judge_status_id'], 'judge_info': judger._run(),'hostname': socket.gethostname()}
                print('send')
                ws.send(json.dumps(result))
            if re.llen(queue_name) == 0:
                time.sleep(1)

    def heartbeat(*args):
        m = psutil.virtual_memory()
        while True:
            body = {"type":"heartbeat","hostname":socket.gethostname(),"token":"12345","task_number":re.llen("judge"),"cpu_usage":psutil.cpu_percent(interval=1),"memory_usage":m.percent,"cpu_core":psutil.cpu_count()}
            ws.send(json.dumps(body))
            time.sleep(5)
    thread.start_new_thread(run, ())
    thread.start_new_thread(heartbeat,())

if __name__ == "__main__":
    # websocket.enableTrace(True)
    print(psutil.cpu_count())
    print(os.getenv("WEB_SOCKET_URL"))
    print(os.getenv("SERVER_URL"))
    ws = websocket.WebSocketApp("{}".format(os.getenv("WEB_SOCKET_URL")),
                              on_message = on_message,
                              on_error = on_error,
                              on_close = on_close)
    ws.on_open = on_open
    ws.run_forever()