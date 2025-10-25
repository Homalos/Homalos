@echo off
setlocal enabledelayedexpansion
title 压缩备份当前目录指定文件夹和文件

echo 文件列表处理...
echo.

:: 设置固定文件列表名和带日期时间的ZIP文件名
set "filelist=files.txt"
set "timestamp=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "timestamp=%timestamp: =0%"
set "zipname=backup_Homalos_%timestamp%.zip"

:: 检查 WinRAR 是否可用
set "rar_cmd="
where WinRAR >nul 2>&1
if not errorlevel 1 (
    set "rar_cmd=WinRAR"
) else if exist "%ProgramFiles%\WinRAR\WinRAR.exe" (
    set "rar_cmd=%ProgramFiles%\WinRAR\WinRAR.exe"
) else if exist "%ProgramW6432%\WinRAR\WinRAR.exe" (
    set "rar_cmd=%ProgramW6432%\WinRAR\WinRAR.exe"
) else (
    echo 错误: 未找到 WinRAR，请确保已安装 WinRAR
    pause
    exit /b 1
)

echo 使用 WinRAR 进行压缩: !rar_cmd!
echo.

:: 如果文件列表不存在，则生成
if not exist "%filelist%" (
    echo 正在生成文件列表...
    
    :: 生成统一的文件列表
    echo 当前目录下的所有文件夹和文件： > "%filelist%"
    echo ======================================== >> "%filelist%"
    echo. >> "%filelist%"
    
    :: 列出所有文件夹
    for /d %%i in (*) do (
        set "item=%%i"
        call :trim_spaces item
        echo !item! >> "%filelist%"
    )
    
    echo. >> "%filelist%"
    
    :: 列出所有文件
    for %%i in (*) do (
        if not "%%i"=="%~nx0" if not "%%i"=="%filelist%" (
            set "skip=no"
            for %%z in ("!zipname!") do if "%%i"=="%%~nz%%~xz" set "skip=yes"
            if "!skip!"=="no" (
                set "item=%%i"
                call :trim_spaces item
                echo !item! >> "%filelist%"
            )
        )
    )
    
    echo 文件列表已生成: %filelist%
) else (
    echo 使用现有文件列表: %filelist%
)
echo.

:: 询问用户选择压缩方式
echo 请选择压缩方式：
echo 1. 压缩所有文件夹和文件
echo 2. 选择特定文件夹和文件进行压缩
echo 3. 仅压缩文件夹
echo 4. 仅压缩文件
echo 5. 手动编辑文件列表后压缩
echo.
set /p choice="请选择 (1-5): "

:: 根据选择执行不同的压缩操作
if "!choice!"=="1" (
    echo 正在压缩所有文件夹和文件...
    "!rar_cmd!" a -afzip -ep1 -r -y "%zipname%" "*.*"
    goto :success
)

if "!choice!"=="2" (
    call :select_files
    goto :compress_selected
)

if "!choice!"=="3" (
    echo 正在压缩所有文件夹...
    set "folders="
    for /d %%i in (*) do (
        set "folders=!folders! "%%i""
    )
    if defined folders (
        "!rar_cmd!" a -afzip -ep1 -r -y "%zipname%" !folders!
    ) else (
        echo 未找到任何文件夹！
    )
    goto :success
)

if "!choice!"=="4" (
    echo 正在压缩所有文件...
    set "files="
    for %%i in (*) do (
        if not "%%i"=="%~nx0" if not "%%i"=="%filelist%" (
            set "skip=no"
            for %%z in ("!zipname!") do if "%%i"=="%%~nz%%~xz" set "skip=yes"
            if "!skip!"=="no" (
                set "files=!files! "%%i""
            )
        )
    )
    if defined files (
        "!rar_cmd!" a -afzip -ep1 -y "%zipname%" !files!
    ) else (
        echo 未找到任何文件！
    )
    goto :success
)

if "!choice!"=="5" (
    echo 请编辑文件 %filelist%，删除不需要压缩的项目，然后按任意键继续...
    echo 注意：请确保只保留要压缩的文件夹和文件名，每行一个
    pause >nul
    call :compress_from_list
    goto :success
)

echo 无效选择！
goto :end

:select_files
echo.
echo 当前可用的文件夹：
for /d %%i in (*) do echo   %%i
echo.
echo 当前可用的文件：
for %%i in (*) do (
    if not "%%i"=="%~nx0" if not "%%i"=="%filelist%" (
        set "skip=no"
        for %%z in ("!zipname!") do if "%%i"=="%%~nz%%~xz" set "skip=yes"
        if "!skip!"=="no" echo   %%i
    )
)
echo.
set /p selected="请输入要压缩的文件夹或文件名（多个用空格分隔）: "
goto :eof

:compress_selected
echo 正在压缩选定的项目...
set "items="
for %%i in (%selected%) do (
    if exist "%%i" (
        set "items=!items! "%%i""
    ) else (
        echo 警告: "%%i" 不存在，已跳过
    )
)
if defined items (
    "!rar_cmd!" a -afzip -ep1 -r -y "%zipname%" !items!
) else (
    echo 未选择任何有效项目！
)
goto :success

:compress_from_list
echo 正在根据文件列表进行压缩...

:: 创建临时列表文件
set "tempfile=%temp%\rar_list_%random%.txt"
type nul > "%tempfile%"

set "count=0"

:: 处理统一文件列表
if exist "%filelist%" (
    for /f "usebackq delims=" %%i in ("%filelist%") do (
        set "line=%%i"
        call :trim_spaces line
        
        if not "!line!"=="" (
            :: 跳过标题行和分隔行
            echo !line! | findstr /r /c:"^当前目录" >nul
            if errorlevel 1 (
                echo !line! | findstr /r /c:"^====" >nul
                if errorlevel 1 (
                    echo !line! | findstr /r /c:"^\\[文件夹\\]" >nul
                    if errorlevel 1 (
                        echo !line! | findstr /r /c:"^\\[文件\\]" >nul
                        if errorlevel 1 (
                            :: 检查项目是否存在
                            if exist "!line!\" (
                                echo 添加文件夹: !line!
                                echo "!line!" >> "%tempfile%"
                                set /a count+=1
                            ) else if exist "!line!" (
                                echo 添加文件: !line!
                                echo "!line!" >> "%tempfile%"
                                set /a count+=1
                            ) else (
                                echo 警告: "!line!" 不存在，已跳过
                            )
                        )
                    )
                )
            )
        )
    )
)

:: 使用列表文件进行压缩
if !count! gtr 0 (
    echo 正在压缩 !count! 个项目...
    "!rar_cmd!" a -afzip -ep1 -r -y "%zipname%" @"%tempfile%"
) else (
    echo 在文件列表中未找到有效项目！
    echo 请确保文件列表中只包含要压缩的文件夹和文件名
)

:: 删除临时文件
del "%tempfile%" >nul 2>&1
goto :eof

:trim_spaces
:: 去除变量值的前后空格
set "tmp=!%1!"
:trim_loop
if not "!tmp!"=="" (
    if "!tmp:~0,1!"==" " (
        set "tmp=!tmp:~1!"
        goto trim_loop
    )
)
:trim_loop_end
if not "!tmp!"=="" (
    if "!tmp:~-1!"==" " (
        set "tmp=!tmp:~0,-1!"
        goto trim_loop_end
    )
)
set "%1=!tmp!"
goto :eof

:success
if exist "%zipname%" (
    echo.
    echo 压缩成功完成！
    echo 生成的ZIP文件: %zipname%
    echo 文件列表: %filelist%
    echo.
    echo 压缩包大小: 
    for %%I in ("%zipname%") do echo   %%~zI 字节
) else (
    echo 压缩失败！
)

:end
echo.
echo 按任意键退出...
pause >nul