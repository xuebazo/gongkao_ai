"""
API 连通性测试脚本
调用 DeepSeek API 验证配置是否正确，打印返回内容。
"""
import json
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import config

import requests


def test_api() -> None:
    """发送一条测试消息，验证 API 连通性"""
    url = f"{config.DEEPSEEK_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config.DEEPSEEK_MODEL,
        "messages": [
            {
                "role": "user",
                "content": "你好，请用一句话介绍公考申论的评分标准。",
            }
        ],
    }

    print(f"[测试] 正在连接 DeepSeek API...")
    print(f"[测试] URL: {url}")
    print(f"[测试] Model: {config.DEEPSEEK_MODEL}")
    print()

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        print("=" * 60)
        print("[OK] API connectivity test passed!")
        print("=" * 60)
        print()
        print(f"[Reply] {content}")
        print()
        print(f"[Usage] prompt_tokens={usage.get('prompt_tokens')}, "
              f"completion_tokens={usage.get('completion_tokens')}, "
              f"total_tokens={usage.get('total_tokens')}")

    except requests.exceptions.HTTPError as e:
        print(f"[FAIL] HTTP error: {e}")
        if resp.text:
            print(f"       Response: {resp.text}")
        sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("[FAIL] Connection failed: unable to reach DeepSeek API")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("[FAIL] Request timed out")
        sys.exit(1)
    except Exception as e:
        print(f"[FAIL] Unknown error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    test_api()
