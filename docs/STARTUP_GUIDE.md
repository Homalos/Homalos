# Homalos 系统启动指南

## 主要入口脚本

### 🎯 推荐使用: `start_integrated.py`

这是新的统一系统入口，支持交易系统和Web界面的启动管理。

#### 基本用法

```bash
# 启动完整交易系统（默认模式，包含Web界面）
python start_integrated.py

# 启动完整交易系统（不含Web界面）
python start_integrated.py --mode trading --no-web

# 仅启动Web界面
python start_integrated.py --mode web

# 使用自定义配置文件
python start_integrated.py --config config/custom.yaml

# 查看所有选项
python start_integrated.py --help
```

#### 运行模式说明

- **`trading`** (默认): 启动完整交易系统，包含数据处理、策略执行、风险控制、Web界面等所有组件
- **`web`**: 仅启动Web界面，可以连接到已运行的交易系统进行监控

#### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--mode` / `-m` | 运行模式 (trading/web) | trading |
| `--config` / `-c` | 配置文件路径 | config/system.yaml |
| `--no-web` | 禁用Web界面 (仅trading模式) | - |
| `--version` / `-v` | 显示版本信息 | - |
| `--help` / `-h` | 显示帮助信息 | - |

### 🗄️ 数据中心独立启动: `start_data_center.py`

**数据中心需要独立启动，不集成到统一入口中。**

```bash
# 启动数据中心（独立运行）
python start_data_center.py
```

**重要说明**:
- 数据中心具有独立的配置文件和运行逻辑
- 专门用于市场数据收集和存储
- 可以7x24小时独立运行
- 使用独立的 `config/data_center_config.yaml` 配置文件

## 兼容性脚本

### `start_integrated_web.py` (兼容保持)
- 保持向后兼容，等同于 `python start_integrated.py --mode trading`
- 会显示迁移提示，建议使用新的统一入口

### `start_homalos.py` (核心实现)
- 包含 `HomalosSystem` 类的完整实现
- 可直接运行，但建议通过 `start_integrated.py` 启动
- 会显示推荐使用统一入口的提示

## 系统启动架构

```
项目启动架构:
├── start_integrated.py      # 统一入口 (交易系统 + Web界面)
├── start_data_center.py     # 数据中心独立启动
├── start_integrated_web.py  # 兼容性入口
└── start_homalos.py         # 核心系统实现
```

## 推荐的部署方案

### 方案一: 完整系统部署
```bash
# 1. 启动数据中心（后台运行）
nohup python start_data_center.py > logs/data_center.log 2>&1 &

# 2. 启动交易系统（包含Web界面）
python start_integrated.py
```

### 方案二: 分离式部署
```bash
# 1. 启动数据中心
python start_data_center.py

# 2. 启动交易系统（无Web界面）
python start_integrated.py --no-web

# 3. 启动Web界面（另一个终端）
python start_integrated.py --mode web
```

### 方案三: 纯数据收集
```bash
# 仅启动数据中心进行数据收集
python start_data_center.py
```

## 系统启动流程

### 交易系统启动流程
1. **环境检查**: Python版本、配置文件
2. **组件初始化**: 事件总线、服务注册、交易引擎等
3. **网关连接**: CTP/TTS等交易接口
4. **Web服务启动**: 管理界面和API服务（可选）
5. **主循环运行**: 事件处理和状态监控

### 数据中心启动流程
1. **配置加载**: 网关配置和数据中心配置
2. **网关连接**: 建立市场数据连接
3. **数据订阅**: 订阅合约行情数据
4. **存储服务**: 启动数据库写入服务
5. **7x24运行**: 持续数据收集和存储

## 系统监控

启动后可通过以下方式监控系统状态：

- **Web界面**: http://127.0.0.1:8000
- **API文档**: http://127.0.0.1:8000/docs
- **事件监控**: http://127.0.0.1:8000/dashboard
- **日志文件**: logs/ 目录下的日志文件

## 常见问题

### 配置文件缺失
```bash
# 复制示例配置文件
cp config/system.yaml.example config/system.yaml
cp config/brokers.json.example config/brokers.json
cp config/data_center_config.yaml.example config/data_center_config.yaml
# 然后编辑配置文件设置你的参数
```

### 网关连接失败
- 检查网络连接和防火墙设置
- 验证broker配置中的服务器地址和端口
- 确认账户信息正确

### Web界面无法访问
- 检查端口是否被占用 (默认8000)
- 确认防火墙允许端口访问
- 查看日志文件排查具体错误

### 数据中心无法启动
- 检查 `config/data_center_config.yaml` 配置文件
- 确认网关配置正确
- 检查数据库目录权限

## 优化特性

✅ **统一入口**: 一个脚本支持交易系统和Web界面启动  
✅ **独立数据中心**: 数据中心保持独立启动，确保稳定性  
✅ **命令行参数**: 丰富的启动选项和配置  
✅ **错误处理**: 完善的异常处理和用户友好的错误信息  
✅ **兼容性**: 保持与旧脚本的向后兼容  
✅ **日志记录**: 详细的启动和运行日志  
✅ **信号处理**: 优雅的关闭和资源清理  

---

**建议**: 
- 使用 `python start_integrated.py` 启动交易系统和Web界面
- 使用 `python start_data_center.py` 独立启动数据中心
- 根据实际需求选择合适的部署方案