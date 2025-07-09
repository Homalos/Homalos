#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : path
@Date       : 2025/5/28 00:09
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: description
"""
from pathlib import Path

from src.config.params import Params
from src.util.path import get_path_ins


class GlobalPath(object):
    # ------------------常用目录完整路径---------------------------------------------------------
    # 项目根路径
    project_root_path = Path(get_path_ins.get_project_dir())

    # log，日志目录完整路径
    log_dir_path = project_root_path / Params.log_dir_name
    # data，数据目录完整路径
    data_dir_path = project_root_path / Params.data_dir_name

    # 配置目录完整路径(用于保存配置文件: instrument_exchange_id.json、product_info.ini、2025_holidays.json等)
    project_files_path = project_root_path / "config"

    # config_files，holiday文件存放目录完整路径
    holiday_dir_path = project_files_path
    # ------------------常用目录完整路径---------------------------------------------------------

    # ------------------产品信息文件完整路径------------------------------------------------------
    # config_files/instrument_exchange_id.json，交易所配置信息文件完整路径
    instrument_exchange_id_filepath = project_files_path / Params.instrument_exchange_id_filename

    # config_files/product_info.ini，产品信息文件完整路径
    product_info_filepath = project_files_path / Params.product_info_filename

    # ------------------产品信息文件完整路径------------------------------------------------------

    # ------------------运行及回测配置文件完整路径-------------------------------------------------
    # config_files/global_config.yaml，全局配置文件完整路径
    global_config_filepath = project_files_path / Params.global_config_filename

    broker_config_filepath = project_files_path / Params.broker_config_filename
    # ------------------运行及回测配置文件完整路径-------------------------------------------------

