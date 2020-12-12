# -*- coding:utf-8 -*-
import psutil
import websocket
import json
import socket
import os
import time
from queue import Queue
from JudgeService import JudgeService
Q = Queue(maxsize=0)
token = os.environ.get("TOKEN")
name = os.environ.get("NAME")
print(token,name)
vis = {}
try:
    import thread
except ImportError:
    import _thread as thread
def on_message(ws, message):
    global Q
    data = json.loads(message)
    if data["type"] == "judge":
        print("{} There are new submissions".format(data["submission_id"]))
        if not vis.get(data["submission_id"],False):
            vis[data["submission_id"]] = True
            Q.put(json.dumps(data))
def on_error(ws, error):
    print(error)

def on_close(ws):
    print(ws)
    print("### closed ###")

def on_open(ws):
    def run(*args):
        global Q
        while True:
            if not Q.empty():
                print("task!!!!\r\n")
                data = json.loads(Q.get())
                judger = JudgeService(
                    language_config=data["language_config"],
                    test_case_id=data["test_case_id"],
                    submission_id=data["submission_id"],
                    src=data["src"],
                    max_memory=data["max_memory"],
                    max_cpu_time=data["max_cpu_time"],
                    is_spj=data['is_spj']
                )
                ws.send(json.dumps({
                    "name": name,
                    'token':token,
                    'type':'judging',
                    'judge_status_id': data['judge_status_id'],
                    "task_number":Q.qsize()
                    }))
                try:
                    result = {
                        "name":name,
                        'token':token,
                        'type': "judged", 
                        'judge_status_id': data['judge_status_id'], 
                        'judge_info': judger._run(),
                        "task_number":Q.qsize()
                        }
                    vis[data['judge_status_id']] = False
                    print('send')
                    print(len(json.dumps(result)))
                    ws.send(json.dumps(result))
                except:
                    pass
            else:
                time.sleep(1)
    def heartbeat(*args):
        m = psutil.virtual_memory()
        while True:
            body = {
                "type":"heartbeat",
                "name":name,
                'token':token,
                "task_number":Q.qsize(),
                "cpu_usage":psutil.cpu_percent(interval=1),
                "memory_usage":m.percent,
                "cpu_core":psutil.cpu_count()}
            ws.send(json.dumps(body))
            time.sleep(5)
    thread.start_new_thread(run, ())
    thread.start_new_thread(heartbeat,())

if __name__ == "__main__":
    print(os.environ.get("WEB_SOCKET_URL"))
    ws = websocket.WebSocketApp(os.environ.get("WEB_SOCKET_URL"),
                              on_message = on_message,
                              on_error = on_error,
                              on_close = on_close)
    ws.on_open = on_open
    ws.run_forever()