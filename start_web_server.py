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
import logging

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # 启用SSE日志流
    os.environ['ENABLE_SSE_LOGS'] = 'true'
    
    try:
        # 直接使用 uvicorn.run()，配置优雅关闭超时
        # 注意：在Windows上，第一次Ctrl+C会触发优雅关闭（最多10秒）
        #      如果10秒内无法完成，需要第二次Ctrl+C强制退出
        uvicorn.run(
            "src.web.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,  # 启用热重载，代码修改后自动重启
            reload_dirs=["src"],  # 监控src目录的变化
            log_level="info",
            timeout_graceful_shutdown=10,  # 优雅关闭超时10秒（Windows推荐设置）
        )
    except KeyboardInterrupt:
        logger.info("检测到 KeyboardInterrupt，正在优雅关闭...")
    except Exception as e:
        logger.error(f"服务器异常: {e}", exc_info=True)
    finally:
        logger.info("Web服务已停止")

