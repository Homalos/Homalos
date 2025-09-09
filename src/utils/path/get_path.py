#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : get_path.py
@Date       : 2025/9/9 21:41
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 路径工具
"""
import os

from src.constants import PROJECT_NAME


class GetPath(object):

    def __init__(self):

        self._current_dir = os.getcwd()

        while os.path.basename(self._current_dir) != PROJECT_NAME:
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
