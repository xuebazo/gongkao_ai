"""
面试模拟训练模块 - InterviewTrainer

模拟体制内面试官进行多轮对练：
  - 结构化面试（综合分析/组织管理/人际应急）
  - 专业面试（车辆工程方向）

每轮：AI 出题 → 考生作答 → AI 简短反馈(50字) + 动态追问
结束：输出全场总结 + 各题表现 + 改进建议
对话记录自动保存为 output/interview_session.md

高级模式：full_simulation() 模拟"10分钟3题"高仿真结构化面试，
自动计时（思考时间/回答时间），结束后给出时间分析报告。

用法:
    from modules.interview_trainer import InterviewTrainer

    trainer = InterviewTrainer(max_rounds=3)
    trainer.start_session("基层治理", mode="结构化")    # 普通模式
    trainer.full_simulation("基层治理")                 # 高仿真模式
"""
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

try:
    from config import config
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from config import config  # type: ignore[no-redef]

# 导入通用输入工具
try:
    from utils.input_helper import get_multiline_input, cleanup_temp_file
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from utils.input_helper import get_multiline_input, cleanup_temp_file


# ── 输出目录 ──
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


# ── 高仿真模式专用提示词 ──
SIMULATION_SYSTEM_PROMPT = """你是一位经验丰富的体制内面试官（处级），正在进行一场"10分钟3题"的结构化面试。
你的风格：专业但不刻板，追问犀利但给考生留思考空间。

【面试规则】
1. 你需在首轮直接给出第一道面试题
2. 题型依次为：综合分析类 → 组织管理类 → 人际应急/情景模拟类（不重复类型）
3. 每道题必须紧扣给定主题

【输出格式】
**首轮**：第1题（综合分析）：[题目]
**第2轮**（反馈+追问）：【反馈】≤50字点评\n【追问】第2题（组织管理）：[题目]
**第3轮**（反馈+追问）：【反馈】≤50字点评\n【追问】第3题（人际/应急）：[题目]
**结束后**：输出【面试总结】
  包含：整体评级（优/良/中/差）、各题答题质量简评、主要优点、致命短板、针对性训练建议

【角色约束】
- 不夸"非常好""很全面"——体制内面试官不溢美
- 反馈要具体到考生原话中的某个词或某句话
- 三道题考察不同能力维度，互不重叠"""


# ── 模拟计时配置 ──
THINKING_TIME_LIMIT = 60       # 每题思考时间上限（秒）
TOTAL_TIME_LIMIT = 10 * 60     # 总时间上限（秒）= 10分钟
QUESTION_COUNT = 3


# ── 系统提示词 ──

STRUCTURED_SYSTEM_PROMPT = """你是一位经验丰富的体制内面试官（处级），正在对考生进行结构化面试。
你的风格：专业但不刻板，追问犀利但给考生留思考空间。

【面试规则】
1. 面试主题和轮次上限已给定，你需要在首轮先出一道面试题
2. 每题题型从以下随机抽取：综合分析类、组织管理类、人际应急类、情景模拟类
3. 题目必须紧扣给定主题，根据考生上一轮回答的质量动态调整难度和方向
4. 追问要点：
   - 深挖考生回答中的模糊表述（"你怎么定义你提到的'长效机制'？"）
   - 指出逻辑跳跃（"你从A直接跳到C，中间的B环节怎么落实？"）
   - 追问具体案例（"请举一个你实际经历过的例子"）
   - 施加时间/资源约束增加压迫感（"如果只有3天时间，你的优先序是什么？"）

【输出格式】
**首轮**：直接给出第一道面试题，格式为 "第1题：[题目]"
**中间轮**：先给上一题反馈（≤50字），再给追问，格式：
  【反馈】一句话点评
  【追问】第X题：[题目]
**最后一轮**（考生回答后）：输出全场总结，格式：
  【面试总结】
  （包含：整体表现评级、各题表现、突出优点、主要短板、针对性改进建议）

【角色约束】
- 不夸"非常好""很全面"——体制内面试官不溢美
- 反馈要具体到考生原话中的某个词或某句话
- 题目不重复，每道题考察不同能力维度"""


PROFESSIONAL_SYSTEM_PROMPT = """你是一位经验丰富的车辆工程领域面试官（技术部门负责人），正在对考生进行专业面试。
你的风格：专业严谨，追问技术细节，考察实践能力与理论基础并重。

【面试规则】
1. 面试主题和轮次上限已给定，你需要在首轮先出一道专业面试题
2. 出题方向涵盖：汽车构造原理、新能源汽车技术（电池/电机/电控）、智能网联汽车、
   制造工艺、汽车设计、车辆动力学、行业政策标准等
3. 题目根据考生上一轮回答质量动态调整：
   - 回答扎实 → 提升难度，追问更深层的技术原理
   - 回答浮于表面 → 追问具体参数、公式或工程实践细节
   - 回答有误 → 先指出错误，再给一道同领域但调整过的题目
4. 追问要点：
   - 追问具体技术参数（"你说的续航提升，电池包能量密度具体达到多少？"）
   - 追问工程权衡（"轻量化和安全性冲突时，你的设计优先级怎么排？"）
   - 追问行业视野（"特斯拉的一体化压铸对传统冲焊工艺的冲击你怎么看？"）

【输出格式】
**首轮**：直接给出第一道专业题，格式为 "第1题：[题目]"
**中间轮**：先给上一题反馈（≤50字），再给追问，格式：
  【反馈】一句话点评
  【追问】第X题：[题目]
**最后一轮**（考生回答后）：输出全场总结，格式：
  【面试总结】
  （包含：整体表现评级、各题表现、技术素养评价、知识盲区、学习建议）

【角色约束】
- 反馈要有技术含金量，不说空话套话
- 发现知识盲区要明确指出，不绕弯子
- 题目要体现车辆工程的前沿性和实践性"""


class InterviewTrainer:
    """面试模拟训练器"""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        max_rounds: int = 3,
    ) -> None:
        self.api_key = api_key or config.DEEPSEEK_API_KEY
        self.base_url = (base_url or config.DEEPSEEK_BASE_URL).rstrip("/")
        self.max_rounds = max_rounds

        if not self.api_key:
            raise ValueError("API Key 未配置")

    def start_session(self, topic: str, mode: str = "结构化") -> str:
        """
        启动一场面试模拟训练（交互式）。

        参数:
            topic: 面试主题（如 "基层治理"/"新能源汽车电池技术"）
            mode: "结构化" 或 "专业面"

        返回:
            全场对话记录的 Markdown 文本
        """
        if mode not in ("结构化", "专业面"):
            raise ValueError(f"不支持的模式: {mode}，可选 '结构化' / '专业面'")

        system_prompt = (
            STRUCTURED_SYSTEM_PROMPT if mode == "结构化" else PROFESSIONAL_SYSTEM_PROMPT
        )

        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
        ]

        # 启动面试
        init_msg = (
            f"面试主题：{topic}\n模式：{mode}面试\n最大轮次：{self.max_rounds}轮\n"
            "请给出第一道面试题。"
        )
        messages.append({"role": "user", "content": init_msg})

        md_lines: list[str] = [
            f"# 面试模拟训练记录\n",
            f"- **主题**：{topic}",
            f"- **模式**：{mode}",
            f"- **轮次**：{self.max_rounds} 轮",
            f"- **时间**：{self._timestamp()}\n",
            "---\n",
        ]

        # 逐轮进行
        # 初始化为空串：max_rounds 为 0 时循环不执行，下方总结判断仍可安全访问
        ai_response = ""
        round_num = 1
        while round_num <= self.max_rounds:
            # 调用 API 获取题目 / 反馈+追问
            ai_response = self._call_api(messages)
            messages.append({"role": "assistant", "content": ai_response})

            # 显示 AI 输出
            print(f"\n{'='*50}")
            print(ai_response)
            print(f"{'='*50}")

            # 记录到 Markdown
            md_lines.append(f"### AI（第 {round_num} 轮）\n\n{ai_response}\n\n")

            # 最后一轮只给总结，不需要用户再回答
            if "【面试总结】" in ai_response:
                break

            # 获取用户回答（使用通用多行输入）
            print("\n请输入你的回答：")
            temp_answer_path = get_multiline_input("你的回答")
            try:
                user_answer = Path(temp_answer_path).read_text(encoding="utf-8").strip()
            finally:
                cleanup_temp_file(temp_answer_path)

            # 检查是否提前结束
            if not user_answer or user_answer.upper() == "QUIT":
                md_lines.append("### 考生（提前结束）\n\n*面试提前结束*\n\n")
                break

            messages.append({"role": "user", "content": f"第{round_num}题我的回答：\n{user_answer}"})
            md_lines.append(f"### 考生（第 {round_num} 轮回答）\n\n{user_answer}\n\n")

            round_num += 1

        # 如果正常结束但 AI 还没输出总结，请求总结
        if round_num > self.max_rounds and "【面试总结】" not in ai_response:
            messages.append({"role": "user", "content": "面试结束，请输出【面试总结】。"})
            summary = self._call_api(messages)
            print(f"\n{summary}")
            md_lines.append(f"### AI（总结）\n\n{summary}\n\n")

        # 保存记录（时间戳命名，防止覆盖）
        full_md = "".join(md_lines)
        OUTPUT_DIR.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = OUTPUT_DIR / f"interview_session_{ts}.md"
        output_file.write_text(full_md, encoding="utf-8")
        print(f"\n[对话记录已保存至 {output_file}]")

        return full_md

    def _call_api(self, messages: list[dict[str, str]]) -> str:
        """调用 DeepSeek API，返回 AI 回复文本"""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1500,
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=90)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    @staticmethod
    def _timestamp() -> str:
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ── 高仿真模拟 ──

    def full_simulation(self, topic: str) -> str:
        """
        高仿真结构化面试："10分钟3题"模式。
        自动读秒计算每题思考时间和回答时间，
        结束后给出时间分析报告，标注超时题目。

        参数:
            topic: 面试主题

        返回:
            全场记录 Markdown 文本
        """
        print()
        print("=" * 60)
        print(f"  高仿真结构化面试 - 10分钟3题")
        print(f"  主题：{topic}")
        print(f"  每题思考上限：{THINKING_TIME_LIMIT}秒")
        print(f"  总时间上限：{TOTAL_TIME_LIMIT // 60}分钟")
        print("=" * 60)
        print()
        print("提示：看到题目后请思考，准备好后按 Enter 开始回答。")
        print()

        # 记录每题的计时数据
        timing_data: list[dict[str, Any]] = []
        session_start = time.time()
        total_elapsed = 0.0

        messages: list[dict[str, str]] = [
            {"role": "system", "content": SIMULATION_SYSTEM_PROMPT},
        ]

        md_lines: list[str] = [
            "# 高仿真面试记录\n",
            f"- **主题**：{topic}",
            f"- **模式**：10分钟3题 结构化面试",
            f"- **时间**：{self._timestamp()}\n",
            "---\n",
        ]

        # 启动
        init_msg = (
            f"面试主题：{topic}\n"
            f"面试轮次：3题，题型依次为综合分析→组织管理→人际应急/情景模拟\n"
            "请给出第一道面试题（综合分析类）。"
        )
        messages.append({"role": "user", "content": init_msg})

        # 初始化为空串：首轮即因总时间耗尽 break 时不会赋值
        ai_response = ""
        for round_num in range(1, QUESTION_COUNT + 1):
            # 检查总时间
            total_elapsed = time.time() - session_start
            remaining = TOTAL_TIME_LIMIT - total_elapsed
            if remaining <= 0:
                print("\n[时间已用完！面试提前结束]")
                break

            print(f"\n[剩余时间: {self._format_time(remaining)}]")

            # 获取 AI 题目/反馈
            ai_response = self._call_api(messages)
            messages.append({"role": "assistant", "content": ai_response})

            print(f"\n{'─' * 50}")
            print(ai_response)
            print(f"{'─' * 50}")

            md_lines.append(f"### AI（第 {round_num} 题）\n\n{ai_response}\n\n")

            # 若 AI 返回的是总结（说明面试提前结束）
            if "【面试总结】" in ai_response:
                break

            # ── 计时：思考阶段 ──
            think_start = time.time()
            input("\n[按 Enter 开始回答，计时开始...]")
            think_end = time.time()
            think_time = think_end - think_start

            # ── 计时：回答阶段 ──
            answer_start = time.time()
            print("[计时中... 请输入你的回答]")
            temp_answer_path = get_multiline_input("你的回答")
            answer_end = time.time()
            answer_time = answer_end - answer_start

            try:
                user_answer = Path(temp_answer_path).read_text(encoding="utf-8").strip()
            finally:
                cleanup_temp_file(temp_answer_path)

            round_total = think_time + answer_time
            total_elapsed = answer_end - session_start

            # 记录计时数据
            timing_data.append({
                "round": round_num,
                "think_time": think_time,
                "answer_time": answer_time,
                "round_total": round_total,
                "elapsed": total_elapsed,
                "think_overtime": think_time > THINKING_TIME_LIMIT,
            })

            # 本轮计时反馈
            flag = " [超时!]" if think_time > THINKING_TIME_LIMIT else ""
            print(f"\n[第{round_num}题计时: 思考 {think_time:.0f}秒 | 回答 {answer_time:.0f}秒 | 累计 {self._format_time(total_elapsed)}{flag}]")

            messages.append({
                "role": "user",
                "content": f"第{round_num}题我的回答：\n{user_answer}",
            })
            md_lines.append(f"### 考生（第 {round_num} 题回答）\n\n{user_answer}\n\n")

        # 请求总结
        if "【面试总结】" not in ai_response:
            messages.append({"role": "user", "content": "面试结束，请输出【面试总结】。"})
            summary = self._call_api(messages)
            print(f"\n{summary}")
            md_lines.append(f"### AI（总结）\n\n{summary}\n\n")
        else:
            summary = ai_response

        # ── 时间分析报告 ──
        time_report = self._build_time_report(timing_data, session_start)
        print(time_report)
        md_lines.append(f"## 时间分析报告\n\n{time_report}\n")

        # 保存（时间戳命名）
        full_md = "".join(md_lines)
        OUTPUT_DIR.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = OUTPUT_DIR / f"interview_{ts}.md"
        output_file.write_text(full_md, encoding="utf-8")
        print(f"\n[对话记录已保存至 {output_file}]")

        return full_md

    # ── 计时工具方法 ──

    @staticmethod
    def _format_time(seconds: float) -> str:
        """格式化秒数为 mm:ss"""
        m, s = divmod(int(seconds), 60)
        return f"{m}:{s:02d}"

    @staticmethod
    def _build_time_report(
        timing_data: list[dict[str, Any]],
        session_start: float,
    ) -> str:
        """构建时间分析报告"""
        total_elapsed = time.time() - session_start
        lines = [
            "",
            "### 时间分析报告",
            "",
            f"| 题号 | 思考用时 | 作答用时 | 合计 | 是否超时 |",
            f"|------|---------|---------|------|---------|",
        ]

        overtime_rounds: list[int] = []
        total_think = 0.0
        total_answer = 0.0

        for t in timing_data:
            r = t["round"]
            think = t["think_time"]
            ans = t["answer_time"]
            ot = "超时" if t["think_overtime"] else "正常"
            if t["think_overtime"]:
                overtime_rounds.append(r)

            lines.append(
                f"| 第{r}题 | {think:.0f}秒 | {ans:.0f}秒 | "
                f"{t['round_total']:.0f}秒 | {ot} |"
            )
            total_think += think
            total_answer += ans

        lines.append("")
        lines.append(f"- **总用时**：{InterviewTrainer._format_time(total_elapsed)}"
                      f"（上限 {TOTAL_TIME_LIMIT // 60} 分钟）")
        lines.append(f"- **思考总耗时**：{total_think:.0f}秒")
        lines.append(f"- **回答总耗时**：{total_answer:.0f}秒")

        if overtime_rounds:
            rounds_str = "、".join(f"第{r}题" for r in overtime_rounds)
            lines.append(f"- **超时题目**：{rounds_str}"
                          f"（每题思考上限 {THINKING_TIME_LIMIT} 秒）")
            lines.append(f"- **建议**：平时练习时控制每题思考在 {THINKING_TIME_LIMIT} 秒内，"
                          "实际考场中思考时间过长会给考官留下犹豫不决的印象。")
        else:
            lines.append("- 所有题目思考时间均在合理范围内")

        if total_elapsed > TOTAL_TIME_LIMIT:
            lines.append(f"- **总时间超限**：超出 {InterviewTrainer._format_time(total_elapsed - TOTAL_TIME_LIMIT)}")
        else:
            remaining = TOTAL_TIME_LIMIT - total_elapsed
            lines.append(f"- 总时间充裕，剩余 {InterviewTrainer._format_time(remaining)}")

        return "\n".join(lines)


# ── 向后兼容 ──
def simulate_interview(topic: str, rounds: int = 3) -> list[dict[str, Any]]:
    """模拟面试对话（向后兼容旧接口，返回对话记录列表）"""
    trainer = InterviewTrainer(max_rounds=rounds)
    md = trainer.start_session(topic, mode="结构化")
    return [{"session_markdown": md}]
