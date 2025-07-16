# Homalos 数据中心使用指南

## 概述

Homalos 数据中心是一个高性能的金融市场数据处理系统，支持实时行情数据接收、存储、查询和K线合成功能。

## 主要功能

### 🚀 核心特性

- **实时行情接收**: 支持CTP等多种行情网关
- **高效数据存储**: SQLite + Parquet 双重存储方案
- **K线合成**: 支持多周期K线实时合成（1分钟、5分钟、15分钟等）
- **批量写入**: 高性能批量数据写入，减少I/O开销
- **事件驱动**: 基于事件总线的松耦合架构
- **线程安全**: 多线程环境下的数据安全保障

### 📊 数据管理

- **Tick数据**: 实时逐笔行情数据
- **Bar数据**: 多周期K线数据
- **数据查询**: 灵活的历史数据查询接口
- **数据持久化**: SQLite数据库 + Parquet文件双重备份

## 快速开始

### 1. 环境准备

```bash
# 激活虚拟环境
.venv\Scripts\activate

# 安装依赖（如果需要）
uv sync
```

### 2. 配置文件

创建或修改 `config/market_symbols.json` 文件：

```json
{
  "symbols": ["RB2510", "FG2510", "HC2510"]
}
```

### 3. 运行测试

```bash
# 运行数据中心测试
python test_data_center.py
```

### 4. 启动数据中心

```bash
# 简单启动（使用默认配置）
python start_data_center_simple.py

# 或使用完整启动脚本
python start_data_center.py
```

## 配置说明

### 数据库配置

```python
config = {
    'database': {
        'path': 'data/market_data.db',        # SQLite数据库路径
        'parquet_path': 'data/parquet',       # Parquet文件存储路径
        'tick_batch_size': 1000,              # Tick数据批量大小
        'bar_batch_size': 500,                # Bar数据批量大小
        'flush_interval': 5                   # 刷新间隔（秒）
    }
}
```

### K线周期配置

```python
config = {
    'bar_intervals': [1, 5, 15, 30, 60]  # 支持的K线周期（分钟）
}
```

### 网关配置

```python
config = {
    'gateway': {
        'user_id': 'your_user_id',
        'password': 'your_password',
        'broker_id': '9999',
        'md_address': 'tcp://180.168.146.187:10131',
        'appid': 'simnow_client_test',
        'auth_code': '0000000000000000'
    }
}
```

## API 使用

### 基本使用

```python
from src.core.event_bus import EventBus
from src.services.data_center import DataCenter

# 创建事件总线
event_bus = EventBus("my_app")
event_bus.start()

# 创建数据中心
config = {...}  # 你的配置
data_center = DataCenter(config, event_bus)

# 启动数据中心
data_center.start()

# 查询数据
tick_data = data_center.database.query_tick_data(
    symbol='RB2510',
    exchange='SHFE',
    limit=100
)

bar_data = data_center.database.query_bar_data(
    symbol='RB2510',
    exchange='SHFE',
    interval='1m',
    limit=100
)

# 获取状态
status = data_center.get_status()
print(status)

# 停止数据中心
data_center.stop()
event_bus.stop()
```

### 事件监听

```python
from src.core.event import EventType

# 监听Tick数据事件
def on_tick_data(event):
    tick_data = event.data
    print(f"收到Tick: {tick_data['symbol']} - {tick_data['last_price']}")

event_bus.subscribe(EventType.TICK_DATA, on_tick_data)

# 监听K线数据事件
def on_bar_data(event):
    bar_data = event.data
    print(f"收到K线: {bar_data['symbol']} - {bar_data['close_price']}")

event_bus.subscribe(EventType.MARKET_BAR_RAW, on_bar_data)
```

## 数据结构

### Tick数据格式

```python
tick_data = {
    'symbol': 'RB2510',
    'exchange': 'SHFE',
    'datetime': '2025-01-01T09:00:00',
    'last_price': 3500.0,
    'volume': 1000,
    'turnover': 3500000.0,
    'open_interest': 50000,
    'bid_price_1': 3499.0,
    'ask_price_1': 3501.0,
    'bid_volume_1': 10,
    'ask_volume_1': 15
}
```

### Bar数据格式

```python
bar_data = {
    'symbol': 'RB2510',
    'exchange': 'SHFE',
    'interval': '1m',
    'datetime': '2025-01-01T09:00:00',
    'open_price': 3500.0,
    'high_price': 3510.0,
    'low_price': 3495.0,
    'close_price': 3505.0,
    'volume': 1000,
    'turnover': 3500000.0,
    'open_interest': 50000
}
```

## 性能优化

### 批量写入

数据中心使用批量写入机制来提高性能：

- Tick数据达到1000条时自动批量写入
- Bar数据达到500条时自动批量写入
- 每5秒强制刷新一次缓存

### 双重存储

- **SQLite**: 用于快速查询和事务处理
- **Parquet**: 用于长期存储和大数据分析

### 多线程处理

- 独立的SQLite写入线程
- 独立的Parquet写入线程
- 主线程专注于数据接收和处理

## 监控和调试

### 状态监控

```python
status = data_center.get_status()
print(f"运行状态: {status['is_running']}")
print(f"连接状态: {status['is_connected']}")
print(f"Tick计数: {status['stats']['tick_count']}")
print(f"Bar计数: {status['stats']['bar_count']}")
```

### 日志配置

系统使用loguru进行日志管理，日志级别和格式可在 `src/core/logger.py` 中配置。

## 故障排除

### 常见问题

1. **数据库连接失败**
   - 检查数据库文件路径是否正确
   - 确保有足够的磁盘空间

2. **网关连接失败**
   - 检查网络连接
   - 验证账户信息是否正确
   - 确认行情服务器地址

3. **数据写入缓慢**
   - 调整批量大小参数
   - 检查磁盘I/O性能
   - 考虑使用SSD存储

### 调试模式

在测试环境中，可以使用 `test_data_center.py` 进行功能验证，该脚本会：

- 测试数据库连接
- 验证数据写入功能
- 检查数据查询功能
- 测试K线合成功能

## 扩展开发

### 添加新的网关

1. 继承 `BaseGateway` 类
2. 实现必要的接口方法
3. 在数据中心配置中注册新网关

### 自定义事件处理

1. 定义新的事件类型
2. 在相应位置发布事件
3. 订阅并处理事件

### 数据格式扩展

1. 修改数据库表结构
2. 更新数据转换逻辑
3. 调整查询接口

## 许可证

本项目遵循项目根目录下的LICENSE文件中指定的许可证。

## 支持

如有问题或建议，请提交Issue或联系开发团队。