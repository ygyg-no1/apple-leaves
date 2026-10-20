"""调用 DeepSeek 开放接口，根据检测结果生成中文防治建议（不存储密钥）。"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

DEEPSEEK_CHAT_URL = "https://api.deepseek.com/v1/chat/completions"
DEFAULT_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")


def resolve_api_key(explicit: str | None) -> str:
    key = (explicit or "").strip()
    if key:
        return key
    return (os.environ.get("DEEPSEEK_API_KEY") or "").strip()


def _build_prompt(stats_text: str, source_hint: str) -> str:
    return (
        "你是果树植保助手，回答须科学、审慎，不能替代现场农技人员或植物病理实验室诊断。\n\n"
        "用户用目标检测模型对苹果叶片做了病害相关框统计，结果如下：\n"
        f"{stats_text}\n\n"
        f"数据来源说明：{source_hint}\n\n"
        "【排版要求（必须遵守）】\n"
        "· 使用纯中文正文，不要使用 Markdown：不要用「#」「##」等标题符号；不要用以「-」「*」开头的无序列表。\n"
        "· 大段内容请用「一、」「二、」「三、」分段；段内如需并列，请用「（1）（2）（3）」或「1．2．3．」编号，每项单独一行。\n"
        "· 段与段之间空一行；不要使用「---」等分隔线。\n\n"
        "【内容要求】\n"
        "一、对上述统计结果的简要解读（若某类为 0 可说明未检出框）。\n"
        "二、果园或家庭盆栽场景下的综合管理建议（清园、水肥、修剪、通风等）。\n"
        "三、若涉及用药：须强调遵守当地法规与农药标签，由农技部门指导，不要编造具体商品名与剂量。\n"
        "全文控制在 900 字以内，用语简洁。"
    )


def format_advice_text(text: str) -> str:
    """去掉常见 Markdown 符号（#、行首 - / *），整理为易读的纯文本。"""
    if not text:
        return ""
    raw = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = raw.split("\n")
    cleaned: list[str] = []
    for line in lines:
        s = line.rstrip()
        # 去掉行首 # 标题
        s = re.sub(r"^#{1,6}\s*", "", s)
        # 去掉 Markdown 粗体星号（保留中间文字）
        s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)
        s = re.sub(r"\*([^*]+)\*", r"\1", s)
        # 无序列表符 -> 中文间隔号，避免行首「-」
        if re.match(r"^[\-\*]\s+", s):
            s = re.sub(r"^[\-\*]\s+", "· ", s, count=1)
        # 分隔线
        if re.fullmatch(r"[\-\*_`=＝]{3,}", s.strip() or ""):
            s = ""
        cleaned.append(s)
    # 连续空行压成最多一个空行
    out: list[str] = []
    prev_blank = False
    for s in cleaned:
        blank = s.strip() == ""
        if blank:
            if not prev_blank:
                out.append("")
            prev_blank = True
        else:
            out.append(s.rstrip())
            prev_blank = False
    return "\n".join(out).strip()


def fetch_treatment_advice(api_key: str, stats_text: str, source_hint: str, timeout: float = 120.0) -> str:
    key = (api_key or "").strip()
    if not key:
        raise ValueError("请填写 DeepSeek API Key，或在系统中设置环境变量 DEEPSEEK_API_KEY。")

    payload = {
        "model": DEFAULT_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你协助用户理解苹果叶病害检测统计并给出一般性农艺管理参考。"
                    "回答一律为纯中文排版：禁止 Markdown 标题（#）、禁止以半角减号或星号开头的列表行。"
                ),
            },
            {"role": "user", "content": _build_prompt(stats_text, source_hint)},
        ],
        "temperature": 0.55,
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        DEEPSEEK_CHAT_URL,
        data=data,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            body = str(e)
        raise RuntimeError(f"DeepSeek HTTP {e.code}: {body[:800]}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"网络错误：{e}") from e

    try:
        content = str(raw["choices"][0]["message"]["content"]).strip()
        return format_advice_text(content)
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError(f"接口返回格式异常：{json.dumps(raw, ensure_ascii=False)[:600]}") from e
