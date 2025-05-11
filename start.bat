@echo off
setlocal

:: 从.env文件加载环境变量，而不是使用占位符
:: 这样可以避免环境变量未正确设置导致的连接问题

:: 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo Python未安装，请先安装Python
    pause
    exit /b 1
)

:: 检查并安装依赖
pip show colorama >nul 2>&1 || pip install colorama
pip show python-dotenv >nul 2>&1 || pip install python-dotenv
pip show openai >nul 2>&1 || pip install openai

:: 安装uv工具
pip install uv 2>nul || (
    echo 安装uv失败，正在尝试其他方式安装...
    python -m pip install uv
)

:: 设置Python环境变量
set PYTHONPATH=.
set PYTHONIOENCODING=utf-8
:: 使用uv运行程序
echo 正在启动网络安全智能系统...
uv run main.py
if errorlevel 1 (
   
    pause
    exit /b 1
)

pause