#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : get_path
@Date       : 2025/5/28 00:25
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: description
"""
import os

from src.config.params import Params


class GetPath(object):

    def __init__(self):
        """
        初始化方法。
        """
        self._current_dir = os.getcwd()

        while os.path.basename(self._current_dir) != Params.project_name:
            self._current_dir = os.path.abspath(os.path.join(self._current_dir, '..'))
        self._project_dir = self._current_dir


    def get_project_dir(self):
        """
        获取项目目录的路径。
        Returns:
            str: 项目目录的路径。
        """
        return self._project_dir

    def get_current_dir(self):
        """
        获取当前目录。
        Returns:
            str: 当前目录的路径。
        """
        return self._current_dir

    def set_project_dir(self, project_dir):
        """
        设置项目的根目录。
        Args:
            project_dir (str): 项目的根目录路径。
        Returns:
            None
        """
        self._project_dir = project_dir


if __name__ == '__main__':
    print(os.getcwd())
    path = GetPath()
    print(path.get_project_dir())