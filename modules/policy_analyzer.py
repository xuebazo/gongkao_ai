"""
政策文件智能解析模块 - PolicyAnalyzer

通过 DeepSeek API，支持两种分析模式：
  - quick（默认）：四维度分析（核心信号 / 金句 / 出题角度 / 面试素材）
  - deep：六维度分析（额外增加"常见解读误区"+"联系其他政策的交叉点"）

用法:
    from config import config
    from modules.policy_analyzer import PolicyAnalyzer

    analyzer = PolicyAnalyzer(api_key=config.DEEPSEEK_API_KEY)
    result = analyzer.analyze_policy("政策文本内容...")              # quick 模式
    result = analyzer.analyze_policy("政策文本内容...", "deep")     # deep 模式
"""
import json
import re
import sys
from pathlib import Path
from typing import Any

import requests

# 确保能从项目根目录导入 config（兼容直接运行和被 main.py 导入两种场景）
try:
    from config import config
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from config import config  # type: ignore[no-redef]


# ── 系统提示词 ──

# Quick 模式（四维度，默认，节省 Token）
QUICK_SYSTEM_PROMPT = """你是一位资深公考政策研究员，擅长从政策文件中提取备考要点。

你的任务：对用户提供的政策文本，从以下四个维度进行分析——

① 一句话核心信号：用一句话概括该政策最核心的导向或信号（25字以内）。

② 申论大作文可引用的金句：从文本中提取 2~3 句可直接用于申论大作文的金句。
   - 金句必须从原文中摘录或高度忠于原文精神
   - 每条金句必须标注"paragraph_ref"：指明该金句出自原文哪个段落（如"第一段""二-(一)"等位置标识），并简要摘录所在段落的原文关键句作为出处依据
   - "source"字段：说明该金句适合用于申论的哪种场景（如"可用于论述政务服务改革的引言""适合作为数字化转型段落的论据"）

③ 可能的申论出题角度：列举 2~3 个该政策可能引出的申论命题角度。
   - 每个角度除"angle"（角度名称）和"description"（角度描述）外，须增加"material_organization"字段
   - "material_organization"应给出具体的材料组织建议，例如：
     * 建议从哪些段落提取论据
     * 可采用什么论证结构（如"是什么-为什么-怎么办""问题-原因-对策"等）
     * 可结合哪些社会现象或热点展开论述

④ 面试可用的观点素材：提炼 1~2 个可用于结构化面试回答的观点素材，包含"viewpoint"（核心观点）和"argument"（论证要点）。

【输出要求】
你必须严格按照以下 JSON 结构返回，并将 JSON 包裹在 markdown 代码块中（```json ... ```），不得包含任何其他文字：

```json
{
  "core_signal": "一句话核心信号",
  "golden_quotes": [
    {
      "quote": "金句正文（须来自原文或忠于原文）",
      "paragraph_ref": "原文出处段落位置及关键句摘录",
      "source": "申论适用场景说明"
    }
  ],
  "exam_angles": [
    {
      "angle": "出题角度名称",
      "description": "角度简要说明",
      "material_organization": "具体的材料组织建议（含段落引用、论证结构、可结合现象）"
    }
  ],
  "interview_material": [
    {
      "viewpoint": "核心观点",
      "argument": "论证要点（分点列出）"
    }
  ]
}
```"""


# Deep 模式（六维度，进阶分析）
DEEP_SYSTEM_PROMPT = """你是一位资深公考政策研究员，擅长从政策文件中深度提取备考要点。

你的任务：对用户提供的政策文本，从以下六个维度进行深度分析——

① 一句话核心信号：用一句话概括该政策最核心的导向或信号（25字以内）。

② 申论大作文可引用的金句：从文本中提取 2~3 句可直接用于申论大作文的金句。
   - 金句必须从原文中摘录或高度忠于原文精神
   - 每条金句必须标注"paragraph_ref"：指明该金句出自原文哪个段落（如"第一段""二-(一)"等位置标识），并简要摘录所在段落的原文关键句作为出处依据
   - "source"字段：说明该金句适合用于申论的哪种场景

③ 可能的申论出题角度：列举 2~3 个该政策可能引出的申论命题角度。
   - 每个角度除"angle"和"description"外，须增加"material_organization"字段
   - "material_organization"应给出具体的材料组织建议（段落引用、论证结构、可结合现象）

④ 面试可用的观点素材：提炼 1~2 个可用于结构化面试回答的观点素材，包含"viewpoint"和"argument"。

⑤ 常见解读误区：指出 1~2 个考生在解读该政策时容易出现的理解偏差或片面认识。
   - "misunderstanding"：描述常见的错误理解
   - "correction"：给出正确的解读方式，说明为什么那种理解是片面的

⑥ 联系其他政策的交叉点：分析该政策与 1~2 个其他重要政策的关联与交叉。
   - "related_policy"：相关政策的名称或文号
   - "intersection"：说明两个政策之间的逻辑关联、互补关系或协同效应，以及这种关联对申论答题的启示

【输出要求】
你必须严格按照以下 JSON 结构返回，并将 JSON 包裹在 markdown 代码块中（```json ... ```），不得包含任何其他文字：

```json
{
  "core_signal": "一句话核心信号",
  "golden_quotes": [
    {
      "quote": "金句正文",
      "paragraph_ref": "原文出处段落位置及关键句摘录",
      "source": "申论适用场景说明"
    }
  ],
  "exam_angles": [
    {
      "angle": "出题角度名称",
      "description": "角度简要说明",
      "material_organization": "材料组织建议"
    }
  ],
  "interview_material": [
    {
      "viewpoint": "核心观点",
      "argument": "论证要点"
    }
  ],
  "common_misunderstandings": [
    {
      "misunderstanding": "常见错误解读",
      "correction": "正确解读方式"
    }
  ],
  "policy_cross_references": [
    {
      "related_policy": "相关政策名称",
      "intersection": "交叉点分析及申论答题启示"
    }
  ]
}
```"""


# 模式 → 提示词映射
_PROMPT_MAP: dict[str, str] = {
    "quick": QUICK_SYSTEM_PROMPT,
    "deep": DEEP_SYSTEM_PROMPT,
}


class PolicyAnalyzer:
    """政策文件智能解析器"""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        """
        初始化解析器。

        参数:
            api_key: DeepSeek API Key，默认从 config 读取
            base_url: API 基础地址，默认从 config 读取
            model: 模型名称，默认从 config 读取
        """
        self.api_key = api_key or config.DEEPSEEK_API_KEY
        self.base_url = (base_url or config.DEEPSEEK_BASE_URL).rstrip("/")
        self.model = model or config.DEEPSEEK_MODEL

        if not self.api_key:
            raise ValueError("API Key 未配置，请设置 DEEPSEEK_API_KEY")

    def analyze_policy(self, text: str, analysis_type: str = "quick") -> dict[str, Any]:
        """
        分析政策文本，返回结构化结果。

        参数:
            text: 政策文件文本内容
            analysis_type: 分析模式
                - "quick"（默认）：四维度（核心信号/金句/出题角度/面试素材）
                - "deep"：六维度（额外增加"常见解读误区"+"政策交叉点"）

        返回:
            dict: 四或六维度结构化结果，若 API 返回无法解析为 JSON 则返回 {"raw_response": "..."}
        """
        if not text or not text.strip():
            return {"error": "输入文本为空，请提供有效的政策文本"}

        # 验证模式
        if analysis_type not in _PROMPT_MAP:
            supported = ", ".join(_PROMPT_MAP.keys())
            return {"error": f"不支持的分析模式: {analysis_type}，可选: {supported}"}

        system_prompt = _PROMPT_MAP[analysis_type]

        # 截断过长文本（保留前 8000 字符，避免超 token 限制）
        max_chars = 8000
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[文本过长已截断，以上为前 {} 字符]".format(max_chars)

        try:
            content = self._call_api(text, system_prompt)
            return self._parse_response(content)
        except requests.exceptions.Timeout:
            return {"error": "API 请求超时，请稍后重试"}
        except requests.exceptions.ConnectionError:
            return {"error": "无法连接到 DeepSeek API，请检查网络"}
        except requests.exceptions.HTTPError as e:
            return {"error": f"API 返回错误: {e}"}
        except Exception as e:
            return {"error": f"解析过程发生异常: {e}"}

    # ── 私有方法 ──

    def _call_api(self, text: str, system_prompt: str) -> str:
        """调用 DeepSeek Chat API，返回模型回复文本"""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            "temperature": 0.3,  # 降低随机性，保证输出结构稳定
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    @staticmethod
    def _parse_response(content: str) -> dict[str, Any]:
        """
        解析 API 返回内容为 JSON。
        若无法解析为合法 JSON，返回原始文本。
        """
        # 尝试 1：直接解析
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # 尝试 2：从 markdown 代码块中提取 JSON
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试 3：匹配首尾花括号
        brace_match = re.search(r"\{[\s\S]*\}", content)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        # 兜底：返回原始文本
        return {"raw_response": content}


# ── 向后兼容的函数接口 ──

def parse_policy(file_path: str, analysis_type: str = "quick") -> dict[str, Any]:
    """
    解析政策文件（文件路径），返回结构化信息。
    向后兼容旧接口。

    参数:
        file_path: 政策文件路径
        analysis_type: 分析模式 "quick" 或 "deep"
    """
    analyzer = PolicyAnalyzer()
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        return {"error": f"文件未找到: {file_path}"}
    except Exception as e:
        return {"error": f"读取文件失败: {e}"}

    return analyzer.analyze_policy(text, analysis_type)
