#!/usr/bin/env python3
"""
Homalos统一构建脚本
用于构建ctp和tts两个C++扩展模块
"""
import os
import shutil
import subprocess
import sys
import sysconfig


def setup_build() -> None:
    """设置构建环境"""
    print("正在设置构建环境...")
    ret = subprocess.call(['meson', 'setup', 'build'])
    if ret != 0:
        print('meson setup build 失败，自动退出。')
        sys.exit(ret)
    print("构建环境设置完成。")

def compile_modules() -> None:
    """编译所有模块"""
    print("正在编译所有模块...")
    ret = subprocess.call(['meson', 'compile', '-C', 'build'])
    if ret != 0:
        print('meson compile 失败。')
        sys.exit(ret)
    print("所有模块编译完成。")

def copy_module_files(module_name: str, module_names: list[str]) -> None:
    """复制指定模块的编译产物到目标目录"""
    ext_suffix = sysconfig.get_config_vars().get('EXT_SUFFIX')
    pyd_files = [f'{mod_name}{ext_suffix}' for mod_name in module_names]
    
    build_dir = os.path.join('build', 'src', module_name)
    target_dir = os.path.join('src', module_name, 'api')

    
    print(f"正在复制{module_name}模块文件...")
    for pyd in pyd_files:
        src_path = os.path.join(build_dir, pyd)
        dst_path = os.path.join(target_dir, pyd)
        try:
            shutil.copy2(src_path, dst_path)
            print(f'已复制 {src_path} 到 {dst_path}')
        except FileNotFoundError as e:
            print(f'文件不存在: {src_path}: {e}')
        except PermissionError as e:
            print(f'权限不足: {e}')
        except OSError as e:
            print(f'复制 {src_path} 失败: {e}')

def generate_stub_files(module_name: str, module_names: list[str]) -> None:
    """为指定模块生成存根文件"""
    print(f"正在为{module_name}模块生成存根文件...")
    
    # 设置PYTHONPATH环境变量
    env = os.environ.copy()
    env['PYTHONPATH'] = os.path.abspath('src') + os.pathsep + env.get('PYTHONPATH', '')
    
    stub_modules = [f'src.{module_name}.api.{mod_name}' for mod_name in module_names]
    
    for mod_base in stub_modules:
        print(f'正在为 {mod_base} 生成存根文件...')
        ret = subprocess.call([
            sys.executable, '-m', 'pybind11_stubgen',
            f'--output-dir=.',
            mod_base
        ], env=env)
        if ret != 0:
            print(f'为 {mod_base} 生成存根文件失败。')
        else:
            print(f'为 {mod_base} 生成存根文件成功。')

def build_ctp() -> None:
    """构建CTP模块"""
    print("=" * 50)
    print("构建CTP模块")
    print("=" * 50)
    copy_module_files('ctp', ['ctpmd', 'ctptd'])
    generate_stub_files('ctp', ['ctpmd', 'ctptd'])

def build_tts() -> None:
    """构建TTS模块"""
    print("=" * 50)
    print("构建TTS模块")
    print("=" * 50)
    copy_module_files('tts', ['ttsmd', 'ttstd'])
    generate_stub_files('tts', ['ttsmd', 'ttstd'])

def main() -> None:
    """主构建流程"""
    print("Homalos量化交易系统 - 统一构建脚本")
    print("=" * 60)
    
    try:
        # 设置构建环境
        setup_build()
        
        # 编译所有模块
        compile_modules()
        
        # 处理各模块的构建产物
        build_ctp()
        build_tts()
        
        print("=" * 60)
        print("所有模块构建流程已全部完成！")
        
    except KeyboardInterrupt:
        print("\n构建过程被用户中断。")
        sys.exit(1)
    except Exception as e:
        print(f"构建过程中发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
