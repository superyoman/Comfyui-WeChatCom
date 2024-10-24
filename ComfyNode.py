import numpy as np
import base64
import json
import subprocess
import psutil
import time
import ast
from .data import sqlite_db
import os
import yaml
import uuid
from openai import OpenAI
import re
from wcferry import Wcf, WxMsg

sqlite_db.cot_db = os.path.join(os.path.dirname(os.path.abspath(__file__)),"data/db/wx.db")

global wechat_script_path
wechat_script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wechat.py")
def is_main_running():
    for proc in psutil.process_iter(attrs=['pid', 'name']):
        try:
            if proc.info['name'] == 'python.exe' and wechat_script_path in proc.cmdline():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return False

def check_wechat(room_id_list):
    if not is_main_running():
        #Build up tables
        for t in ["at_record", "reply_record", "mission_record"]:
            sqlite_db.preperation(table_name = t)
        # Save room_id to config
        file_path =  os.path.join(os.path.dirname(os.path.abspath(__file__)),"config.yaml")
        data = read_yaml(file_path)
        if 'groups' not in data:
            data['groups'] = {}
        # 修改 enable 列表
        data['groups']['enable'] = room_id_list  # 直接写入整个列表
        # 写回修改后的数据
        write_yaml(file_path, data)
        # Run main.py
        subprocess.Popen(['start', 'cmd', '/k', 'python', wechat_script_path], shell=True)
        return True
    else:
        print("main.py is already running.")
        return False

def is_list_format(s):
    try:
        # 尝试将字符串解析为 Python 对象
        result = ast.literal_eval(s)
        # 检查结果是否为列表
        return isinstance(result, list)
    except (ValueError, SyntaxError):
        return False

# 读取 YAML 文件
def read_yaml(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)

# 写入 YAML 文件
def write_yaml(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as file:
        yaml.dump(data, file, allow_unicode=True, default_flow_style=False)


def chat(api_key="", model_name="gpt-4o",
         input_text="",base_url = "https://api.deepbricks.ai/v1/"):
    client = OpenAI(
        api_key=api_key,
        # base_url="https://api.deepbricks.ai/v1/"
        base_url = "https://api.ephone.ai/v1/"
    )
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "user", "content": input_text},
            ],

        )
        print(response)
        print(response.choices)
        return response.choices[0].message.content

    except Exception as e:
        print(f"An error occurred: {e}")

class WeChat_YoC_input:

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "room_id": ("STRING", {"default": "['xxxxxx@chatroom']", "multiline": False}),
            },
            "optional": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "tooltip": ""}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("STRING",)
    FUNCTION = "Wechat_input"
    CATEGORY = "YoC app/WeChat"

    def Wechat_input(self, room_id,**kwargs):
        if is_list_format(room_id):
            room_id_list = eval(room_id)
        # Check wechat main.py
        if check_wechat(room_id_list):
            time.sleep(3)

        # Wait for getting a question
        while True:
            q_ = sqlite_db.query_data_dict(table = "at_record",sql_where = "where completed = 'init' ")
            print("Waiting to chat")
            if len(q_) > 0:
                q = q_[0]
                break
            time.sleep(5)
        q = {**{"func":"wechat_input"}, **q}

        return (str(q),)

class WeChat_YoC_output:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "response": ("STRING", {"forceInput": True}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("STRING",)
    FUNCTION = "Wechat_output"
    CATEGORY = "YoC app/WeChat"
    OUTPUT_NODE = True

    @classmethod
    def Wechat_output(cls, response):
        try:
            match = re.search(r'\{.*?\}', response, re.DOTALL)
            if match:
                dictionary_str = match.group(0)
            res = eval(dictionary_str)
            if res["chat"] is not None:
                res["completed"] = "completed"
                print(res)
                reply_ = {"chat_id":res["chat_id"],"chat":res["chat"],"room_id":res["room_id"],"receiver_id":res["sender_id"]}
                reply = {**reply_,**{"completed":"init", "modified_time": int(time.time() * 1000000),"asset":None}}
                ans = {k: res[k] for k in ["chat_id", "chat", "room_id", "sender_id", "modified_time", "completed"] if k in res}
                if sqlite_db.update_table(table_name = "at_record", data = ans, id_field = "chat_id", id_value = res["chat_id"]):
                    sqlite_db.add_data(table_name="reply_record", data = reply)
                    return (reply,)
            return (None,)
        except Exception as ex:
            print(ex)
            return (None,)


class WeChat_YoC_history:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "wechat_input": ("STRING", {"forceInput": True}),
            },
            "optional": {
                "run": ("BOOLEAN", {"default": True}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("STRING",)
    FUNCTION = "get_history"
    CATEGORY = "YoC app/WeChat"
    OUTPUT_NODE = True

    def get_history(self, wechat_input,run):
        try:
            res = eval(wechat_input)
            if run:
                reply_ = {"chat_id": res["chat_id"], "chat": res["chat"], "room_id": res["room_id"],
                          "receiver_id": res["sender_id"]}
                reply = {**reply_, **{"completed": "init", "modified_time": int(time.time() * 1000000), "mission": "chat_history", "result": None}}
                if sqlite_db.add_data(table_name="mission_record", data = reply):
                    time.sleep(2)
                    while True:
                        d = sqlite_db.query_data_dict(table = "mission_record",
                                    sql_where = "where chat_id = '%s' and completed = 'completed' " % reply["chat_id"])
                        if len(d) > 0:
                            break
                    history = str(d[0]["result"])
            else:
                history = None
        except Exception as ex:
            history = None
            print(ex)
        return (history,)

class WeChat_YoC_LLM:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "OpenAI_api": ("STRING", {"default": "sk-xxxxx", "multiline": False}),
                "model": ("STRING", {"default": "gpt-4o", "multiline": False}),
                "wechat_input": ("STRING", {"forceInput": True}),
                "prompt_template": ("STRING", {"default": "请根据提供的聊天纪录 总结一下说了什么内容", "multiline": True}),
            },

        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("STRING",)
    FUNCTION = "LLM_api"
    CATEGORY = "YoC app/WeChat"

    def LLM_api(self, OpenAI_api, wechat_input, prompt_template, model):
        try:
            input_text = prompt_template + wechat_input
            print(input_text)
            out = chat(api_key = OpenAI_api, model_name = model, input_text = input_text,base_url = "https://api.ephone.ai/v1/")
            return (str(out),)
        except Exception as ex:
            print(ex)
            return (None,)

class WeChat_YoC_Decider:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "wechat_input": ("STRING", {"forceInput": True}),
                "input_key": ("STRING", {"default": "输入关键字段名", "multiline": False}),
                "true_if_value_is": ("STRING", {"default": "True_if_value_is", "multiline": False}),
            },
            "optional": {
                "run": ("BOOLEAN", {"default": True}),
            },

        }

    RETURN_TYPES = ("BOOLEAN","BOOLEAN")
    RETURN_NAMES = ("True","False")
    FUNCTION = "decider"
    CATEGORY = "YoC app/WeChat"

    def decider(self, wechat_input, input_key,true_if_value_is,run):
        if run:
            input_ = eval(wechat_input)
            if input_key in list(input_.keys()):
                key_value = input_[input_key]
                if key_value == true_if_value_is:
                    out1, out2 = True, False
                else:
                    out1, out2 = False, True
                return (out1, out2,)
            return (False, True)
        else:
            return (False, False)

class WeChat_YoC_text:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "wechat_input": ("STRING", {"forceInput": True}),
            },
            "optional": {
                "run": ("BOOLEAN", {"default": True}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("STRING",)
    FUNCTION = "text_content"
    CATEGORY = "YoC app/WeChat"

    def text_content(self, wechat_input, run):
        if run:
            return (wechat_input,)
        else:
            return (None,)

class WeChat_YoC_convert_dict:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "wechat_input": ("STRING", {"forceInput": True}),
                "input_key": ("STRING", {"forceInput": True}),
            },
            "optional": {
                "run": ("BOOLEAN", {"default": True}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("STRING",)
    FUNCTION = "change2dict"
    CATEGORY = "YoC app/WeChat"

    def change2dict(self, wechat_input, input_key,run):

        if run:
            dict_str = {input_key:wechat_input}
            return (str(dict_str),)
        else:
            return (None,)


class WeChat_YoC_dict_concat:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "dict1": ("STRING", {"forceInput": True}),
                "dict2": ("STRING", {"forceInput": True}),
            },
            "optional": {
                "run": ("BOOLEAN", {"default": True}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("STRING",)
    FUNCTION = "concat_dict"
    CATEGORY = "YoC app/WeChat"

    def concat_dict(self, dict1, dict2,run):

        if run:
            # print(dict1)
            # print(dict2)
            dict_str = {**eval(dict1), **eval(dict2)}
            return (str(dict_str),)
        else:
            return (None,)

class WeChat_YoC_mission:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "wechat_input": ("STRING", {"forceInput": True}),
                "mission_input": ("STRING", {"forceInput": True}),
            },
            "optional": {
                "run": ("BOOLEAN", {"default": True}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("STRING",)
    FUNCTION = "get_mission"
    CATEGORY = "YoC app/WeChat"

    def get_mission(self, wechat_input, mission_input, run):
        res = eval(wechat_input)
        if run:
            reply_ = {"chat_id": res["chat_id"], "chat": res["chat"], "room_id": res["room_id"],
                      "receiver_id": res["sender_id"]}
            reply = {**reply_, **{"completed": "init", "modified_time": int(time.time() * 1000000), "mission": "app", "result": eval(mission_input)}}
            if sqlite_db.add_data(table_name="mission_record", data = reply):
                time.sleep(2)
                while True:
                    d = sqlite_db.query_data_dict(table = "mission_record",
                                sql_where = "where chat_id = '%s' and completed = 'completed' " % reply["chat_id"])
                    if len(d) > 0:
                        break
                history = str(d[0]["result"])
        else:
            history = None

        return (history,)
NODE_CLASS_MAPPINGS = {
    "WeChat_YoC_input": WeChat_YoC_input,
    "WeChat_YoC_output": WeChat_YoC_output,
    "WeChat_YoC_history":WeChat_YoC_history,
    "WeChat_YoC_LLM": WeChat_YoC_LLM,
    "WeChat_YoC_Decider": WeChat_YoC_Decider,
    "WeChat_YoC_text": WeChat_YoC_text,
    "WeChat_YoC_convert_dict": WeChat_YoC_convert_dict,
    "WeChat_YoC_dict_concat": WeChat_YoC_dict_concat
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WeChat_input": "WeChat_YoC_input @.@",
    "WeChat_output": "WeChat_YoC_output @.@",
    "WeChat_history": "WeChat_YoC_history @.@",
    "WeChat_LLM":  "WeChat_YoC_LLM @.@",
    "WeChat_Decider": "WeChat_YoC_Decider @.@",
    "WeChat_text": "WeChat_YoC_text @.@",
    "WeChat_convert_dict": "WeChat_YoC_convert_dict @.@",
    "WeChat_dict_concat": "WeChat_YoC_dict_concat @.@",
}

if __name__ == "__main__":
    pass