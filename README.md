# Homalos——基于Python的期货量化交易系统

## 项目整体架构

```reStructuredText
Homalos_v2/
├── 📁 src/                   # 核心源代码目录
│   ├── 📁 config/            # 配置管理
│   ├── 📁 core/              # 系统核心模块
│   ├── 📁 ctp/               # CTP接口模块
│   ├── 📁 services/          # 服务模块
│   ├── 📁 strategies/        # 策略实例模块
│   ├── 📁 tts/               # TTS接口模块
│   ├── 📁 util/              # TTS接口模块
│   └── 📁 web/               # Web界面
├── 📁 config/                # 配置文件
├── 📁 data/                  # 数据存储
├── 📁 log/                   # 日志存储
└── 📁 test/                  # 测试脚本目录
```

## 核心技术栈

**构建系统:**

- **Meson + Ninja**: 现代化的C++扩展构建系统
- **Pybind11**: Python-C++绑定
- **Hatch**: Python项目管理和打包
- uv：我们选择使用现代化的`uv`作为Python包管理器，它提供更快的安装速度和更智能的依赖解析能力。

**主要依赖:**

- **数据处理**: NumPy, Pandas, Polars
- **技术分析**: TA-Lib
- **日志系统**: Loguru

### 核心模块详解

#### 1. **Core 核心模块** (`src/core/`)

- **event.py**: 事件对象
- **event_bus.py**: 高性能事件总线
- **gateway.py**: 抽象网关类
- **object.py**: 基本数据结构
- **logger.py**: 日志模块

#### 2. **策略模块** (`src/strategies/`)

- **base_strategy.py**: 策略基类
- **moving_average_strategy.py**: 移动平均策略

#### 3. **交易接口模块**

- **CTP模块** (`src/ctp/`): 上期技术CTP接口
- **TTS模块** (`src/tts/`): TTS交易接口

两个模块都包含：

- `api/`: C++扩展模块 (.pyd文件)
- `gateway/`: Python网关实现
- `meson.build`: 构建配置

#### 4. **配置系统** (`config_files/`)

- **system.yaml**: 全局系统配置
- **global_config.yaml**: 全局系统配置
- **broker_config.json**: 券商配置
- **2024/2025_holidays.json**: 交易日历
- **instrument_exchange_id.json**: 合约交易所映射

### 🚀 构建系统特点

1. **统一构建**: 使用Meson构建系统管理C++扩展
2. **跨平台支持**: Windows/Linux/Mac
3. **增量编译**: 支持快速重新构建
4. **一键构建**: `python build.py`

### 系统特色

1. **事件驱动架构**: 基于EventEngine的异步事件处理
2. **多接口支持**: 同时支持CTP和TTS交易接口
3. **策略框架**: 完整的策略生命周期管理
4. **配置化设计**: 灵活的配置文件系统
5. **现代化工具链**: 使用最新的Python构建和开发工具

## 构建流程

删除旧的构建：

```bash
rmdir /s /q build
```

第三方扩展构建：

```bash
meson compile -C build
```

这个项目使用了`meson-python`作为构建后端，我需要确保构建系统配置正确：

## 总结

使用 `hatch build` 命令来构建您的项目。建议在将来的构建中使用：

- `hatch build` - 正常构建
- `hatch build --clean` - 清理并重新构建  
- `hatch build -t wheel` - 只构建wheel包
- `hatch build -t sdist` - 只构建源码包

## 主要成就

**✅ 解决的关键问题:**

1. **编译器参数冲突**: 移除了`/MT`参数，避免与Python默认的`/MD`冲突
2. **头文件路径错误**: 将include路径从`api/include/ctp`和`api/include/tts`调整为`api/include`
3. **C++17废弃警告**: 添加了`-D_SILENCE_CXX17_CODECVT_HEADER_DEPRECATION_WARNING`参数

**✅ 成功生成的扩展模块:**

- `ctpmd.cp312-win_amd64.pyd` (256KB)
- `ctptd.cp312-win_amd64.pyd` (1.2MB)  
- `ttsmd.cp312-win_amd64.pyd` (255KB)
- `ttstd.cp312-win_amd64.pyd` (1.1MB)

**✅ 建立的统一构建架构:**

- 根目录主`meson.build`统一管理项目配置
- 子模块`meson.build`专注于模块特定配置
- 统一的`build.py`脚本简化构建流程
- 跨平台支持（Windows/Linux/Mac）

## 构建流程验证

```bash
# 简单的一键构建命令
python build.py
```

所有4个扩展模块已成功编译并复制到目标位置：

- `src/ctp/api/ctpmd.cp312-win_amd64.pyd`
- `src/ctp/api/ctptd.cp312-win_amd64.pyd`
- `src/tts/api/ttsmd.cp312-win_amd64.pyd`
- `src/tts/api/ttstd.cp312-win_amd64.pyd`

## 技术细节

**修复的配置文件:**

- ✅ `meson.build` (根目录主构建脚本)
- ✅ `src/ctp/meson.build` (CTP模块配置)
- ✅ `src/tts/meson.build` (TTS模块配置)  
- ✅ `build.py` (统一构建脚本)
- ✅ `src/tts/gateway/build.py` (路径错误修复)

**编译环境:**

- Windows 10 + MSVC 2022
- Python 3.12虚拟环境
- Meson 1.8.1 + Ninja构建系统
- Pybind11用于Python-C++绑定

统一构建系统现已完全就绪，可以支持Homalos量化交易系统的持续开发和部署！

## ✅ 构建过程检查结果

**meson compile -C build** 命令运行完全成功！

### 🔍 构建过程分析

1. **✅ MSVC编译器环境**: 自动激活成功
2. **✅ Ninja构建系统**: 正常运行
3. **✅ 构建状态**: `ninja: no work to do` (所有目标已是最新)

### 📦 生成的扩展模块 (在build目录)

**CTP模块:**

- `ctpmd.cp312-win_amd64.pyd` (256KB)
- `ctptd.cp312-win_amd64.pyd` (1.2MB)

**TTS模块:**

- `ttsmd.cp312-win_amd64.pyd` (255KB)
- `ttstd.cp312-win_amd64.pyd` (1.1MB)

### 最终部署状态

所有扩展模块已成功部署到目标位置：

- `src/ctp/api/` - CTP模块扩展
- `src/tts/api/` - TTS模块扩展

### 构建系统状态总结

| 组件      | 状态   | 说明                    |
| --------- | ------ | ----------------------- |
| Meson设置 | ✅ 成功 | 根目录和子模块配置正确  |
| 编译环境  | ✅ 正常 | MSVC + Ninja构建链      |
| 扩展模块  | ✅ 完整 | 4个.pyd文件全部生成     |
| 部署状态  | ✅ 就绪 | 文件已复制到目标位置    |
| 增量构建  | ✅ 支持 | ninja检测到无需重复编译 |

**结论**: Homalos量化交易系统的统一构建系统已完全就绪，支持增量编译和一键构建！
