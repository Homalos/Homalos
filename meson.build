project(
  'homalos',
  'cpp',
  version: '6.7.7.1',
  license: 'MIT',
  meson_version: '>=1.7.0',
  default_options: [
    'buildtype=release',
    'cpp_std=c++17',
    'warning_level=2',
  ],
)

# 导入Python模块
py = import('python').find_installation(pure: false)
py_dep = py.dependency()

# 获取pybind11路径
python_cmd = host_machine.system() == 'windows' ? 'python' : 'python3'
pybind11_include_dir = run_command(python_cmd, '-c', 'import pybind11; print(pybind11.get_include())', check: true).stdout().strip()
message('使用pybind11路径: ' + pybind11_include_dir)

# 创建pybind11依赖对象
pybind11_dep = declare_dependency(
  compile_args: ['-I' + pybind11_include_dir]
)

# 获取编译器信息
cpp = meson.get_compiler('cpp')

# 输出构建目标系统信息
message('构建目标系统: ' + host_machine.system())

# 设置平台特定的编译参数
# 注意：Windows下Python扩展通常使用/MD运行时库
# /MT在子模块中的extra_cpp_args中设置

# 包含子模块
subdir('src/ctp')
subdir('src/tts')
