project(
  'ctp',
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

# 导入文件系统和Python模块
py = import('python').find_installation(pure: false)
py_dep = py.dependency()

# 获取pybind11路径
python_cmd = host_machine.system() == 'windows' ? 'python' : 'python3'
pybind11_include_dir = run_command(python_cmd, '-c', 'import pybind11; print(pybind11.get_include())', check: true).stdout().strip()
message('使用pybind11路径: ' + pybind11_include_dir)

# 创建pybind11依赖对象，使用compile_args避免绝对路径报错
pybind11_dep = declare_dependency(
  compile_args: ['-I' + pybind11_include_dir]
)

# 获取编译器信息
cpp = meson.get_compiler('cpp')
compiler_id = cpp.get_id()

# 输出构建目标系统信息
message('构建目标系统: ' + host_machine.system())

# 初始化变量
thostmduserapi_lib = []
thosttraderapi_lib = []
extra_cpp_args = []
extra_link_args = []

# 初始化库变量
thostmduserapi_lib = []
thosttraderapi_lib = []

# 初始化其他编译选项
extra_link_args = []
install_rpath_value = ''
api_abs_dir = 'src/ctp/api'

# 设置Windows特定编译选项
if host_machine.system() == 'windows'
  # Windows编译器设置
  add_project_arguments('/MT', language : 'cpp')
  
  # 添加编码和安全警告屏蔽参数
  extra_cpp_args += ['/source-charset:GB2312', '-D_CRT_SECURE_NO_WARNINGS']
  
  # 设置库目录
  lib_dir = meson.current_source_dir() / api_abs_dir + '/libs'
  api_dir = meson.current_source_dir() / api_abs_dir
  
  # 设置include目录
  include_dirs = include_directories(
    api_abs_dir + '/include',
    api_abs_dir + '/src_ctp',
  )
  
  # 定义CTP库
  thostmduserapi_lib = cpp.find_library('thostmduserapi_se', 
                                       dirs: [lib_dir, api_dir],
                                       required: true)
  thosttraderapi_lib = cpp.find_library('thosttraderapi_se', 
                                       dirs: [lib_dir, api_dir],
                                       required: true)
                                       
# 设置Mac特定编译选项
elif host_machine.system() == 'darwin'
  # Mac编译器设置
  extra_cpp_args = [
    '-std=c++11',
    '-mmacosx-version-min=10.12',
  ]
  
  # 设置链接参数，包括@rpath到@loader_path的修改
  extra_link_args = [
    '-mmacosx-version-min=10.12',
    '-Wl,-rpath,@loader_path',
  ]
  
  # 设置库目录
  lib_dir = meson.current_source_dir() / api_abs_dir + '/libs'
  api_dir = meson.current_source_dir() / api_abs_dir

  # 设置include目录
  include_dirs = include_directories(
    api_abs_dir + '/include/mac',
    api_abs_dir + '/src_ctp',
  )
  
  # 定义Mac Framework依赖
  thostmduserapi_lib = declare_dependency(
    dependencies: [py_dep],
    link_args: [
      '-F', meson.current_source_dir() / api_abs_dir,
      '-framework', 'thostmduserapi_se'
    ]
  )
  
  thosttraderapi_lib = declare_dependency(
    dependencies: [py_dep],
    link_args: [
      '-F', meson.current_source_dir() / api_abs_dir,
      '-framework', 'thosttraderapi_se'
    ]
  )

# 设置Linux特定编译选项
else  # Linux
  # Linux编译器设置
  extra_cpp_args = [
    '-std=c++17',
    '-O3',
    '-Wno-delete-incomplete',
    '-Wno-sign-compare',
  ]
  
  extra_link_args = [
    '-lstdc++',
    '-Wl,-rpath,$ORIGIN',  # 添加rpath设置，使库能在运行时找到同目录下的动态库
  ]
  
  # 设置库目录
  lib_dir = meson.current_source_dir() / api_abs_dir
  
  # 设置include目录
  include_dirs = include_directories(
    api_abs_dir + '/include',
    api_abs_dir + '/src_ctp',
  )
  
  # 定义CTP库
  thostmduserapi_lib = cpp.find_library('thostmduserapi_se', 
                                       dirs: [lib_dir],
                                       required: true)
  thosttraderapi_lib = cpp.find_library('thosttraderapi_se', 
                                       dirs: [lib_dir],
                                       required: true)
endif

# 创建MD模块扩展
md_module = py.extension_module(
  'ctpmd',
  sources: [api_abs_dir + '/src_ctp/ctpmd/ctpmd.cpp'],
  include_directories: include_dirs,
  dependencies: [py_dep, pybind11_dep, thostmduserapi_lib],
  cpp_args: extra_cpp_args,
  link_args: extra_link_args,
  install: true,
  subdir: api_abs_dir
)

# 创建TD模块扩展
td_module = py.extension_module(
  'ctptd',
  sources: [api_abs_dir + '/src_ctp/ctptd/ctptd.cpp'],
  include_directories: include_dirs,
  dependencies: [py_dep, pybind11_dep, thosttraderapi_lib],
  cpp_args: extra_cpp_args,
  link_args: extra_link_args,
  install: true,
  subdir: api_abs_dir
)

# 安装Python源代码
python_files = [
  ['src/ctp/__init__.py', 'ctp'],
  ['src/ctp/api/__init__.py', 'ctp/api'],
  ['src/ctp/api/ctp_constant.py', 'ctp/api'],
  ['src/ctp/gateway/__init__.py', 'ctp/gateway'],
  ['src/ctp/gateway/ctp_gateway.py', 'ctp/gateway'],
]

foreach file : python_files
  py.install_sources(
    [file[0]],
    pure: false,
    subdir: file[1]
  )
endforeach

# 安装API动态库文件
if host_machine.system() == 'windows'
  api_libs = [
    api_abs_dir + '/thostmduserapi_se.dll',
    api_abs_dir + '/thosttraderapi_se.dll',
  ]
  
  install_data(
    api_libs,
    install_dir: py.get_install_dir() / 'ctp/api'
  )
elif host_machine.system() == 'darwin'
  # 安装Mac Framework文件夹
  install_subdir(
    api_abs_dir + '/thostmduserapi_se.framework',
    install_dir: py.get_install_dir() / 'ctp/api'
  )
  
  install_subdir(
    api_abs_dir + '/thosttraderapi_se.framework',
    install_dir: py.get_install_dir() / 'ctp/api'
  )
else  # Linux
  api_libs = [
    api_abs_dir + '/libthostmduserapi_se.so',
    api_abs_dir + '/libthosttraderapi_se.so',
  ]
  
  install_data(
    api_libs,
    install_dir: py.get_install_dir() / 'ctp/api'
  )
endif