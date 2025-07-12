import subprocess
import sys
import shutil
import os
import sysconfig

# 执行 meson setup build
ret = subprocess.call(['meson', 'setup', 'build'])
if ret != 0:
    print('meson setup build 失败，自动退出。')
    sys.exit(ret)

# 执行 meson compile -C build
ret = subprocess.call(['meson', 'compile', '-C', 'build'])
if ret != 0:
    print('meson compile 失败。')
    sys.exit(ret)

# Dynamically determine .pyd filenames
# The following lines replace the original hardcoded pyd_files list
ext_suffix = sysconfig.get_config_vars().get('EXT_SUFFIX')
# Example ext_suffix: '.cp312-win_amd64.pyd' on Windows with Python 3.12
pyd_files = [f'ctpmd{ext_suffix}', f'ctptd{ext_suffix}']

# 复制生成的pyd文件到目标目录
build_dir = 'build'
target_dir = os.path.join('src', 'ctp', 'api')

for pyd in pyd_files:
    src_path = os.path.join(build_dir, pyd)
    dst_path = os.path.join(target_dir, pyd)
    try:
        shutil.copy2(src_path, dst_path)
        print(f'已复制 {src_path} 到 {dst_path}')
    except Exception as e:
        print(f'复制 {src_path} 失败: {e}')

# 自动生成存根文件，使用包名并设置PYTHONPATH
stub_modules = ['src.ctp.api.ctpmd', 'src.ctp.api.ctptd']
env = os.environ.copy()
env['PYTHONPATH'] = os.path.abspath('src') + os.pathsep + env.get('PYTHONPATH', '')

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

print('构建流程已全部完成。') 