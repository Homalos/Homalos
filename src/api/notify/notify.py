#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : notify.py
@Date       : 2025/10/11 16:29
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 通知类
"""
import json
import time
import traceback
from threading import Thread

import requests
from requests_toolbelt import MultipartEncoder

from src.system_config import Config
from src.utils.log import get_logger
from src.utils.time import time_module_ins


class Notify(object):
    """
    通知类
    微信教程地址：https://www.bilibili.com/video/BV1P94y1Z7DE
    """
    def __init__(self):
        self.wx_agent_id: int = Config.wx_agent_id
        self.wx_secret: str = Config.wx_secret
        self.wx_corp_id: str = Config.wx_corp_id
        self.notify_type: dict[str, bool] = Config.notify_type
        self.url_wx_gettoken: str = Config.url_wx_gettoken
        self.url_wx_media_upload: str = Config.url_wx_media_upload
        self.url_wx_send: str = Config.url_wx_send
        self.access_token: str = self.get_token()
        self.filepath = ""
        self.filename = ""
        self.media_id = ""
        # 钉钉相关
        self.ding_app_name: str = Config.ding_app_name
        self.ding_address: str = Config.ding_address
        self.logger = get_logger(__name__)

        if self.notify_type.get("weixin"):
            t = Thread(target=self.update_token)
            # 将此线程设置成后台线程
            t.daemon = True
            t.name = '更新微信token-守护线程'
            t.start()

    def get_token(self) -> str:
        """
        获取凭证，每个凭证有效期2小时，不能频繁调用

        Returns:
            str: token
        """
        url = self.url_wx_gettoken
        data = {
            "corpid": self.wx_corp_id,
            "corpsecret": self.wx_secret
        }
        r = requests.get(url=url, params=data)
        token = r.json()['access_token']
        return token

    def update_token(self) -> None:
        """
        更新token

        Returns:
            None
        """
        while True:
            try:
                time.sleep(3600)
                self.access_token = self.get_token()
            except Exception as e:
                self.logger.exception(traceback.format_exc())
                self.logger.exception(e)

    def get_media_id(self) -> dict:
        """
        返回media信息

        Returns:
            dict: media
        """
        filepath = self.filepath
        filename = self.filename
        post_file_url = f"{self.url_wx_media_upload}?access_token={self.access_token}&type=file"
        m = MultipartEncoder(
            fields={filename: ('file', open(filepath + filename, 'rb'), 'text/plain')},
        )
        ret = requests.post(url=post_file_url, data=m, headers={'Content-Type': m.content_type})
        return json.loads(ret.text)

    def _upload_file(self, file) -> str:
        """
        文件上传到临时媒体库，返回media_id

        Args:
            file: 文件路径

        Returns:
            str: media_id
        """
        url = f"{self.url_wx_media_upload}?access_token={self.access_token}&type=file"
        data = {"file": open(file, "rb")}
        ret = requests.post(url, files=data)
        if "Error-Code" in ret.headers.keys():
            if ret.headers['Error-Code'] != '0':
                print('发送文件时获取media_id失败: {}'.format(json.loads(ret.text)['errmsg']))
                return ''
        return ret.json()['media_id']

    def send_img(self, filepath, filename):
        """
        发送图片

        Args:
            filepath:
            filename:

        Returns:

        """
        if self.notify_type.get("weixin"):
            self.filepath = filepath
            self.filename = filename
            ret = self.get_media_id()
            if "Error-Code" in ret.keys():
                if ret['errcode'] != 0:
                    self.logger.error('发送图片时获取media_id失败：{}'.format(ret['errmsg']))
                    return ret
            self.media_id = ret['media_id']

            data = {
                "touser": "@all",
                "toparty": "@all",
                "msgtype": "image",
                "agentid": self.wx_agent_id,
                "image": {
                    "media_id": self.media_id
                },
                "safe": 0
            }
            response = requests.post(
                f"{self.url_wx_send}?access_token={self.access_token}",
                data=json.dumps(data))
            if response.headers['Error-Code'] != '0':
                self.logger.error('发送图片到微信失败：{}'.format(response.headers['Error-Msg']))
            return response

    def send_file(self, file):
        """
        发送文件

        Args:
            file:

        Returns:

        """
        ret = None
        if self.notify_type.get("weixin"):
            try:
                media_id = self._upload_file(file)  # 先将文件上传至临时媒体库
                url = f"{self.url_wx_send}?access_token={self.access_token}"
                send_values = {
                    "touser": "@all",
                    "msgtype": "file",
                    "agentid": self.wx_agent_id,
                    "file": {
                        "media_id": media_id
                    },
                }
                send_message = (bytes(json.dumps(send_values), 'utf-8'))
                response = requests.post(url, send_message)
                if response.headers['Error-Code'] != '0':
                    self.logger.error('发送文件到微信失败：{}'.format(response.headers['Error-Msg']))
            except Exception as e:
                self.logger.exception(traceback.format_exc())
                self.logger.exception(e)
            return ret
        elif self.notify_type.get("dingding"):
            self.logger.error('无法通过python发送文件到钉钉: {} '.format(file))


    def send_txt(self, content):
        """
        发送文本内容

        Args:
            content: 文本内容

        Returns:

        """
        if self.notify_type.get("weixin"):
            data = {
                "touser": "@all",
                "toparty": "@all",
                "agentid": self.wx_agent_id,
                "msgtype": "text",  # 消息类型，此时固定为text
                "text": {
                    "content": content,  # 文本内容，最长不超过2048个字节，必须是utf8编码
                    "mentioned_list": ["@all"],
                    # userid的列表，提醒群中的指定成员(@某个成员)，@all表示提醒所有人，如果开发者获取不到userid，可以使用mentioned_mobile_list
                    "mentioned_mobile_list": ["@all"]  # 手机号列表，提醒手机号对应的群成员(@某个成员)，@all表示提醒所有人
                }
            }
            ret = requests.post(
                f"{self.url_wx_send}?access_token={self.access_token}",
                data=json.dumps(data))
            if ret.headers['Error-Code'] != '0':
                self.logger.error('发送消息到微信失败：{}'.format(ret.headers['Error-Msg']))
            return ret
        elif self.notify_type.get("dingding"):
            # 请求的URL，WebHook地址
            webhook = self.ding_address  # 机器人的WebHook
            # 构建请求头部
            header = {
                "Content-Type": "application/json",
                "Charset": "UTF-8"
            }
            # 构建请求数据
            tex = "通知：" + content  # 写要发的通知内容
            message = {

                "msgtype": "text",
                "text": {
                    "content": tex
                },
                "at": {

                    "isAtAll": True  # False是不@，改为True是@所有人
                }

            }
            # 对请求的数据进行json封装
            message_json = json.dumps(message)
            # 发送请求
            info = requests.post(url=webhook, data=message_json, headers=header)
            if info.status_code != 200:
                self.logger.error('发送消息到钉钉失败：{}'.format(info.content))

        elif self.notify_type.get("email"):
            self.logger.info(content)

    def send_time_txt(self, content):
        """
        发送文本内容

        Args:
            content: 文本内容

        Returns:

        """
        ret = 0
        try:
            ret = self.send_txt('{}: {}'.format(time_module_ins.strf_now_time('%Y-%m-%d %H:%M:%S.%f'), content))
        except Exception as e:
            self.logger.exception(traceback.format_exc())
            self.logger.exception(e)
        return ret

    def send_markdown(self, content):
        """
        发送markdown

        Args:
            content: markdown

        Returns:

        """
        send_data = {
            "touser": "@all",
            "toparty": "@all",
            "agentid": self.wx_agent_id,
            "msgtype": "markdown",  # 消息类型，此时固定为markdown
            "markdown": {
                "content": content
            }
        }
        response = requests.post(f"{self.url_wx_send}?access_token={self.access_token}",
            data=json.dumps(send_data))
        if response.headers['Error-Code'] != '0':
            self.logger.error('发送MarkDown消息到微信失败：{}'.format(response.headers['Error-Msg']))
        return response


if __name__ == "__main__":
    wxSys = Notify()

    wxSys.send_txt("利用微信框架发送")
    # time.sleep(1)
    # wxSys.sendImg("./", "1.png")
    # time.sleep(1)

    # wxSys.send_file("1.txt")


    # i = 0
    # while True:
    #     wxSys.send_time_txt('检测网络是否通畅')
    #     print(i)
    #     time.sleep(60)
    #     i = i+1