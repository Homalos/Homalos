#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : email_notifier.py
@Date       : 2025/10/16 18:15
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 邮件通知器 - 发送告警邮件
"""
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any
from datetime import datetime

from src.utils.log.logger import get_logger


class EmailNotifier:
    """
    邮件通知器
    
    功能：
    - 读取系统设置中的邮件配置
    - 发送告警邮件（异步）
    - 邮件模板渲染
    """
    
    def __init__(self, config_getter):
        """
        Args:
            config_getter: 获取邮件配置的回调函数 async () -> dict
        """
        self.logger = get_logger("EmailNotifier")
        self.config_getter = config_getter
    
    async def send_alarm(self, alarm_data: Dict[str, Any]):
        """
        发送告警邮件
        
        Args:
            alarm_data: 告警数据字典
        """
        try:
            # 获取邮件配置
            config = await self.config_getter()
            
            if not config or not config.get("email_enabled"):
                self.logger.debug("邮件通知未启用，跳过发送")
                return
            
            # 只发送 error 和 critical 级别的告警邮件
            severity = alarm_data.get("severity", "info")
            if severity not in ["error", "critical"]:
                self.logger.debug(f"告警级别 {severity} 不发送邮件")
                return
            
            smtp_server = config.get("smtp_server")
            smtp_port = config.get("smtp_port", 587)
            smtp_user = config.get("smtp_user")
            smtp_password = config.get("smtp_password")
            from_email = config.get("from_email", smtp_user)
            to_emails = config.get("to_emails", [])
            
            if not all([smtp_server, smtp_user, smtp_password, to_emails]):
                self.logger.warning("邮件配置不完整，无法发送邮件")
                return
            
            # 渲染邮件内容
            subject, body = self._render_email_template(alarm_data)
            
            # 在线程池中执行邮件发送（避免阻塞）
            await asyncio.to_thread(
                self._send_email_sync,
                smtp_server, smtp_port, smtp_user, smtp_password,
                from_email, to_emails, subject, body
            )
            
            self.logger.info(f"告警邮件已发送: {alarm_data['alarm_id']}")
        
        except Exception as e:
            self.logger.error(f"发送告警邮件失败: {e}", exc_info=True)
    
    def _render_email_template(self, alarm_data: Dict[str, Any]) -> tuple:
        """
        渲染邮件模板
        
        Args:
            alarm_data: 告警数据
        
        Returns:
            tuple: (subject, body)
        """
        severity = alarm_data.get("severity", "info").upper()
        alarm_type = alarm_data.get("alarm_type", "unknown")
        message = alarm_data.get("message", "")
        source = alarm_data.get("source", "")
        target = alarm_data.get("target", "")
        created_at = alarm_data.get("created_at", "")
        alarm_id = alarm_data.get("alarm_id", "")
        
        # 严重程度对应的emoji
        severity_emoji = {
            "INFO": "ℹ️",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "CRITICAL": "🚨"
        }
        emoji = severity_emoji.get(severity, "📢")
        
        # 邮件主题
        subject = f"{emoji} [Homalos告警] {severity} - {alarm_type}"
        
        # 邮件正文（HTML格式）
        body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #f8f9fa; padding: 15px; border-left: 4px solid #dc3545; }}
                .severity-critical {{ border-left-color: #dc3545; }}
                .severity-error {{ border-left-color: #fd7e14; }}
                .severity-warning {{ border-left-color: #ffc107; }}
                .severity-info {{ border-left-color: #17a2b8; }}
                .content {{ padding: 20px 0; }}
                .field {{ margin-bottom: 10px; }}
                .field-label {{ font-weight: bold; color: #666; }}
                .field-value {{ color: #333; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #999; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header severity-{severity.lower()}">
                    <h2 style="margin: 0;">{emoji} Homalos 系统告警</h2>
                </div>
                
                <div class="content">
                    <div class="field">
                        <span class="field-label">严重程度：</span>
                        <span class="field-value" style="color: {'#dc3545' if severity == 'CRITICAL' else '#fd7e14' if severity == 'ERROR' else '#ffc107'};">
                            {severity}
                        </span>
                    </div>
                    
                    <div class="field">
                        <span class="field-label">告警类型：</span>
                        <span class="field-value">{alarm_type}</span>
                    </div>
                    
                    <div class="field">
                        <span class="field-label">告警源：</span>
                        <span class="field-value">{source}</span>
                    </div>
                    
                    {f'<div class="field"><span class="field-label">目标对象：</span><span class="field-value">{target}</span></div>' if target else ''}
                    
                    <div class="field">
                        <span class="field-label">告警消息：</span>
                        <div class="field-value" style="background-color: #f8f9fa; padding: 10px; margin-top: 5px; border-radius: 4px;">
                            {message}
                        </div>
                    </div>
                    
                    <div class="field">
                        <span class="field-label">触发时间：</span>
                        <span class="field-value">{created_at}</span>
                    </div>
                    
                    <div class="field">
                        <span class="field-label">告警ID：</span>
                        <span class="field-value" style="font-family: monospace; font-size: 12px;">{alarm_id}</span>
                    </div>
                </div>
                
                <div class="footer">
                    <p>此邮件由 Homalos 期货量化交易系统自动发送，请勿直接回复。</p>
                    <p>如需处理告警，请登录系统控制台。</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return subject, body
    
    def _send_email_sync(
        self,
        smtp_server: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        from_email: str,
        to_emails: list,
        subject: str,
        body: str
    ):
        """
        同步发送邮件（在线程池中执行）
        
        Args:
            smtp_server: SMTP服务器
            smtp_port: SMTP端口
            smtp_user: SMTP用户名
            smtp_password: SMTP密码
            from_email: 发件人邮箱
            to_emails: 收件人邮箱列表
            subject: 邮件主题
            body: 邮件正文（HTML）
        """
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = ', '.join(to_emails)
        
        # 添加HTML正文
        html_part = MIMEText(body, 'html', 'utf-8')
        msg.attach(html_part)
        
        # 发送邮件
        with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)

