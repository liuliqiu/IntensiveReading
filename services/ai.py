import json
import os
import re
from openai import AsyncOpenAI

_API_KEY = os.environ.get("OPENAI_API_KEY", "")
_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
_MODEL = os.environ.get("OPENAI_MODEL", "deepseek-chat")

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=_API_KEY, base_url=_BASE_URL)
    return _client

_SUMMARIZE_PROMPT = """你是一个专业的文本分析助手。请对以下中文文本进行总结，并在总结中标出关键术语与原文本的对应关系。

要求：
1. 用简洁的中文总结原文的核心内容（300-500字）。
2. 对于总结中使用到的关键术语，标注它在原文中对应的表述（可能有多种表述）。

请严格按照以下JSON格式输出，不要输出其他内容：
{
  "summary": "总结文本...",
  "term_mapping": [
    {"summary_term": "Transformer架构", "original_terms": ["Transformer", "Transformer架构", "该架构"]},
    {"summary_term": "注意力机制", "original_terms": ["注意力机制", "Attention机制"]}
  ]
}

原文：
"""


_CONCEPTS_PROMPT = """你是一个专业的文本分析助手。请分析以下摘要文本中的关键概念及其之间的关系。

要求：
1. 提取文本中提到的所有关键概念（专业术语、核心主题等）。每个概念的 "text" 字段必须是文本中出现的精确原文片段。
2. 分析这些概念之间的语义关系。
3. 关系类型使用以下之一：causal(因果), contains(包含), contrasts(对比), complements(互补), precedes(递进), describes(描述)

请严格按照以下JSON格式输出，不要输出其他内容：
{
  "concepts": [
    {"text": "Transformer架构", "description": "一种基于注意力机制的深度学习架构"},
    {"text": "注意力机制", "description": "Transformer的核心组件，用于计算序列中不同位置的相关性"}
  ],
  "relationships": [
    {"type": "contains", "source": "Transformer架构", "target": "注意力机制", "description": "Transformer架构包含注意力机制作为其核心组件"}
  ]
}

摘要文本：
"""


_EXPLAIN_PROMPT = """你是一个专业的文本分析助手。请结合上下文解释以下术语在文中的含义。

术语：「{term}」

上下文：
{context}

请用简洁的中文解释这个术语在这段文字中的具体含义。只输出解释内容，不要加前缀或格式。"""


def _clean_json_response(text: str) -> str:
    text = text.strip()
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        return m.group(0)
    return text


async def summarize_text(original_text: str, model: str | None = None) -> tuple[str, list[dict]]:
    m = model or _MODEL
    response = await _get_client().chat.completions.create(
        model=m,
        messages=[{"role": "user", "content": _SUMMARIZE_PROMPT + original_text}],
        temperature=0.3,
        max_tokens=4096,
    )
    content = response.choices[0].message.content or ""
    cleaned = _clean_json_response(content)
    data = json.loads(cleaned)
    summary = data.get("summary", "")
    term_mapping = data.get("term_mapping", [])
    return summary, term_mapping


async def analyze_concepts(text: str, model: str | None = None) -> tuple[list[dict], list[dict]]:
    m = model or _MODEL
    response = await _get_client().chat.completions.create(
        model=m,
        messages=[{"role": "user", "content": _CONCEPTS_PROMPT + text}],
        temperature=0.3,
        max_tokens=4096,
    )
    content = response.choices[0].message.content or ""
    cleaned = _clean_json_response(content)
    data = json.loads(cleaned)
    concepts = data.get("concepts", [])
    relationships = data.get("relationships", [])
    return concepts, relationships


async def explain_text(term: str, context: str, model: str | None = None) -> str:
    m = model or _MODEL
    prompt = _EXPLAIN_PROMPT.format(term=term, context=context)
    response = await _get_client().chat.completions.create(
        model=m,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=1024,
    )
    return (response.choices[0].message.content or "").strip()
