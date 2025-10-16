#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : start_web.py
@Date       : 2025/10/8
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 启动Web服务
"""
import os
import uvicorn

if __name__ == "__main__":
    # 启用SSE日志流
    os.environ['ENABLE_SSE_LOGS'] = 'true'
    
    uvicorn.run(
        "src.web.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # 禁用Uvicorn自动重载，使用策略管理器的Watchdog
        log_level="info"
    )

