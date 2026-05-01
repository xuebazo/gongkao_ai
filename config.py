"""
配置模块 -- 从 .env 文件与系统环境变量双重途径读取 DeepSeek API Key。
优先级：系统环境变量 > .env 文件 > 默认值
若未找到 API Key，通过 validate_or_exit() 打印明确提示并退出程序。
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent
ENV_FILE = PROJECT_ROOT / ".env"

# 记录加载前系统环境变量中是否已存在 API Key（用于来源追踪）
_HAD_KEY_IN_SYS_ENV = "DEEPSEEK_API_KEY" in os.environ

# 加载 .env 文件（override=False：不覆盖已有的系统环境变量，确保系统环境变量优先）
if ENV_FILE.exists():
    load_dotenv(ENV_FILE, override=False)
else:
    load_dotenv()  # 兜底：尝试加载工作目录下的 .env


class Config:
    """全局配置单例"""

    # ── DeepSeek API 配置 ──
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = os.getenv(
        "DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"
    )
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    # ── 应用配置 ──
    APP_NAME: str = "公考智能解析助手"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # ── 配置来源追踪（调试用） ──
    KEY_SOURCE: str = ""

    @classmethod
    def _detect_key_source(cls) -> None:
        """检测 API Key 的来源（系统环境变量 or .env 文件）"""
        if not cls.DEEPSEEK_API_KEY:
            cls.KEY_SOURCE = "未找到"
        elif _HAD_KEY_IN_SYS_ENV:
            cls.KEY_SOURCE = "系统环境变量"
        elif ENV_FILE.exists():
            cls.KEY_SOURCE = ".env 文件"
        else:
            cls.KEY_SOURCE = "系统环境变量"  # 兜底

    @classmethod
    def validate(cls) -> bool:
        """校验必要配置是否存在，返回 True / False"""
        cls._detect_key_source()
        if not cls.DEEPSEEK_API_KEY:
            return False
        return True

    @classmethod
    def validate_or_exit(cls) -> None:
        """
        校验必要配置，若缺少 API Key 则打印明确提示并退出程序。

        使用方式（在 main.py 入口处调用）：
            from config import config
            config.validate_or_exit()
        """
        if cls.validate():
            return

        msg = (
            "\n"
            "=" * 60 + "\n"
            "  [ERROR] DeepSeek API Key not found\n"
            "=" * 60 + "\n"
            "\n"
            "  Please configure via one of the following:\n"
            "\n"
            "  Option 1 (recommended) -- Create .env file:\n"
            f"    Path: {ENV_FILE}\n"
            f"    Content: DEEPSEEK_API_KEY=your_key\n"
            "\n"
            "  Option 2 -- Set system environment variable:\n"
            "    Windows: set DEEPSEEK_API_KEY=your_key\n"
            "    macOS:   export DEEPSEEK_API_KEY=your_key\n"
            "\n"
            "=" * 60 + "\n"
        )
        sys.stderr.write(msg)
        sys.exit(1)


# 初始化配置实例
config = Config()
# 预检测 Key 来源（供 main.py 启动时展示）
config._detect_key_source()
