#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos_v2
@FileName   : test_colorama
@Date       : 2025/7/30 09:56
@Author     : Donny
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: description
"""
from colorama import Fore, Style, Back

print(Fore.RED + Back.WHITE + Style.BRIGHT + '红字 + 白背景 + 高亮')
print(Style.RESET_ALL + '样式已重置')
