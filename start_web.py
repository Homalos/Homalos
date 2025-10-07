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
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "src.web.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

