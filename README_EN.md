# Homalos——Futures quantitative trading system based on Python

ENGLISH | [中文](README.md)

## Overall architecture of the project

```reStructuredText
Homalos_v2/
├── 📁 src/ # Core source code directory
│ ├── 📁 config/ # Configuration management
│ ├── 📁 core/ # System core module
│ ├── 📁 ctp/ # CTP interface module
│ ├── 📁 services/ # Service module
│ ├── 📁 strategies/ # Strategy instance module
│ ├── 📁 tts/ # TTS interface module
│ ├── 📁 util/ # TTS interface module
│ └── 📁 web/ # Web interface
├── 📁 config/ # Configuration file
├── 📁 data/ # Data storage
├── 📁 log/ # Log storage
└── 📁 test/ # Test script directory
```
## Core technology stack

**Build system:**

- **Meson + Ninja**: Modern C++ extension build system
- **Pybind11**: Python-C++ binding
- **Hatch**: Python project management and packaging
- uv: We choose to use the modern `uv` as the Python package manager, which provides faster installation speed and smarter dependency resolution capabilities.

**Main dependencies:**

- **Data processing**: NumPy, Pandas, Polars

- **Technical analysis**: TA-Lib

- **Log system**: Loguru

### Detailed explanation of core modules

#### 1. **Core core module** (`src/core/`)

- **event.py**: event object
- **event_bus.py**: high-performance event bus
- **gateway.py**: abstract gateway class
- **object.py**: basic data structure
- **logger.py**: log module

#### 2. **Strategy module** (`src/strategies/`)

- **base_strategy.py**: strategy base class
- **moving_average_strategy.py**: moving average strategy

#### 3. **Trading interface module**

- **CTP module** (`src/ctp/`): previous technical CTP interface
- **TTS module** (`src/tts/`): TTS trading interface

Both modules contain:

- `api/`: C++ extension module (.pyd file)

- `gateway/`: Python gateway implementation

- `meson.build`: build configuration

#### 4. **Configure system** (`config_files/`)

- **system.yaml**: global system configuration
- **global_config.yaml**: global system configuration
- **broker_config.json**: broker configuration
- **2024/2025_holidays.json**: trading calendar
- **instrument_exchange_id.json**: contract exchange mapping

### 🚀 Build system features

1. **Unified build**: Use Meson build system to manage C++ extensions

2. **Cross-platform support**: Windows/Linux/Mac

3. **Incremental compilation**: Support fast rebuild
4. **One-click build**: `python build.py`

### System Features

1. **Event-driven architecture**: Asynchronous event processing based on EventEngine

2. **Multiple interface support**: Supports both CTP and TTS trading interfaces

3. **Strategy framework**: Complete strategy lifecycle management

4. **Configuration-based design**: Flexible configuration file system

5. **Modern tool chain**: Use the latest Python build and development tools

## Build process

Delete old builds:

```bash
rmdir /s /q build
```

Third-party extension builds:

```bash
meson compile -C build
```

This project uses `meson-python` as the build backend, and I need to make sure the build system is configured correctly:

## Summary

Use the `hatch build` command to build your project. Recommended for future builds:

- `hatch build` - normal build
- `hatch build --clean` - clean and rebuild
- `hatch build -t wheel` - build only wheel packages
- `hatch build -t sdist` - build only source packages

## Main achievements

**✅ Key issues solved:**

1. **Compiler parameter conflict**: Removed the `/MT` parameter to avoid conflict with Python's default `/MD`

2. **Header file path error**: Adjust the include path from `api/include/ctp` and `api/include/tts` to `api/include`
3. **C++17 deprecation warning**: Added the `-D_SILENCE_CXX17_CODECVT_HEADER_DEPRECATION_WARNING` parameter

**✅ Successfully generated extension modules:**

- `ctpmd.cp312-win_amd64.pyd` (256KB)
- `ctptd.cp312-win_amd64.pyd` (1.2MB)
- `ttsmd.cp312-win_amd64.pyd` (255KB)
- `ttstd.cp312-win_amd64.pyd` (1.1MB)

**✅ Unified build architecture established:**

- Root directory main `meson.build` unified management of project configuration
- Submodule `meson.build` focuses on module-specific configuration
- Unified `build.py` script simplifies the build process
- Cross-platform support (Windows/Linux/Mac)

## Build process verification

```bash
# Simple one-click build command
python build.py
```

All 4 extension modules have been successfully compiled and copied to the target location:

- `src/ctp/api/ctpmd.cp312-win_amd64.pyd`
- `src/ctp/api/ctptd.cp312-win_amd64.pyd`
- `src/tts/api/ttsmd.cp312-win_amd64.pyd`
- `src/tts/api/ttstd.cp312-win_amd64.pyd`

## Technical details

**Fixed configuration files:**

- ✅ `meson.build` (root directory main build script)
- ✅ `src/ctp/meson.build` (CTP module configuration)
- ✅ `src/tts/meson.build` (TTS module configuration)
- ✅ `build.py` (unified build script)
- ✅ `src/tts/gateway/build.py` (path error fix)

**Compilation environment:**

- Windows 10 + MSVC 2022
- Python 3.12 virtual environment
- Meson 1.8.1 + Ninja build system
- Pybind11 for Python-C++ bindings

The unified build system is now fully ready to support the continued development and deployment of the Homalos quantitative trading system!

## ✅ Check the results of the build process

**meson compile -C build** The command ran completely successfully!

### 🔍 Build process analysis

1. **✅ MSVC compiler environment**: Automatic activation successful

2. **✅ Ninja build system**: Normal operation

3. **✅ Build status**: `ninja: no work to do` (all targets are up to date)

### 📦 Generated extension modules (in the build directory)

**CTP module:**

- `ctpmd.cp312-win_amd64.pyd` (256KB)

- `ctptd.cp312-win_amd64.pyd` (1.2MB)

**TTS module:**

- `ttsmd.cp312-win_amd64.pyd` (255KB)

- `ttstd.cp312-win_amd64.pyd` (1.1MB)

### Final deployment status

All extension modules have been successfully deployed to the target location:

- `src/ctp/api/` - CTP module extension
- `src/tts/api/` - TTS module extension

### Build system status summary

| Component               | Status     | Description                                            |
| ----------------------- | ---------- | ------------------------------------------------------ |
| Meson settings          | ✅ Success  | Root directory and submodules are configured correctly |
| Compilation environment | ✅ Normal   | MSVC + Ninja build chain                               |
| Extension module        | ✅ Complete | All 4 .pyd files are generated                         |
| Deployment status       | ✅ Ready    | Files have been copied to the target location          |
| Incremental build       | ✅ Support  | ninja detects that no repeated compilation is required |

**Conclusion**: The unified build system of the Homalos quantitative trading system is fully ready, supporting incremental compilation and one-click build!