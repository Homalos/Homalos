#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : get_path.py
@Date       : 2025/9/9 21:41
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 路径工具类

常用目录快捷方法:
get_config_dir() → 获取配置目录
get_logs_dir() → 获取日志目录
get_data_dir() → 获取数据目录
get_src_dir() → 获取源代码目录

join_path(*args) → 基于项目目录拼接路径
ensure_dir_exists(path) → 确保目录存在，不存在则创建
"""
from pathlib import Path


PROJECT_NAME = "Homalos"


class GetPath:
    """
    路径工具类，使用 pathlib.Path 实现路径操作。
    """

    def __init__(self):
        """
        初始化路径工具类，自动查找项目根目录。
        """
        self._current_dir = Path.cwd()
        
        # 向上查找项目根目录
        current = self._current_dir
        while current.name != PROJECT_NAME and current.parent != current:
            current = current.parent
            
        if current.name == PROJECT_NAME:
            self._project_dir = current
        else:
            # 如果没有找到项目名称的目录，使用当前工作目录
            self._project_dir = self._current_dir

    def get_project_dir(self) -> Path:
        """
        获取项目目录的路径。
        
        Returns:
            Path: 项目目录的 Path 对象。
        """
        return self._project_dir

    def get_project_dir_str(self) -> str:
        """
        获取项目目录的字符串路径。
        
        Returns:
            str: 项目目录的字符串路径。
        """
        return str(self._project_dir)

    def get_current_dir(self) -> Path:
        """
        获取当前工作目录。
        
        Returns:
            Path: 当前工作目录的 Path 对象。
        """
        return self._current_dir

    def get_current_dir_str(self) -> str:
        """
        获取当前工作目录的字符串路径。
        
        Returns:
            str: 当前工作目录的字符串路径。
        """
        return str(self._current_dir)

    def set_project_dir(self, project_dir: str | Path) -> None:
        """
        设置项目的根目录。
        
        Args:
            project_dir (str | Path): 项目的根目录路径。
        """
        if isinstance(project_dir, str):
            self._project_dir = Path(project_dir)
        else:
            self._project_dir = project_dir

    def get_config_dir(self) -> Path:
        """
        获取配置文件目录。
        
        Returns:
            Path: 配置文件目录的 Path 对象。
        """
        return self._project_dir / "config"

    def get_logs_dir(self) -> Path:
        """
        获取日志文件目录。
        
        Returns:
            Path: 日志文件目录的 Path 对象。
        """
        return self._project_dir / "logs"

    def get_data_dir(self) -> Path:
        """
        获取数据文件目录。
        
        Returns:
            Path: 数据文件目录的 Path 对象。
        """
        return self._project_dir / "data"

    def get_src_dir(self) -> Path:
        """
        获取源代码目录。
        
        Returns:
            Path: 源代码目录的 Path 对象。
        """
        return self._project_dir / "src"

    def join_path(self, *args) -> Path:
        """
        基于项目目录拼接路径。
        
        Args:
            *args: 路径组件。
            
        Returns:
            Path: 拼接后的 Path 对象。
        """
        return self._project_dir.joinpath(*args)

    @staticmethod
    def ensure_dir_exists(path: str | Path) -> Path:
        """
        确保目录存在，如果不存在则创建。
        
        Args:
            path (str | Path): 目录路径。
            
        Returns:
            Path: 目录的 Path 对象。
        """
        if isinstance(path, str):
            path = Path(path)
        
        path.mkdir(parents=True, exist_ok=True)
        return path


get_path_ins = GetPath()
