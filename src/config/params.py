#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : params
@Date       : 2025/5/28 00:07
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: description
"""
class Params(object):

    # ----------------------------项目中目录名称----------------------------
    project_name = "Homalos_v2"  # 项目名称
    log_dir_name = "log"  # 日志目录名
    data_dir_name = "data"  # 数据目录名
    # ----------------------------项目中目录名称----------------------------

    # ----------------------------项目参数配置文件----------------------------
    broker_config_filename = "broker_config.json"  # 多源服务器节点配置文件名
    global_config_filename = "global_config.yaml"  # 全局配置文件名
    # ----------------------------项目参数配置文件----------------------------

    # ----------------------------项目信息文件名----------------------------
    instrument_exchange_id_filename = "instrument_exchange_id.json"  # 期货合约与交易所映射信息文件名
    product_info_filename = "product_info.ini"  # 合约乘数及手续费信息文件名
    holidays_filename = "_holidays.json"  # 节假日文件后缀名称
    # ----------------------------项目信息文件名----------------------------

    # ------------------------------日志类常量------------------------------
    file_format = "%Y%m%d"  # 日志文件名格式
    log_time_format = "%Y-%m-%d %H:%M:%S.%f"  # 日志文件中时间格式
    print_time_format = "%Y-%m-%d %H:%M:%S.%f"  # 控制台打印的时间格式
    # ------------------------------日志类常量------------------------------

    # -------------------------------时间常量-------------------------------
    TIME_SIXTY_SECONDS = 60  # 60秒
    # -------------------------------时间常量-------------------------------

if __name__ == '__main__':
    print(Params.data_dir_name)
