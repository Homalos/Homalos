#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : func.py
@Date       : 2025/10/11 16:22
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 业务公共函数
"""
import socket


def get_ip_port(server_front: str) -> (str, str):
    """
    获取IP和端口

    Args:
        server_front: 服务器前置地址

    Returns:
        tuple: ip, port
    """
    server_front = server_front.replace('tcp://', '')
    st = server_front.split(':')
    return st[0], st[1]

def is_open(ip, port) -> bool:
    """
    使用socket判断是否开盘

    Args:
        ip: ip
        port: 端口

    Returns:
        bool: 是否开盘
    """
    socket_obj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        socket_obj.connect((ip, int(port)))
        socket_obj.shutdown(2)
        return True
    except Exception as e:
        return False
