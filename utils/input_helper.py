"""
通用多行文本输入工具

提供统一的多行文本输入函数，支持 CLI 粘贴模式，
自动写入临时文件并返回文件路径。
"""
from datetime import datetime
from pathlib import Path
from typing import Any

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TMP_DIR = PROJECT_ROOT / "tmp"


def get_multiline_input(prompt: str) -> str:
    """
    获取用户多行输入，自动写入临时文件并返回文件路径。

    用户输入完成标志：单独一行输入 END 并回车。
    临时文件存放在 tmp/ 目录，文件名格式：tmp/input_YYYYMMDD_HHMMSS.txt。

    参数:
        prompt: 提示信息，显示在输入前

    返回:
        临时文件的路径（字符串）
    """
    # 确保 tmp 目录存在
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    # Rich 库可选导入
    try:
        from rich.console import Console
        console = Console()
        _has_rich = True
    except ImportError:
        console = None
        _has_rich = False

    # 显示提示
    if _has_rich and console is not None:
        console.print(f"[cyan]{prompt}[/cyan]")
        console.print("[dim]（输入完成后在单独一行输入 END 并回车确认）[/dim]")
    else:
        print(prompt)
        print("（输入完成后在单独一行输入 END 并回车确认）")

    # 收集多行输入
    lines: list[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip().upper() == "END":
            break
        lines.append(line)

    # 生成临时文件路径
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_file = TMP_DIR / f"input_{timestamp}.txt"

    # 写入文件
    content = "\n".join(lines)
    temp_file.write_text(content, encoding="utf-8")

    # 显示确认
    if _has_rich and console is not None:
        console.print(f"[green]✅ 文本已接收 ({len(content)} 字符)[/green]")
    else:
        print(f"✅ 文本已接收 ({len(content)} 字符)")

    return str(temp_file)


def cleanup_temp_file(file_path: str | Path) -> None:
    """
    删除临时文件。

    参数:
        file_path: 临时文件路径
    """
    try:
        path = Path(file_path)
        if path.exists() and path.is_file():
            path.unlink()
    except Exception as e:
        # 删除失败时打印警告但不中断程序
        import warnings
        warnings.warn(f"清理临时文件失败: {file_path}, 错误: {e}")


class TempFileCleaner:
    """
    临时文件清理上下文管理器。

    用法:
        with TempFileCleaner(temp_path) as path:
            text = Path(path).read_text(encoding="utf-8")
            # 使用 text 进行处理...
        # 退出 with 块后自动删除临时文件
    """

    def __init__(self, file_path: str | Path) -> None:
        self.file_path = Path(file_path)

    def __enter__(self) -> str:
        return str(self.file_path)

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        cleanup_temp_file(self.file_path)
