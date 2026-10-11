"""
PolicyLens 启动脚本
双击桌面快捷方式时由此文件执行。
"""
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

# 确保工作目录始终是本文件所在目录（即 gongkao_ai/）
BASE_DIR = Path(__file__).resolve().parent
PORT = 8501
URL = f"http://localhost:{PORT}"


def main():
    print("=" * 50)
    print("  公考智能解析助手 PolicyLens")
    print("  正在启动 Streamlit 服务，请稍候...")
    print("=" * 50)

    # 使用当前 Python 环境的 streamlit
    streamlit_cmd = [
        sys.executable, "-m", "streamlit", "run",
        str(BASE_DIR / "app.py"),
        "--server.port", str(PORT),
        # 强制仅监听本机：Web 界面无鉴权，不能暴露到局域网
        "--server.address", "127.0.0.1",
    ]

    try:
        proc = subprocess.Popen(
            streamlit_cmd,
            cwd=str(BASE_DIR),
        )
        print(f"Streamlit 服务已启动（PID: {proc.pid}）")
        print(f"浏览器即将打开：{URL}")
        time.sleep(2)
        webbrowser.open(URL)
        print("按 Ctrl+C 或关闭此窗口以停止服务。")
        proc.wait()
    except KeyboardInterrupt:
        print("\n用户中断，正在关闭服务...")
        proc.terminate()
    except FileNotFoundError:
        print("错误：未找到 streamlit，请确认已执行 pip install -r requirements.txt")
        input("按 Enter 退出...")


if __name__ == "__main__":
    main()
