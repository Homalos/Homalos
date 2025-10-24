<div align="center">
  <a href="https://homalos.github.io" target="blank"><img alt="Homalos Logo" src="assets/logo.svg"/></a>
</div>
<p>&nbsp;</p>

<p align="center">
  <font size="5px">✨ Python-based Futures Quantitative Trading System ✨</font>
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
  English |
  <a href="i18n/README_CN.md">简体中文</a>
</p>

## Overview

This project is a new development fork of Homalos, a Python-based event-driven futures trading platform designed to be deployed on a single machine with minimal external dependencies.

- **Current Status**: Under development

## Features

- ✅ Event-driven architecture
- ✅ CTP-API (Comprehensive trading platform API) integration
- ✅ Real-time market data processing
- ✅ K-line data generation (1m, 3m, 5m, 15m, 30m, 60m)
- ✅ **Web Management Interface** (FastAPI + Vue 3)
  - User authentication (JWT)
  - System monitoring dashboard
  - Strategy management with detailed panel
  - Task scheduler
  - Notification center
  - Data center control via Web API
  - Real-time data visualization

### ✨ Recent Updates (v0.0.6.20251024)

- 🚀 **Critical Performance & Stability Fixes**:
  - Fixed FastAPI blocking issue caused by synchronous locks in `subscription_manager`
  - Fixed ZeroMQ message corruption due to multi-threading race conditions
  - Implemented non-blocking lock (trylock) for HTTP request handlers
  - Added thread-safe ZeroMQ send operations with dedicated lock
  - System now handles high-frequency market data without blocking
- 🏗️ **Architecture Improvements**:
  - ZeroMQ PUB-SUB pattern for strategy IPC (replacing `multiprocessing.Pipe`)
  - Thread-safe message broadcasting with atomic send operations
  - Improved strategy isolation with robust error handling
  - Enhanced EventBus performance under concurrent workload
- ✅ **Verified Stability**:
  - Web frontend: No timeout errors, all HTTP requests < 100ms
  - Strategy callbacks: Successfully receiving tick/bar data via ZeroMQ
  - Message format: 100% correct (2-part messages, no corruption)
  - System performance: CPU < 5%, minimal overhead

### Previous Updates (v0.0.5.20251022)

- 🏗️ **Core Architecture Optimization**:
  - Event.py refactoring: Converted 10 module-level functions to `Event` class methods
  - Improved API: `Event.tick()` vs `create_tick_event()`
  - Python 3.10+ union type syntax (`|` instead of `Optional`)
  - Better encapsulation and reduced namespace pollution
- ⏱️ **Built-in Timer Mechanism**:
  - EventBus now has built-in timer for second-level periodic tasks
  - Configurable interval (default 1 second)
  - Automatic TIMER event publishing to general queue
  - Thread-safe start/stop mechanism
  - Use case: Periodic account/position queries
- 🐛 **Bug Fixes**:
  - Fixed TraderGateway timer event handler signature mismatch
  - Added account query logging for better observability
  - Enhanced monitoring and debugging capabilities
- 📝 **Developer Experience**:
  - Out-of-the-box timer functionality
  - Clear logging for all query operations
  - Flexible configuration options

## Web Interface

Homalos now includes a modern web management interface built with FastAPI and Vue 3.

### Quick Start

1. **Initialize Admin Account**
   ```bash
   init_admin.bat
   ```
   Default credentials: `admin` / `admin123`

2. **Start All Services**
   ```bash
   start_all_web.bat
   ```
   This will start both backend (port 8000) and frontend (port 5173)

3. **Access Web Interface**
   - Frontend: http://localhost:5173
   - API Docs: http://localhost:8000/docs

### Tech Stack

**Backend:**
- FastAPI
- SQLAlchemy 2.0 + SQLite
- JWT Authentication
- Argon2 Password Hashing

**Frontend:**
- Vue 3 + Vite
- Element Plus UI
- Vue Router 4
- Pinia State Management
- Axios

### Documentation

See [Web System Guide](docs/Web系统使用指南.md) for detailed documentation.

## Installation

```bash
# Clone repository
git clone https://github.com/Homalos/Homalos.git
cd Homalos

# Install Python dependencies
.venv\Scripts\activate
uv pip install -r requirements.txt

# Install frontend dependencies
cd web-ui
npm install
cd ..
```

## License

MIT License