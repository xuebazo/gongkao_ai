"""
申论真题评阅模块 - ShenlunReviewer

AI 同时扮演阅卷组长与辅导老师，从"深度剖析评分"与"写作提升方案"两大块反馈。
支持四种题型微调评分标准：
  - 概括归纳：侧重要点完整性与信息准确度
  - 综合分析：侧重逻辑深度与多角度分析
  - 贯彻执行：侧重格式规范与措施可行性
  - 申发论述：侧重论证结构与论点清晰度

用法:
    from config import config
    from modules.shenlun_reviewer import ShenlunReviewer

    reviewer = ShenlunReviewer()
    feedback = reviewer.evaluate_essay("题目", "文章", question_type="申发论述")
"""
import sys
from pathlib import Path
from typing import Any

import requests

try:
    from config import config
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from config import config  # type: ignore[no-redef]


# ── 题型专属评分侧重 ──

# 各题型的名称映射与评分维度权重说明
QUESTION_TYPE_CONFIG: dict[str, dict[str, Any]] = {
    "概括归纳": {
        "label": "概括归纳题",
        "focus": (
            "本题为概括归纳题，评阅时请重点关注：\n"
            "- **要点完整性**（权重最高）：是否全面、无遗漏地提取了材料中的关键信息\n"
            "- **信息准确度**：归纳的内容是否忠于原文，有无主观添加或曲解\n"
            "- **语言简洁性**：是否用精炼的语言概括，避免冗长啰嗦\n"
            "- **条理清晰度**：分点是否合理，逻辑是否顺畅"
        ),
        "dimensions": "| 要点完整性 | X | 30 | ... | ... |\n| 信息准确度 | X | 25 | ... | ... |\n| 条理清晰度 | X | 20 | ... | ... |\n| 语言简洁性 | X | 15 | ... | ... |\n| 格式规范性 | X | 10 | ... | ... |",
    },
    "综合分析": {
        "label": "综合分析题",
        "focus": (
            "本题为综合分析题，评阅时请重点关注：\n"
            "- **逻辑深度**（权重最高）：是否深入剖析了问题的原因、影响、本质\n"
            "- **多角度分析**：是否从不同维度（如经济、社会、制度等）展开论述\n"
            "- **辩证思维**：是否能一分为二地看待问题，避免片面化\n"
            "- **对策针对性**：提出的观点或建议是否切中要害"
        ),
        "dimensions": "| 逻辑深度 | X | 30 | ... | ... |\n| 多角度分析 | X | 25 | ... | ... |\n| 观点立意 | X | 20 | ... | ... |\n| 语言表达 | X | 15 | ... | ... |\n| 结构层次 | X | 10 | ... | ... |",
    },
    "贯彻执行": {
        "label": "贯彻执行题",
        "focus": (
            "本题为贯彻执行题（公文/应用文写作），评阅时请重点关注：\n"
            "- **格式规范性**（权重最高）：是否遵循了该文种的标准格式（标题、称谓、正文、落款等）\n"
            "- **角色定位**：是否准确把握了发文机关的身份和行文语气\n"
            "- **措施可行性**：提出的方案是否具体、可操作，而非空洞口号\n"
            "- **语言得体性**：用语是否符合公文风格，有无口语化或随意表达"
        ),
        "dimensions": "| 格式规范性 | X | 25 | ... | ... |\n| 措施可行性 | X | 25 | ... | ... |\n| 角色定位 | X | 20 | ... | ... |\n| 语言得体性 | X | 15 | ... | ... |\n| 内容完整性 | X | 15 | ... | ... |",
    },
    "申发论述": {
        "label": "申发论述题（大作文）",
        "focus": (
            "本题为申发论述题（大作文），评阅时请重点关注：\n"
            "- **论证结构**（权重最高）：是否有清晰的总分总结构，分论点是否支撑中心论点\n"
            "- **论点清晰度**：中心论点是否鲜明，各分论点是否逻辑递进\n"
            "- **论据丰富性**：是否引用政策、数据、案例等多元论据支撑观点\n"
            "- **语言文采**：表达是否生动有力，有无亮点句式"
        ),
        "dimensions": "| 观点立意 | X | 25 | ... | ... |\n| 论证逻辑 | X | 25 | ... | ... |\n| 结构层次 | X | 20 | ... | ... |\n| 语言表达 | X | 15 | ... | ... |\n| 政策素养 | X | 15 | ... | ... |",
    },
}

# 默认（未指定或无效题型时使用）
DEFAULT_FOCUS = "请按通用申论评分标准评阅，全面考察观点、论证、结构、语言和政策素养。"


# ── 系统提示词模板 ──
SYSTEM_PROMPT_TEMPLATE = """你同时扮演两个角色：
1. **申论阅卷组长**：严格按官方评分标准打分，客观指出得分点与扣分点
2. **资深辅导老师**：针对考生失分原因，制定可操作的提升方案

【题型说明】
{question_type_label}

【评分侧重】
{scoring_focus}

请根据用户提供的【真题题目】和【考生文章】，按以下格式输出反馈（总字数控制在 800 字左右，Markdown 格式）：

---

## 一、深度剖析评分

**预估分数**：XX分 / 100分 | **等级**：一类/二类/三类/四类文 | **题型**：{question_type_label}

**总体评价**：（围绕本题型的核心评分标准，用一句话概括文章优缺点）

### 分项得分明细

{dimensions}

### 逐段点评
对文章的每个自然段给出 1-2 句点评，指出该段的亮点或问题。

---

## 二、写作提升方案

### 阶段目标
- **近期（1 周内）**：（针对本题型最紧迫的 1 个改进点）
- **中期（1 个月内）**：（针对本题型需要持续练习的 1 个能力）

### 专项训练
1. **（训练项目名称）**：具体训练方法（1-2 句话，须与本题型直接相关）
2. **（训练项目名称）**：具体训练方法（1-2 句话，须与本题型直接相关）

### 常见写作误区纠正（针对本题型）
- **误区**：（考生在本题型中暴露的典型问题）
  **纠正**：（如何针对性改进）

---

【重要】只返回上述 Markdown 格式的反馈内容，不包含其他文字。总字数严格控制在 800 字左右。"""


# ── 题型参数校验 ──
VALID_QUESTION_TYPES = frozenset(QUESTION_TYPE_CONFIG.keys())


class ShenlunReviewer:
    """申论真题评阅器"""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.api_key = api_key or config.DEEPSEEK_API_KEY
        self.base_url = (base_url or config.DEEPSEEK_BASE_URL).rstrip("/")

        if not self.api_key:
            raise ValueError("API Key 未配置，请设置 DEEPSEEK_API_KEY")

    def evaluate_essay(
        self,
        question: str,
        essay_text: str,
        question_type: str = "申发论述",
        use_pro: bool = False,
    ) -> dict[str, Any]:
        """
        评阅申论文章（支持题型适配）。

        参数:
            question: 申论真题题目
            essay_text: 考生文章内容
            question_type: 题型，可选 "概括归纳" / "综合分析" / "贯彻执行" / "申发论述"
            use_pro: 是否启用 Pro 深度评阅（显式参数；不再依赖题目里的 "Pro模式" 前缀）

        返回:
            dict: {"feedback": "Markdown 评阅报告"} 或 {"error": "错误信息"}
        """
        if not question or not question.strip():
            return {"error": "题目为空，请提供申论真题题目"}
        if not essay_text or not essay_text.strip():
            return {"error": "文章为空，请提供考生文章内容"}

        # 校验题型
        if question_type not in VALID_QUESTION_TYPES:
            supported = " / ".join(sorted(VALID_QUESTION_TYPES))
            return {"error": f"不支持的题型: {question_type}，可选: {supported}"}

        # 获取题型配置
        type_config = QUESTION_TYPE_CONFIG[question_type]

        # 模型选择：显式 use_pro 参数。
        # 兼容历史调用方：题目里若仍带 "Pro模式" 前缀，自动识别并从题干中剔除。
        legacy_prefix = "Pro模式" in question
        if legacy_prefix:
            question = question.replace("Pro模式", "").strip()
        pro = use_pro or legacy_prefix
        model = getattr(config, "DEEPSEEK_MODEL", "deepseek-chat")
        if pro:
            model = getattr(config, "DEEPSEEK_PRO_MODEL", "deepseek-reasoner")
        question_clean = question

        # 构建题型专属系统提示词
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            question_type_label=type_config["label"],
            scoring_focus=type_config["focus"],
            dimensions=type_config["dimensions"],
        )

        # 构建用户消息
        user_content = f"【真题题目】\n{question_clean}\n\n【考生文章】\n{essay_text}"

        # 截断文章（避免超 token 限制）
        max_essay_chars = 4000
        truncated = False
        if len(essay_text) > max_essay_chars:
            essay_text = essay_text[:max_essay_chars] + "\n\n[文章过长已截断]"
            user_content = f"【真题题目】\n{question_clean}\n\n【考生文章】\n{essay_text}"
            truncated = True
        else:
            user_content = f"【真题题目】\n{question_clean}\n\n【考生文章】\n{essay_text}"

        try:
            feedback = self._call_api(user_content, model, system_prompt)
            result: dict[str, Any] = {"feedback": feedback}
            if truncated:
                result["truncated"] = True
            return result
        except requests.exceptions.Timeout:
            return {"error": "API 请求超时，请稍后重试"}
        except requests.exceptions.ConnectionError:
            return {"error": "无法连接到 DeepSeek API，请检查网络"}
        except requests.exceptions.HTTPError as e:
            return {"error": f"API 返回错误: {e}"}
        except Exception as e:
            return {"error": f"评阅过程异常: {e}"}

    def _call_api(self, user_content: str, model: str, system_prompt: str) -> str:
        """调用 DeepSeek API，返回评阅文本"""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.5,
            "max_tokens": 2000,
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=90)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


# ── 向后兼容的函数接口 ──
def review_essay(
    essay_text: str,
    topic: str = "",
    question_type: str = "申发论述",
) -> dict[str, Any]:
    """评阅申论文章（向后兼容旧接口）"""
    reviewer = ShenlunReviewer()
    return reviewer.evaluate_essay(topic, essay_text, question_type)
