@echo off
rem 切到本脚本所在目录：换机器 / 换盘符 / 改名目录都能用
cd /d "%~dp0"
python launch.py
rem 出错时保留窗口，方便看到报错信息
if errorlevel 1 pause
