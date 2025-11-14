#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@ProjectName: Homalos
@FileName   : brokerage_usage_example.py
@Date       : 2025/11/13
@Author     : Lumosylva
@Email      : donnymoving@gmail.com
@Software   : PyCharm
@Description: 期货券商账户系统使用示例
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from src.web.services.brokerage_service import BrokerageService
from src.web.models.brokerage import ConnectionStatus

# 数据库配置
DATABASE_URL = "sqlite+aiosqlite:///./data/homalos_web.db"
engine = create_async_engine(DATABASE_URL)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def example_usage():
    """期货券商账户系统使用示例"""
    print("=" * 60)
    print("🏗️  期货券商账户系统使用示例")
    print("=" * 60)
    
    async with async_session_maker() as session:
        # 初始化服务
        brokerage_service = BrokerageService(session, encryption_key="example_key_123")
        
        try:
            # 1. 创建券商账户
            print("\n📝 1. 创建券商账户")
            account_data = {
                "account_name": "国泰君安期货实盘账户",
                "broker_code": "CTP",
                "broker_name": "国泰君安期货有限公司",
                "account_id": "123456789",
                "investor_id": "123456789",
                "broker_id": "1234",
                "password": "MySecretPassword123!",
                "auth_code": "AUTH123456",
                "app_id": "APP_ID_12345",
                "user_product_info": "Homalos量化交易系统v2.0",
                "account_type": "production",
                "environment": "prod",
                "daily_order_limit": 2000,
                "is_default": True
            }
            
            # 假设用户ID为1
            user_id = 1
            brokerage = await brokerage_service.create_brokerage_account(
                user_id=user_id,
                user_type="user",
                account_data=account_data
            )
            
            print(f"✅ 创建券商账户成功: {brokerage.display_name}")
            print(f"   账户ID: {brokerage.id}")
            print(f"   券商代码: {brokerage.broker_code}")
            print(f"   账户类型: {brokerage.account_type}")
            
            # 2. 获取用户的券商账户列表
            print("\n📋 2. 获取用户券商账户列表")
            accounts = await brokerage_service.get_user_brokerages(user_id, "user", include_inactive=True)
            
            print(f"✅ 找到 {len(accounts)} 个券商账户:")
            for account in accounts:
                status_icon = "🟢" if account.is_active else "🔴"
                default_icon = "⭐" if account.is_default else "  "
                print(f"   {status_icon} {default_icon} {account.display_name}")
                print(f"      ID: {account.id}, 状态: {account.status}, 连接: {account.connection_status}")
            
            # 3. 获取解密后的凭据
            print("\n🔐 3. 获取解密后的凭据")
            password = await brokerage_service.get_decrypted_password(brokerage.id)
            auth_code = await brokerage_service.get_decrypted_auth_code(brokerage.id)
            app_id = await brokerage_service.get_decrypted_app_id(brokerage.id)
            
            print(f"✅ 解密凭据成功:")
            print(f"   密码: {password}")
            print(f"   认证码: {auth_code}")
            print(f"   应用ID: {app_id}")
            
            # 4. 更新连接状态
            print("\n🔗 4. 更新连接状态")
            success = await brokerage_service.update_connection_status(
                brokerage.id,
                ConnectionStatus.CONNECTED
            )
            
            if success:
                print("✅ 连接状态更新成功: 已连接")
            
            # 模拟连接错误
            await brokerage_service.update_connection_status(
                brokerage.id,
                ConnectionStatus.ERROR,
                "网络连接超时"
            )
            print("⚠️  模拟连接错误: 网络连接超时")
            
            # 5. 创建资金快照
            print("\n💰 5. 创建资金快照")
            snapshot_data = {
                "pre_balance": 100000.00,
                "balance": 105000.00,
                "available": 95000.00,
                "commission": 150.50,
                "margin": 10000.00,
                "frozen_margin": 0.00,
                "frozen_commission": 0.00,
                "close_profit": 3000.00,
                "position_profit": 2000.00,
                "withdraw_quota": 95000.00,
                "reserve_balance": 0.00,
                "snapshot_timestamp": datetime.utcnow()
            }
            
            snapshot = await brokerage_service.create_account_snapshot(
                brokerage.id,
                snapshot_data
            )
            
            print(f"✅ 创建资金快照成功:")
            print(f"   快照ID: {snapshot.id}")
            print(f"   账户权益: ¥{snapshot.balance:,.2f}")
            print(f"   可用资金: ¥{snapshot.available:,.2f}")
            print(f"   总盈亏: ¥{snapshot.total_profit:,.2f}")
            print(f"   保证金使用率: {snapshot.used_margin_ratio:.2f}%")
            print(f"   风险度: {snapshot.risk_ratio:.2f}%")
            
            # 6. 获取最新快照
            print("\n📊 6. 获取最新资金快照")
            latest_snapshot = await brokerage_service.get_latest_snapshot(brokerage.id)
            
            if latest_snapshot:
                print(f"✅ 最新快照时间: {latest_snapshot.snapshot_timestamp}")
                print(f"   账户权益: ¥{latest_snapshot.balance:,.2f}")
            
            # 7. 设置默认账户
            print("\n⭐ 7. 设置默认账户")
            success = await brokerage_service.set_default_account(
                brokerage.id, user_id, "user"
            )
            
            if success:
                print("✅ 默认账户设置成功")
            
            print("\n" + "=" * 60)
            print("🎉 期货券商账户系统示例完成！")
            print("=" * 60)
            print("📋 演示功能:")
            print("1. ✅ 创建加密券商账户")
            print("2. ✅ 获取用户账户列表")
            print("3. ✅ 解密敏感凭据")
            print("4. ✅ 更新连接状态")
            print("5. ✅ 创建资金快照")
            print("6. ✅ 查询最新快照")
            print("7. ✅ 设置默认账户")
            print("=" * 60)
            
        except Exception as e:
            print(f"❌ 示例执行失败: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(example_usage())
