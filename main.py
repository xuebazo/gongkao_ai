"""
公考智能解析助手 - 主程序入口
菜单式交互界面
"""
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from config import config
from utils.input_helper import get_multiline_input, cleanup_temp_file
from modules.favorites import Favorites

# Rich 库可选导入：若未安装则退化为纯文本输出
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()
    _HAS_RICH = True
except ImportError:
    console = None
    _HAS_RICH = False

# 非 TTY 环境（管道/重定向/CI）强制退化为纯文本，避免 Rich 编码崩溃
if _HAS_RICH and not sys.stdout.isatty():
    console = None
    _HAS_RICH = False


def _print(text: str = "", **kwargs: Any) -> None:
    """统一输出：Rich 环境下用 console.print，否则用内置 print"""
    if _HAS_RICH and console is not None:
        try:
            console.print(text, **kwargs)
        except UnicodeEncodeError:
            import re
            clean = re.sub(r"\[/?\w+\s*\]", "", text)
            print(clean)
    else:
        # 去掉 Rich 标记语法
        import re
        clean = re.sub(r"\[/?\w+\s*\]", "", text)
        print(clean)

MENU_OPTIONS = {
    "1": ("📄 政策文件解析", "导入政策文件，自动提取考点与结构化信息"),
    "2": ("📝 申论真题评阅", "提交申论文章，获取AI评分与写作建议"),
    "3": ("🎤 面试模拟训练", "AI模拟面试官，进行结构化面试练习"),
    "4": ("⚙️  系统配置", "查看 API 与模型配置"),
    "5": ("📋 错题本", "查看申论与面试薄弱点统计"),
    "6": ("📜 历史记录", "查看过往政策解析、申论批改与面试对练记录"),
    "7": ("⭐ 我的收藏本", "查看已收藏的解析/批改/面试报告"),
    "0": ("🚪 退出系统", "退出公考智能解析助手"),
}


def _display_analysis_result(result: dict[str, Any]) -> None:
    """美化显示分析结果"""
    if "error" in result:
        _print(f"[red]错误: {result['error']}[/red]")
        return

    if "raw_response" in result:
        _print("[yellow]API 返回了非标准格式，以下是原始内容:[/yellow]")
        _print(result["raw_response"])
        return

    # 四维度格式化展示
    _print()
    if _HAS_RICH and console is not None:
        try:
            console.print(Panel.fit(result.get("core_signal", "无"), title="[bold]核心信号[/bold]", border_style="yellow"))
        except UnicodeEncodeError:
            print(f"【核心信号】{result.get('core_signal', '无')}")
    else:
        print(f"【核心信号】{result.get('core_signal', '无')}")
    _print()

    quotes = result.get("golden_quotes", [])
    if quotes:
        _print("[bold]申论金句[/bold]")
        for i, q in enumerate(quotes, 1):
            _print(f"  {i}. [yellow]\"{q.get('quote', '')}\"[/yellow]")
            ref = q.get("paragraph_ref", "")
            if ref:
                _print(f"     [dim]出处: {ref}[/dim]")
            _print(f"     [dim]适用: {q.get('source', '')}[/dim]")
        _print()

    angles = result.get("exam_angles", [])
    if angles:
        _print("[bold]申论出题角度[/bold]")
        for i, a in enumerate(angles, 1):
            _print(f"  {i}. [cyan]{a.get('angle', '')}[/cyan]")
            _print(f"     [dim]{a.get('description', '')}[/dim]")
            org = a.get("material_organization", "")
            if org:
                _print(f"     [green]材料组织建议: {org}[/green]")
        _print()

    materials = result.get("interview_material", [])
    if materials:
        _print("[bold]面试观点素材[/bold]")
        for i, m in enumerate(materials, 1):
            _print(f"  {i}. [green]{m.get('viewpoint', '')}[/green]")
            _print(f"     [dim]{m.get('argument', '')}[/dim]")
        _print()

    # Deep 模式专属维度
    misunderstandings = result.get("common_misunderstandings", [])
    if misunderstandings:
        _print("[bold]常见解读误区[/bold]")
        for i, m in enumerate(misunderstandings, 1):
            _print(f"  {i}. [red]误区: {m.get('misunderstanding', '')}[/red]")
            _print(f"     [dim]正解: {m.get('correction', '')}[/dim]")
        _print()

    cross_refs = result.get("policy_cross_references", [])
    if cross_refs:
        _print("[bold]政策交叉关联[/bold]")
        for i, c in enumerate(cross_refs, 1):
            _print(f"  {i}. [cyan]关联政策: {c.get('related_policy', '')}[/cyan]")
            _print(f"     [dim]{c.get('intersection', '')}[/dim]")
        _print()


def show_banner() -> None:
    """显示欢迎横幅"""
    if _HAS_RICH and console is not None:
        try:
            banner = Panel.fit(
                f"[bold cyan]{config.APP_NAME}[/bold cyan]\n"
                f"[dim]v{config.APP_VERSION}  ·  助你高效备考[/dim]",
                border_style="cyan",
            )
            console.print(banner)
            console.print("[dim]提示：CLI 模式下支持粘贴长文本，输入完成后另起一行输入 END 并回车即可提交。[/dim]")
        except UnicodeEncodeError:
            print(f"\n{config.APP_NAME} v{config.APP_VERSION}")
            print("-" * 40)
            print("提示：CLI 模式下支持粘贴长文本，输入完成后另起一行输入 END 并回车即可提交。")
    else:
        print(f"\n{config.APP_NAME} v{config.APP_VERSION}")
        print("-" * 40)
        print("提示：CLI 模式下支持粘贴长文本，输入完成后另起一行输入 END 并回车即可提交。")


def show_menu() -> None:
    """显示主菜单"""
    if _HAS_RICH and console is not None:
        try:
            table = Table(title="主菜单", show_header=False, border_style="blue")
            table.add_column("选项", style="cyan bold", width=4)
            table.add_column("功能", style="white")
            table.add_column("说明", style="dim")
            for key, (name, desc) in MENU_OPTIONS.items():
                table.add_row(key, name, desc)
            console.print(table)
        except UnicodeEncodeError:
            print("\n主菜单:")
            for key, (name, desc) in MENU_OPTIONS.items():
                print(f"  {key}. {name} - {desc}")
    else:
        print("\n主菜单:")
        for key, (name, desc) in MENU_OPTIONS.items():
            print(f"  {key}. {name} - {desc}")


def handle_policy_analyzer() -> None:
    """政策文件解析入口"""
    from modules.policy_analyzer import PolicyAnalyzer

    _print("[bold cyan]政策文件智能解析[/bold cyan]")

    # 模式选择
    _print("[dim]分析模式: [1] 快速(四维)  [2] 深度(六维)[/dim]")
    if _HAS_RICH and console is not None:
        mode_choice = console.input("[cyan]请选择模式 (默认1): [/cyan]").strip()
    else:
        mode_choice = input("请选择模式 (默认1): ").strip()

    analysis_type = "deep" if mode_choice == "2" else "quick"
    _print(f"[dim]当前模式: {'深度(六维)' if analysis_type == 'deep' else '快速(四维)'}[/dim]")
    _print()

    # 输入方式选择
    _print("[bold]请选择输入方式:[/bold]")
    _print("[dim]  [1] 粘贴文本  [2] 输入文件路径[/dim]")
    if _HAS_RICH and console is not None:
        input_choice = console.input("[cyan]请选择 (默认1): [/cyan]").strip()
    else:
        input_choice = input("请选择 (默认1): ").strip()

    analyzer = PolicyAnalyzer()
    favs = Favorites()
    temp_file_path: str | None = None
    source_file: str | None = None   # 记录来源文件路径
    source_text: str = ""             # 记录原始文本（用于报告标题）

    try:
        if input_choice == "2":
            # 文件路径模式
            if _HAS_RICH and console is not None:
                file_path = console.input("[cyan]请输入政策文件路径: [/cyan]").strip()
            else:
                file_path = input("请输入政策文件路径: ").strip()

            if not Path(file_path).exists():
                _print(f"[red]文件未找到: {file_path}[/red]")
                return

            source_file = file_path
            _print("[dim]正在读取文件并分析...[/dim]")
            result = parse_policy_file(file_path, analyzer, analysis_type)
            source_text = Path(file_path).read_text(encoding="utf-8")
        else:
            # 粘贴文本模式
            _print("[dim]请直接粘贴政策文本内容:[/dim]")
            temp_file_path = get_multiline_input("政策文本")
            _print("[dim]正在分析...[/dim]")

            # 读取临时文件内容
            text = Path(temp_file_path).read_text(encoding="utf-8").strip()
            if not text:
                _print("[red]文本内容为空，已取消[/red]")
                return

            source_text = text
            result = analyzer.analyze_policy(text, analysis_type)

        _display_analysis_result(result)

        # 解析成功后自动保存报告
        if "error" not in result and "raw_response" not in result:
            report_path = _save_policy_report(
                result=result,
                analysis_type=analysis_type,
                source_text=source_text,
                source_file=source_file,
            )
            if report_path:
                _print(f"[dim]✅ 解析报告已自动保存至：{report_path}[/dim]")

                # 收藏提示
                _print("[dim]💡 按 S 键将此解析报告添加到收藏本，按任意其他键继续…[/dim]")
                if _HAS_RICH and console is not None:
                    fav_choice = console.input("[cyan]请选择: [/cyan]").strip().upper()
                else:
                    fav_choice = input("请选择: ").strip().upper()
                if fav_choice == "S":
                    try:
                        preview_title = source_text.strip().replace("\n", " ")[:60]
                        favs.add_favorite("policy", preview_title, str(report_path))
                        _print("[green]✅ 已收藏[/green]")
                    except Exception:
                        _print("[red]收藏失败[/red]")

    finally:
        # 清理临时文件
        if temp_file_path:
            cleanup_temp_file(temp_file_path)


def _show_favorite_prompt(fav_type: str, title: str, source_file: str) -> None:
    """显示收藏提示，用户按 S 键则添加到收藏本"""
    type_label = {"policy": "解析报告", "shenlun": "批改报告", "interview": "面试记录"}.get(fav_type, "报告")
    _print(f"[dim]💡 按 S 键将此{type_label}添加到收藏本，按任意其他键继续…[/dim]")
    if _HAS_RICH and console is not None:
        fav_choice = console.input("[cyan]请选择: [/cyan]").strip().upper()
    else:
        fav_choice = input("请选择: ").strip().upper()
    if fav_choice == "S":
        try:
            favs = Favorites()
            favs.add_favorite(fav_type, title[:60], source_file)
            _print("[green]✅ 已收藏[/green]")
        except Exception:
            _print("[red]收藏失败[/red]")


def _show_favorite_prompt_interview(topic: str) -> None:
    """面试结束后的收藏提示（扫描最新 interview 文件）"""
    output_dir = Path(__file__).resolve().parent / "output"
    files = sorted(output_dir.glob("interview_*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
    if files:
        source_file = str(files[0])
        _show_favorite_prompt("interview", topic, source_file)


def _record_interview_mistake(topic: str, mode: str, full_md: str) -> None:
    """从面试总结中提取薄弱点，自动记录到错题本"""
    try:
        from modules.mistake_tracker import MistakeTracker
        # 提取 AI 总结部分中的薄弱点
        weak_keywords = ["缺乏", "不足", "薄弱", "扣分", "短板", "过于", "问题"]
        weak_lines: list[str] = []
        in_summary = False
        for line in full_md.split("\n"):
            if "面试总结" in line or "改进建议" in line:
                in_summary = True
                continue
            if in_summary:
                for kw in weak_keywords:
                    if kw in line:
                        weak_lines.append(line.strip())
                        break
        weak_point = "; ".join(weak_lines[:3]) if weak_lines else "详见对话记录"

        tracker = MistakeTracker()
        tracker.add_interview_mistake(
            topic=f"{topic}（{mode}）",
            question="多轮面试对话",
            weak_point=weak_point,
        )
    except Exception:
        pass  # 记录失败不阻塞主流程


def _save_policy_report(
    result: dict[str, Any],
    analysis_type: str,
    source_text: str,
    source_file: str | None = None,
) -> str | None:
    """
    将政策解析结果格式化为 Markdown 报告并保存到 output/ 目录。

    返回:
        保存的文件路径，失败返回 None
    """
    output_dir = Path(__file__).resolve().parent / "output"
    output_dir.mkdir(exist_ok=True)

    # 生成标题：取原文前60字
    preview = source_text.strip().replace("\n", " ")[:60]
    mode_label = "深度六维" if analysis_type == "deep" else "快速四维"
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    display_time = now.strftime("%Y-%m-%d %H:%M:%S")

    lines: list[str] = [
        f"# 政策解析报告 | {preview}",
        "",
        f"- **生成时间**：{display_time}",
        f"- **分析模式**：{mode_label}",
    ]

    if source_file:
        lines.append(f"- **来源文件**：{source_file}")

    lines.append("")
    lines.append("---")
    lines.append("")

    # 核心信号
    core = result.get("core_signal", "")
    if core:
        lines.append("## 📌 核心信号")
        lines.append("")
        lines.append(f"> {core}")
        lines.append("")

    # 金句
    quotes = result.get("golden_quotes", [])
    if quotes:
        lines.append("## 🏅 申论金句")
        lines.append("")
        for i, q in enumerate(quotes, 1):
            lines.append(f"**{i}. {q.get('quote', '')}**")
            ref = q.get("paragraph_ref", "")
            if ref:
                lines.append(f"- 出处：{ref}")
            src = q.get("source", "")
            if src:
                lines.append(f"- 适用场景：{src}")
            lines.append("")

    # 出题角度
    angles = result.get("exam_angles", [])
    if angles:
        lines.append("## 📝 申论出题角度")
        lines.append("")
        for i, a in enumerate(angles, 1):
            lines.append(f"**{i}. {a.get('angle', '')}**")
            lines.append(f"{a.get('description', '')}")
            org = a.get("material_organization", "")
            if org:
                lines.append(f"- 材料组织建议：{org}")
            lines.append("")

    # 面试素材
    materials = result.get("interview_material", [])
    if materials:
        lines.append("## 🎤 面试观点素材")
        lines.append("")
        for i, m in enumerate(materials, 1):
            lines.append(f"**{m.get('viewpoint', '')}**")
            lines.append(f"{m.get('argument', '')}")
            lines.append("")

    # Deep 模式专属
    misunderstandings = result.get("common_misunderstandings", [])
    if misunderstandings:
        lines.append("## ⚠️ 常见解读误区")
        lines.append("")
        for i, m in enumerate(misunderstandings, 1):
            lines.append(f"**误区 {i}**：{m.get('misunderstanding', '')}")
            lines.append(f"- 正解：{m.get('correction', '')}")
            lines.append("")

    cross_refs = result.get("policy_cross_references", [])
    if cross_refs:
        lines.append("## 🔗 政策交叉关联")
        lines.append("")
        for i, c in enumerate(cross_refs, 1):
            lines.append(f"**关联政策**：{c.get('related_policy', '')}")
            lines.append(f"- {c.get('intersection', '')}")
            lines.append("")

    # 写入文件
    report_path = output_dir / f"policy_{timestamp}.md"
    try:
        report_path.write_text("\n".join(lines), encoding="utf-8")
        return str(report_path)
    except Exception as e:
        # 静默失败，不影响主流程
        import warnings
        warnings.warn(f"保存政策解析报告失败: {e}")
        return None


def handle_shenlun_reviewer() -> None:
    """申论真题评阅入口"""
    from datetime import datetime
    from modules.shenlun_reviewer import ShenlunReviewer

    _print("[bold cyan]申论真题深度拆解[/bold cyan]")
    _print()

    # 题型选择
    _print("[bold]请选择题型:[/bold]")
    _print("[dim]  1. 概括归纳   2. 综合分析   3. 贯彻执行   4. 申发论述(大作文)[/dim]")
    if _HAS_RICH and console is not None:
        type_choice = console.input("[cyan]请选择 (默认4): [/cyan]").strip()
    else:
        type_choice = input("请选择 (默认4): ").strip()

    type_map = {"1": "概括归纳", "2": "综合分析", "3": "贯彻执行", "4": "申发论述"}
    question_type = type_map.get(type_choice, "申发论述")
    _print(f"[dim]当前题型: {question_type}[/dim]")
    _print()

    # Pro 模式选项
    _print("[dim]是否启用 Pro 模式（更深度评阅，Token 消耗约多 50%）？[y/N][/dim]")
    if _HAS_RICH and console is not None:
        pro_choice = console.input("[cyan]请选择: [/cyan]").strip().lower()
    else:
        pro_choice = input("请选择: ").strip().lower()
    use_pro = pro_choice == "y"
    if use_pro:
        _print("[dim]Pro 模式已启用[/dim]")
    _print()

    # 输入方式选择
    _print("[dim]输入方式: [1] 手动输入  [2] 从文件读取[/dim]")
    if _HAS_RICH and console is not None:
        input_mode = console.input("[cyan]请选择 (默认1): [/cyan]").strip()
    else:
        input_mode = input("请选择 (默认1): ").strip()

    if input_mode == "2":
        question, essay_text = _read_essay_from_files()
    else:
        question, essay_text = _read_essay_manual()

    if question is None or essay_text is None:
        return

    # 若用户选 Pro 模式，在题目参数前拼接关键字
    eval_question = question
    if use_pro:
        eval_question = "Pro模式 " + question

    # 调用评阅
    _print("[dim]正在调用 AI 评阅（约需 10-30 秒）...[/dim]")
    reviewer = ShenlunReviewer()
    result = reviewer.evaluate_essay(eval_question, essay_text, question_type)

    if "error" in result:
        _print(f"[red]评阅失败: {result['error']}[/red]")
        return

    feedback = result["feedback"]
    _print()
    _print("[bold green]========== 评阅报告 ==========[/bold green]")

    # 截断警告
    if result.get("truncated"):
        _print("[yellow]⚠️ 提示：您的文章已超过 4000 字，系统已自动截取前 4000 字进行评阅，评分结果仅供参考。[/yellow]")

    _print(feedback)
    _print("[bold green]==============================[/bold green]")

    # 保存到 output 目录
    output_dir = Path(__file__).resolve().parent / "output"
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"shenlun_feedback_{timestamp}.md"
    output_file.write_text(feedback, encoding="utf-8")
    _print(f"[dim]报告已保存至: {output_file}[/dim]")

    # 自动记录到错题本
    try:
        from modules.mistake_tracker import MistakeTracker
        tracker = MistakeTracker()
        tracker.add_shenlun_mistake(
            question=question,
            question_type=question_type,
            feedback=feedback,
        )
        _print("[dim]已自动记录到错题本[/dim]")
    except Exception:
        pass

    # 导出选项
    _print("[dim]导出选项: [X] 小红书模版  [C] 社群模版  [Enter] 跳过[/dim]")
    if _HAS_RICH and console is not None:
        export_choice = console.input("[cyan]请选择: [/cyan]").strip().upper()
    else:
        export_choice = input("请选择: ").strip().upper()

    if export_choice in ("X", "C"):
        try:
            from modules.export_templates import export_shenlun_feedback
            mode = "xiaohongshu" if export_choice == "X" else "community"
            exported = export_shenlun_feedback(feedback, mode=mode)
            export_file = output_dir / f"shenlun_export_{timestamp}.md"
            export_file.write_text(exported, encoding="utf-8")
            _print(f"[dim]已导出至: {export_file}[/dim]")
        except Exception:
            pass

    # 收藏提示
    _print("[dim]💡 按 S 键将此批改报告添加到收藏本，按任意其他键继续…[/dim]")
    if _HAS_RICH and console is not None:
        fav_choice = console.input("[cyan]请选择: [/cyan]").strip().upper()
    else:
        fav_choice = input("请选择: ").strip().upper()
    if fav_choice == "S":
        try:
            favs = Favorites()
            preview_title = question.strip().replace("\n", " ")[:60]
            favs.add_favorite("shenlun", preview_title, str(output_file))
            _print("[green]✅ 已收藏[/green]")
        except Exception:
            _print("[red]收藏失败[/red]")


def _read_essay_manual() -> tuple[str | None, str | None]:
    """手动输入题目和文章"""
    temp_question_path: str | None = None
    temp_essay_path: str | None = None

    try:
        # 题目输入
        _print("[bold]请输入申论真题题目[/bold]")
        temp_question_path = get_multiline_input("真题题目")
        question = Path(temp_question_path).read_text(encoding="utf-8").strip()
        if not question:
            _print("[red]题目不能为空，已取消[/red]")
            return None, None

        _print()
        # 文章输入
        _print("[bold]请输入你的申论文章[/bold]")
        temp_essay_path = get_multiline_input("申论文章")
        essay_text = Path(temp_essay_path).read_text(encoding="utf-8").strip()
        if not essay_text:
            _print("[red]文章不能为空，已取消[/red]")
            return None, None

        return question, essay_text

    finally:
        # 清理临时文件
        if temp_question_path:
            cleanup_temp_file(temp_question_path)
        if temp_essay_path:
            cleanup_temp_file(temp_essay_path)


def _read_essay_from_files() -> tuple[str | None, str | None]:
    """从文件读取题目和文章"""
    if _HAS_RICH and console is not None:
        q_path = console.input("[cyan]题目文件路径: [/cyan]").strip()
        e_path = console.input("[cyan]文章文件路径: [/cyan]").strip()
    else:
        q_path = input("题目文件路径: ").strip()
        e_path = input("文章文件路径: ").strip()

    try:
        question = Path(q_path).read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        _print(f"[red]题目文件未找到: {q_path}[/red]")
        return None, None
    except Exception as e:
        _print(f"[red]读取题目文件失败: {e}[/red]")
        return None, None

    try:
        essay_text = Path(e_path).read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        _print(f"[red]文章文件未找到: {e_path}[/red]")
        return None, None
    except Exception as e:
        _print(f"[red]读取文章文件失败: {e}[/red]")
        return None, None

    if not question or not essay_text:
        _print("[red]题目或文章为空[/red]")
        return None, None

    return question, essay_text


def handle_interview_trainer() -> None:
    """面试模拟训练入口"""
    from modules.interview_trainer import InterviewTrainer

    _print("[bold cyan]面试模拟对练[/bold cyan]")
    _print()

    # 模式选择：普通 vs 高仿真
    _print("[bold]请选择训练模式:[/bold]")
    _print("[dim]  1. 普通模式（自定义主题与轮次）  2. 高仿真模式（10分钟3题，自动计时）[/dim]")
    if _HAS_RICH and console is not None:
        train_mode = console.input("[cyan]请选择 (默认1): [/cyan]").strip()
    else:
        train_mode = input("请选择 (默认1): ").strip()

    temp_topic_path: str | None = None

    try:
        if train_mode == "2":
            # 高仿真模式
            _print("[bold]请输入面试主题[/bold]")
            temp_topic_path = get_multiline_input("面试主题")
            topic = Path(temp_topic_path).read_text(encoding="utf-8").strip()
            if not topic:
                _print("[red]主题不能为空，已取消[/red]")
                return

            _print(f"[dim]主题: {topic} | 10分钟3题 | 自动计时[/dim]")
            trainer = InterviewTrainer()
            try:
                full_md = trainer.full_simulation(topic)
            except Exception as e:
                _print(f"[red]面试异常: {e}[/red]")
                return

            # 自动记录面试错题
            _record_interview_mistake(topic, "高仿真面试", full_md)

            # 收藏提示（扫描最新 output 文件）
            _show_favorite_prompt_interview(topic)
            return

        # 普通模式
        _print("[bold]请选择面试方向:[/bold]")
        _print("[dim]  1. 结构化（综合分析/组织管理/人际应急）  2. 专业面（车辆工程方向）[/dim]")
        if _HAS_RICH and console is not None:
            mode_choice = console.input("[cyan]请选择 (默认1): [/cyan]").strip()
        else:
            mode_choice = input("请选择 (默认1): ").strip()
        mode = "专业面" if mode_choice == "2" else "结构化"

        _print("[bold]请输入面试主题[/bold]")
        temp_topic_path = get_multiline_input("面试主题")
        topic = Path(temp_topic_path).read_text(encoding="utf-8").strip()
        if not topic:
            _print("[red]主题不能为空，已取消[/red]")
            return

        if _HAS_RICH and console is not None:
            rounds_str = console.input("[cyan]训练轮次 (默认3): [/cyan]").strip()
        else:
            rounds_str = input("训练轮次 (默认3): ").strip()
        try:
            max_rounds = int(rounds_str) if rounds_str else 3
        except ValueError:
            max_rounds = 3

        _print(f"[dim]方向: {mode} | 主题: {topic} | {max_rounds}轮[/dim]")
        _print()

        trainer = InterviewTrainer(max_rounds=max_rounds)
        try:
            full_md = trainer.start_session(topic, mode=mode)
        except Exception as e:
            _print(f"[red]面试异常: {e}[/red]")
            return

        # 自动记录面试错题
        _record_interview_mistake(topic, mode, full_md)

        # 收藏提示
        _show_favorite_prompt_interview(topic)

    finally:
        # 清理临时文件
        if temp_topic_path:
            cleanup_temp_file(temp_topic_path)


def handle_config() -> None:
    """系统配置入口"""
    if _HAS_RICH and console is not None:
        try:
            console.print(Panel.fit("系统配置", border_style="green"))
        except UnicodeEncodeError:
            print("\n=== 系统配置 ===")
    else:
        print("\n=== 系统配置 ===")
    _print(f"[bold]API Key 状态:[/bold] {'已配置' if config.DEEPSEEK_API_KEY else '未配置'}")
    _print(f"[bold]API Base URL:[/bold] {config.DEEPSEEK_BASE_URL}")
    _print(f"[bold]模型:[/bold] {config.DEEPSEEK_MODEL}")
    _print()
    _print("[dim]提示：在项目根目录创建 .env 文件并设置 DEEPSEEK_API_KEY=your_key[/dim]")


def handle_mistake_tracker() -> None:
    """错题本统计入口"""
    try:
        from modules.mistake_tracker import MistakeTracker
    except ImportError:
        _print("[red]错题本模块未找到[/red]")
        return

    tracker = MistakeTracker()
    stats = tracker.get_stats()

    _print("[bold cyan]错题本统计[/bold cyan]")
    _print()
    _print(f"[bold]申论错题: {stats['shenlun_total']} 条[/bold]")
    _print(f"[bold]面试错题: {stats['interview_total']} 条[/bold]")
    _print()

    if stats["shenlun_by_type"]:
        _print("[bold]申论按题型分布:[/bold]")
        for r in stats["shenlun_by_type"]:
            _print(f"  {r['question_type']}: {r['cnt']} 条")

    if stats["interview_by_topic"]:
        _print("[bold]面试按主题分布:[/bold]")
        for r in stats["interview_by_topic"]:
            _print(f"  {r['topic']}: {r['cnt']} 条")

    if stats["recent"]:
        _print()
        _print("[bold]最近记录:[/bold]")
        for r in stats["recent"]:
            _print(f"  [dim]{r['created_at']}[/dim] {r['question'][:50]}")

    # 查看详情 / 手动添加选项
    _print()
    _print("[dim]输入 's' 查看申论错题详情, 'i' 查看面试错题, 'a' 手动添加, 其他键返回[/dim]")
    if _HAS_RICH and console is not None:
        choice = console.input("[cyan]请选择: [/cyan]").strip().lower()
    else:
        choice = input("请选择: ").strip().lower()

    if choice == "s":
        mistakes = tracker.get_shenlun_mistakes(limit=10)
        for i, m in enumerate(mistakes, 1):
            _print(f"\n[bold]{i}. [{m['question_type']}] {m['question'][:60]}[/bold]")
            if m.get("weak_points"):
                _print(f"   [dim]薄弱点: {m['weak_points'][:100]}[/dim]")
    elif choice == "i":
        mistakes = tracker.get_interview_mistakes(limit=10)
        for i, m in enumerate(mistakes, 1):
            _print(f"\n[bold]{i}. [{m['topic']}] {m['question'][:60]}[/bold]")
            if m.get("weak_point"):
                _print(f"   [dim]薄弱点: {m['weak_point'][:100]}[/dim]")
    elif choice == "a":
        # 手动添加流程
        _print()
        _print("[bold]手动添加错题[/bold]")
        _print("[dim]类型: [1] 申论错题  [2] 面试错题[/dim]")
        if _HAS_RICH and console is not None:
            add_type = console.input("[cyan]请选择 (默认1): [/cyan]").strip()
        else:
            add_type = input("请选择 (默认1): ").strip()

        if add_type == "2":
            _print("[bold]请输入面试主题[/bold]")
            temp_path = get_multiline_input("面试主题")
            topic = Path(temp_path).read_text(encoding="utf-8").strip()
            cleanup_temp_file(temp_path)
            if not topic:
                return
            _print("[bold]请输入面试题目[/bold]")
            temp_path = get_multiline_input("面试题目")
            question = Path(temp_path).read_text(encoding="utf-8").strip()
            cleanup_temp_file(temp_path)
            if not question:
                return
            _print("[bold]请输入薄弱点描述[/bold]")
            temp_path = get_multiline_input("薄弱点描述")
            weak_point = Path(temp_path).read_text(encoding="utf-8").strip()
            cleanup_temp_file(temp_path)
            if not weak_point:
                return
            tracker.add_interview_mistake_manual(topic, question, weak_point)
            _print("[green]✅ 面试错题已添加[/green]")
        else:
            _print("[bold]请输入申论题目[/bold]")
            temp_path = get_multiline_input("申论题目")
            question = Path(temp_path).read_text(encoding="utf-8").strip()
            cleanup_temp_file(temp_path)
            if not question:
                return
            _print("[bold]请选择题型[/bold]")
            _print("[dim]1.概括归纳 2.综合分析 3.贯彻执行 4.申发论述[/dim]")
            if _HAS_RICH and console is not None:
                qt = console.input("[cyan]请选择 (默认4): [/cyan]").strip()
            else:
                qt = input("请选择 (默认4): ").strip()
            qt_map = {"1": "概括归纳", "2": "综合分析", "3": "贯彻执行", "4": "申发论述"}
            question_type = qt_map.get(qt, "申发论述")
            _print("[bold]请输入薄弱点描述[/bold]")
            temp_path = get_multiline_input("薄弱点描述")
            weak_points = Path(temp_path).read_text(encoding="utf-8").strip()
            cleanup_temp_file(temp_path)
            if not weak_points:
                return
            tracker.add_shenlun_mistake_manual(question, question_type, weak_points)
            _print("[green]✅ 申论错题已添加[/green]")


def handle_policy_history() -> None:
    """历史记录查看入口（政策解析 / 申论批改 / 面试对练）"""
    while True:
        _print("[bold cyan]📜 历史记录[/bold cyan]")
        _print()
        _print("[bold]请选择记录类型:[/bold]")
        _print("[dim]  1. 政策解析记录    2. 申论批改记录    3. 面试对练记录    b. 返回[/dim]")
        if _HAS_RICH and console is not None:
            cat_choice = console.input("[cyan]请选择: [/cyan]").strip().lower()
        else:
            cat_choice = input("请选择: ").strip().lower()

        if cat_choice == "b":
            return

        pattern_map = {"1": "policy_*.md", "2": "shenlun_feedback_*.md", "3": "interview_*.md"}
        type_map_label = {"1": "政策解析", "2": "申论批改", "3": "面试对练"}
        pattern = pattern_map.get(cat_choice)
        if not pattern:
            _print("[red]无效选择[/red]")
            _print()
            continue

        _handle_history_list(pattern, type_map_label[cat_choice])


def _handle_history_list(pattern: str, label: str) -> None:
    """通用的历史记录列表/查看/删除交互"""
    output_dir = Path(__file__).resolve().parent / "output"

    while True:
        files = sorted(
            output_dir.glob(pattern),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )[:20]

        if not files:
            _print(f"[yellow]暂无{label}记录[/yellow]")
            return

        _print(f"[bold]{label}记录[/bold]（最近 20 条）")
        _print()

        if _HAS_RICH and console is not None:
            from rich.table import Table
            table = Table(show_header=True, border_style="blue")
            table.add_column("序号", style="cyan bold", width=5)
            table.add_column("文件名", style="white")
            table.add_column("生成时间", style="dim")
            table.add_column("操作", style="red")
            for i, f in enumerate(files, 1):
                mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                table.add_row(str(i), f.name, mtime, f"删除：d{i}")
            console.print(table)
        else:
            for i, f in enumerate(files, 1):
                mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                print(f"  {i}. {f.name}  [{mtime}]  删除：d{i}")

        _print()
        _print("[dim]输入序号查看详情 | 输入 d+序号 删除 | 输入 b 返回[/dim]")
        if _HAS_RICH and console is not None:
            choice = console.input("[cyan]请选择: [/cyan]").strip()
        else:
            choice = input("请选择: ").strip()

        if choice.lower() == "b":
            return

        if choice.lower().startswith("d"):
            try:
                idx = int(choice[1:])
                if 1 <= idx <= len(files):
                    target = files[idx - 1]
                    if _HAS_RICH and console is not None:
                        confirm = console.input(f"[yellow]确定删除 {target.name} 吗？(y/n): [/yellow]").strip().lower()
                    else:
                        confirm = input(f"确定删除 {target.name} 吗？(y/n): ").strip().lower()
                    if confirm == "y":
                        target.unlink()
                        _print(f"[green]✅ 已删除: {target.name}[/green]")
                    else:
                        _print("[dim]已取消[/dim]")
                else:
                    _print("[red]无效序号[/red]")
            except ValueError:
                _print("[red]无效输入[/red]")
            _print()
            continue

        try:
            idx = int(choice)
            if 1 <= idx <= len(files):
                selected = files[idx - 1]
                _print()
                _print(f"[bold]查看: {selected.name}[/bold]")
                _print("-" * 60)
                content = selected.read_text(encoding="utf-8")
                _print(content)
                _print("-" * 60)
                _print()
                _print("[dim]按 Enter 返回列表...[/dim]")
                input()
            else:
                _print("[red]无效序号[/red]")
                _print()
        except ValueError:
            _print("[red]无效输入[/red]")
            _print()


def handle_favorites() -> None:
    """我的收藏本入口"""
    favs = Favorites()

    # 搜索
    _print("[bold cyan]⭐ 我的收藏本[/bold cyan]")
    _print()
    _print("[dim]输入关键词搜索（直接回车显示全部）[/dim]")
    if _HAS_RICH and console is not None:
        keyword = console.input("[cyan]搜索: [/cyan]").strip()
    else:
        keyword = input("搜索: ").strip()
    items = favs.search_favorites(keyword) if keyword else favs.list_favorites()

    if not items:
        if keyword:
            _print(f"[yellow]未找到包含「{keyword}」的收藏[/yellow]")
        else:
            _print("[yellow]收藏本还是空的，去政策解析/申论批改/面试对练里按S收藏吧！[/yellow]")
        return

    while True:
        _print()
        _print(f"[bold cyan]⭐ 我的收藏本[/bold cyan]（共 {len(items)} 条）")
        if keyword:
            _print(f"[dim]当前搜索: {keyword}[/dim]")
        _print()

        type_labels = {"policy": "政策", "shenlun": "申论", "interview": "面试"}
        type_colors = {"policy": "cyan", "shenlun": "green", "interview": "yellow"}

        if _HAS_RICH and console is not None:
            from rich.table import Table
            table = Table(show_header=True, border_style="blue")
            table.add_column("序号", style="cyan bold", width=5)
            table.add_column("类型", style="white", width=6)
            table.add_column("标题", style="white")
            table.add_column("收藏时间", style="dim")
            table.add_column("操作", style="red")
            for i, item in enumerate(items, 1):
                t = item.get("type", "")
                color = type_colors.get(t, "white")
                label = type_labels.get(t, t)
                title = item.get("title", "无标题")[:50]
                table.add_row(
                    str(i),
                    f"[{color}]{label}[/{color}]",
                    title,
                    item.get("created_at", ""),
                    f"删除：d{i}",
                )
            console.print(table)
        else:
            for i, item in enumerate(items, 1):
                t = item.get("type", "")
                label = type_labels.get(t, t)
                title = item.get("title", "无标题")[:50]
                print(f"  {i}. [{label}] {title}  {item.get('created_at', '')}  删除：d{i}")

        _print()
        _print("[dim]输入序号查看详情 | 输入 d+序号 删除 | 输入 b 返回菜单[/dim]")
        if _HAS_RICH and console is not None:
            choice = console.input("[cyan]请选择: [/cyan]").strip()
        else:
            choice = input("请选择: ").strip()

        if choice.lower() == "b":
            return

        # 删除操作
        if choice.lower().startswith("d"):
            try:
                idx = int(choice[1:])
                if 1 <= idx <= len(items):
                    title = items[idx - 1].get("title", "此收藏")[:30]
                    if _HAS_RICH and console is not None:
                        confirm = console.input(
                            f"[yellow]确定删除「{title}」吗？(y/n): [/yellow]"
                        ).strip().lower()
                    else:
                        confirm = input(f"确定删除「{title}」吗？(y/n): ").strip().lower()
                    if confirm == "y":
                        favs.remove_favorite(idx - 1)
                        _print("[green]✅ 已删除[/green]")
                        items = favs.list_favorites()
                        if not items:
                            _print("[yellow]收藏本还是空的，去政策解析/申论批改/面试对练里按S收藏吧！[/yellow]")
                            return
                    else:
                        _print("[dim]已取消[/dim]")
                else:
                    _print("[red]无效序号[/red]")
            except ValueError:
                _print("[red]无效输入，格式: d1 / d2 / ...[/red]")
            _print()
            continue

        # 查看操作
        try:
            idx = int(choice)
            if 1 <= idx <= len(items):
                _print()
                _print(f"[bold]查看收藏: {items[idx - 1].get('title', '无标题')[:60]}[/bold]")
                _print("-" * 60)
                content = favs.view_favorite(idx - 1)
                if content:
                    _print(content)
                else:
                    _print("[red]无法读取该收藏对应的文件[/red]")
                _print("-" * 60)
                _print()
                _print("[dim]按 Enter 返回列表...[/dim]")
                input()
            else:
                _print("[red]无效序号[/red]")
                _print()
        except ValueError:
            _print("[red]无效输入[/red]")
            _print()


def parse_policy_file(file_path: str, analyzer: Any, analysis_type: str = "quick") -> dict[str, Any]:
    """读取政策文件内容"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        return {"error": f"文件未找到: {file_path}"}
    except Exception as e:
        return {"error": f"读取文件失败: {e}"}
    return analyzer.analyze_policy(text, analysis_type)


HANDLERS = {
    "1": handle_policy_analyzer,
    "2": handle_shenlun_reviewer,
    "3": handle_interview_trainer,
    "4": handle_config,
    "5": handle_mistake_tracker,
    "6": handle_policy_history,
    "7": handle_favorites,
}


# ── 测试入口 ──

TEST_POLICY_FILE = Path(__file__).resolve().parent / "test_policy.txt"


def run_test(analysis_type: str = "quick") -> None:
    """
    测试函数：从本地 test_policy.txt 读取政策文本，调用 PolicyAnalyzer，
    将结果以美观方式打印出来。

    参数:
        analysis_type: "quick"（四维）或 "deep"（六维）
    """
    from modules.policy_analyzer import PolicyAnalyzer

    if not TEST_POLICY_FILE.exists():
        _print(f"[red]测试文件不存在: {TEST_POLICY_FILE}[/red]")
        _print("[dim]请在项目根目录创建 test_policy.txt 文件[/dim]")
        return

    mode_label = "深度(六维)" if analysis_type == "deep" else "快速(四维)"
    _print(f"[bold]>>> 开始测试 ({mode_label})：解析 {TEST_POLICY_FILE.name}[/bold]")
    _print("[dim]正在读取文件并调用 DeepSeek API 分析...[/dim]")
    _print()

    text = TEST_POLICY_FILE.read_text(encoding="utf-8")
    analyzer = PolicyAnalyzer()
    result = analyzer.analyze_policy(text, analysis_type)

    _display_analysis_result(result)
    _print("[bold green]>>> 测试完成[/bold green]")


# ── 主入口 ──


def main() -> None:
    """主循环 / 测试入口"""
    # 支持命令行参数: --test (快速测试) / --test --deep (深度测试)
    if "--test" in sys.argv:
        config.validate_or_exit()
        show_banner()
        _print(f"[dim]API Key 来源: {config.KEY_SOURCE}[/dim]")
        _print()
        analysis_type = "deep" if "--deep" in sys.argv else "quick"
        run_test(analysis_type)
        return

    show_banner()

    # 启动前强制校验配置，缺少 API Key 则打印提示并退出
    config.validate_or_exit()
    _print(f"[dim]API Key 来源: {config.KEY_SOURCE}[/dim]")

    while True:
        show_menu()
        if _HAS_RICH and console is not None:
            choice = console.input("\n[cyan]请输入选项: [/cyan]").strip()
        else:
            choice = input("\n请输入选项: ").strip()

        if choice == "0":
            _print("[green]感谢使用，祝备考顺利！[/green]")
            break

        handler = HANDLERS.get(choice)
        if handler:
            _print()
            handler()
            _print()
        else:
            _print("[red]无效选项，请重新选择[/red]")


if __name__ == "__main__":
    main()
