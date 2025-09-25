#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : baidu_yun.py
@Date       : 2025/9/25 21:38
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 百度云工具类(百度网盘)
"""
import sys

from bypy import ByPy

from src.constants import BAIDU_YUN_FILES
from src.utils.get_path import get_path_ins


class BaiDuYun(object):

    def __init__(self):
        self.baidu_yun = ByPy()
        self.file_list: list = []
        self.dir_list: list = []
        self.txt_filename = str(get_path_ins.get_config_dir() / BAIDU_YUN_FILES)  # 百度云列表文件存放位置

    def mkdir(self, dir_name):
        # 百度网盘创建远程文件夹
        self.baidu_yun.mkdir(remotepath=dir_name)

    def upload(self, file_name, remote_path):
        # 上传某一文件到百度云网盘对应的远程文件夹
        # ondup中参数代表复制文件，默认值为'overwrite'，指定'newcopy'不会覆盖重复文件
        ret_code = self.baidu_yun.upload(localpath=file_name, remotepath=remote_path, ondup='newcopy')
        return ret_code

    def update_list(self, remote_path):
        # 将文件列表写入到TXT文档
        root = sys.stdout
        output_content = open(self.txt_filename, "w", encoding="utf-8")
        sys.stdout = output_content

        # 查询百度云列表，并写入文档
        self.baidu_yun.list(remotepath=remote_path)
        # 将print还原
        sys.stdout = root
        output_content.close()

        # 读取文档，并返回文件列表
        txt_file = open(self.txt_filename, "r", encoding="utf-8")
        for line in txt_file:
            line_list: list = line.split(' ')
            if line_list[0] == 'D':  # 获取按空格分割后的第一个部分(D代表是文件夹)
                self.dir_list.append(line_list)
            elif line_list[0] == 'F':  # 获取按空格分割后的第一个部分(F代表是文件)
                self.file_list.append(line_list)
        txt_file.close()

    def is_file_in_baidu_yun(self, filename):
        """
        判断文件是否在百度云中
        :param filename:
        :return:
        """
        for file_info in self.file_list:
            if filename == file_info[1]:
                return True
        return False

    def is_dir_in_baidu_yun(self, dirname):
        """
        判断文件夹是否在百度云中
        :param dirname:
        :return:
        """
        for dir_info in self.dir_list:
            if dirname == dir_info[1]:
                return True
        return False

    def get_filesize(self, filename):
        """
        获取文件大小
        :param filename:
        :return:
        """
        if self.is_file_in_baidu_yun(filename):
            for file_info in self.file_list:
                if filename == file_info[1]:
                    a = int(file_info[2])
                    return round(int(file_info[2]) / 1024 / 1024, 2)
        else:
            return '{}未在百度云中'.format(filename)


if __name__ == "__main__":
    pass
    # baiDuYunSys = BaiDuYun()
    # baiDuYunSys.upload("ceshi.txt", "")
    # baiDuYunSys.update_list("")
    # res = baiDuYunSys.is_file_in_baidu_yun("ceshi.txt")
    # print(res)
