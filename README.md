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

### ✨ Recent Updates (v0.0.3.20251012)

- 🎨 **Component Refactoring**: Split `Home.vue` (945 lines) into 7 independent components
  - Dashboard, Console, Strategy Management, Task Scheduler, Notifications, Settings, About
  - Reduced Home.vue by 92% (945 → 280 lines)
  - Improved maintainability with single responsibility principle
- 🔧 **System Configuration**:
  - Dev mode & trading hours check settings
  - Two-way sync with `config/system.yaml`
  - Automatic backup on every change
  - Audit logging for all modifications
- 📄 **Dynamic About Page**: Load system info from config file
  - No hardcoded values, easy to update
  - Public API access (no authentication required)
- 🐛 **Bug Fixes**: Fixed config save issues, validation logic improvements
- 📚 **Documentation**: 5 new guides and automated API tests

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
   start_all.bat
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