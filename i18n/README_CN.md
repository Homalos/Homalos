<div align="center">
  <a href="https://homalos.github.io" target="blank"><img alt="Homalos Logo" src="../assets/logo.svg"/></a>
</div>
<p>&nbsp;</p>

<p align="center">
  <font size="5px">✨ 基于Python的期货量化交易系统 ✨</font>
</p>

<p align="center">
  <a href="https://img.shields.io/github/license/Homalos/Homalos"><img alt="GitHub License" title="GitHub License"
src="https://img.shields.io/github/license/Homalos/Homalos"/></a>
  <a href="https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2FHomalos%2FHomalos%2Frefs%2Fheads%2Fmain%2Fpyproject.toml"><img alt="Python Version from PEP 621 TOML" title="Python Version from PEP 621 TOML"
src="https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2FHomalos%2FHomalos%2Frefs%2Fheads%2Fmain%2Fpyproject.toml"/></a>
  <a href="https://deepwiki.com/Homalos/Homalos"><img src="https://deepwiki.com/badge.svg" alt="Ask DeepWiki"></a>
  <a href="https://qun.qq.com/universal-share/share?ac=1&authKey=dzGDk%2F%2Bpy%2FwpVyR%2BTrt9%2B5cxLZrEHL793cZlFWvOXuV5I8szMnOU4Wf3ylap7Ph0&busi_data=eyJncm91cENvZGUiOiI0NDYwNDI3NzciLCJ0b2tlbiI6IlFrM0ZhZmRLd0xIaFdsZE9FWjlPcHFwSWxBRFFLY2xZbFhaTUh4K2RldisvcXlBckZ4NVIrQzVTdDNKUFpCNi8iLCJ1aW4iOiI4MjEzMDAwNzkifQ%3D%3D&data=O1Bf7_yhnvrrLsJxc3g5-p-ga6TWx6EExnG0S1kDNJTyK4sV_Nd9m4p-bkG4rhj_5TdtS5lMjVZRBv4amHyvEA&svctype=4&tempid=h5_group_info"><img alt="Group#1" title="Group#1"
src="https://img.shields.io/badge/Group%231-Join-blue"/></a>
</p>

<p align="center">
  简体中文 |
  <a href="../README.md">English</a>
</p>

## 概述

此项目是 Homalos 的新进展分支项目，Homalos 是一个基于 Python 的事件驱动型期货交易平台，旨在实现单机部署，并最大限度地减少外部依赖。

- **当前状态**: 开发中

## 功能特性

- ✅ 事件驱动架构
- ✅ CTP（上海期货交易所）集成
- ✅ 实时行情数据处理
- ✅ K线数据生成（1m、3m、5m、15m、30m、60m）
- ✅ **Web管理界面**（FastAPI + Vue 3）
  - 用户认证（JWT）
  - 系统监控仪表盘
  - 策略详情管理
  - 任务调度器
  - 通知中心
  - 数据中心Web控制
  - 实时数据可视化

### ✨ 最新更新 (v0.0.1.20251010)

- 🎨 **策略管理增强**：抽屉式详情面板，展示持仓信息、风险控制参数和操作日志
- 📊 **仪表盘扩展**：账户总览、今日表现、持仓分布、关键指标展示
- ⏰ **任务调度器**：管理定时任务（每日/单次/分钟/周/月）
- 🎮 **控制台面板**：控制交易系统和数据中心，实时状态监控
- 🔔 **通知中心**：统一消息管理，未读消息提醒
- 🏗️ **前端优化**：模块化代码结构，Home.vue从3060行优化至1663行
- 🚀 **数据中心API**：完整的进程管理（启动/停止/重启）、监控和审计日志
- 🐛 **Bug修复**：中文日志编码、异步操作、多个UI改进

## Web界面

Homalos 现已包含基于 FastAPI 和 Vue 3 构建的现代化 Web 管理界面。

### 快速开始

1. **初始化管理员账户**
   ```bash
   init_admin.bat
   ```
   默认凭据：`admin` / `admin123`

2. **启动所有服务**
   ```bash
   start_all.bat
   ```
   这将启动后端（端口 8000）和前端（端口 5173）

3. **访问 Web 界面**
   - 前端：http://localhost:5173
   - API 文档：http://localhost:8000/docs

### 技术栈

**后端：**
- FastAPI
- SQLAlchemy 2.0 + SQLite
- JWT 认证
- Argon2 密码哈希

**前端：**
- Vue 3 + Vite
- Element Plus UI
- Vue Router 4
- Pinia 状态管理
- Axios

### 文档

详细文档请参见 [Web系统使用指南](../docs/Web系统使用指南.md)。

## 安装

```bash
# 克隆仓库
git clone https://github.com/Homalos/Homalos.git
cd Homalos

# 安装 Python 依赖
.venv\Scripts\activate
uv pip install -r requirements.txt

# 安装前端依赖
cd web-ui
npm install
cd ..
```

## 许可证

MIT License
