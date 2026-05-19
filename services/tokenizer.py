import re
import uuid
import jieba

_PUNCTUATION_RE = re.compile(
    r"^[\u3000-\u303F\uFF00-\uFFEF\u2000-\u206F"
    r".,!?;:\'\"()\[\]{{}}<>…—～\-—/@#$%^&*+=|~`]+$"
)

_NUMBER_RE = re.compile(r"^\d+([.,]\d+)?[%‰]?$")

_CONNECTORS: frozenset[str] = frozenset({
    "的", "了", "在", "是", "有", "和", "与", "或", "而", "但", "却",
    "因为", "所以", "如果", "虽然", "但是", "而且", "并且",
    "然后", "接着", "于是", "因此", "因而", "从而",
    "以便", "以免", "除非", "否则",
    "不管", "无论", "尽管", "即使", "既然",
    "不仅", "不但", "只要", "只有",
    "才", "就", "也", "都", "还", "又", "再", "更", "最", "很", "太",
    "非常", "比较", "特别", "尤其", "大概", "大约",
    "可能", "也许", "或许", "一定", "必须", "应该",
    "可以", "能够", "会", "要", "想", "愿意",
    "把", "被", "让", "给", "对", "于",
    "按", "按照", "依照", "根据", "通过", "经过", "关于", "至于",
    "着", "过", "得", "地", "之", "所", "以", "为",
    "上", "下", "中", "里", "外", "前", "后", "内", "旁",
    "从", "由", "向", "往", "朝", "到",
    "这", "那", "哪", "某", "每", "各", "本", "该", "其",
    "且", "则", "虽", "并", "及", "同", "跟",
    "啊", "吧", "吗", "呢", "哦", "嗯", "呀", "嘛", "哇",
    "便", "即", "可", "能", "该", "既",
})


def _classify_token(word: str) -> str:
    if _PUNCTUATION_RE.match(word):
        return "punctuation"
    if _NUMBER_RE.match(word):
        return "number"
    if word in _CONNECTORS:
        return "connector"
    return "default"


def tokenize_text(text: str) -> list[dict]:
    results = jieba.tokenize(text)
    return [
        {
            "id": str(uuid.uuid4()),
            "start_offset": start,
            "text": word,
            "style_type": _classify_token(word),
        }
        for word, start, end in results
    ]


def tokenize_and_merge(text: str) -> list[dict]:
    raw = tokenize_text(text)
    groups: dict[str, dict] = {}
    order: list[str] = []

    for t in raw:
        key = t["text"]
        if key not in groups:
            groups[key] = {
                "id": str(uuid.uuid4()),
                "start_offsets": [],
                "text": key,
                "style_type": _classify_token(key),
            }
            order.append(key)
        groups[key]["start_offsets"].append(t["start_offset"])

    return [groups[k] for k in order]


def tokenize_with_vocabulary(text: str, doc_tokens: list[dict]) -> tuple[list[dict], list[dict]]:
    vocab: dict[str, dict] = {}
    for t in doc_tokens:
        if t["text"] not in vocab:
            vocab[t["text"]] = t
    vocab_entries = sorted(vocab.values(), key=lambda t: -len(t["text"]))

    result: list[dict] = []
    result_by_id: dict[str, dict] = {}
    order: list[str] = []

    new_tokens: list[dict] = []

    i = 0
    while i < len(text):
        matched = None
        for entry in vocab_entries:
            if text.startswith(entry["text"], i):
                matched = entry
                break

        if matched:
            tid = matched["id"]
            if tid not in result_by_id:
                token_entry = {
                    "id": tid,
                    "start_offsets": [],
                    "text": matched["text"],
                    "style_type": matched["style_type"],
                }
                result_by_id[tid] = token_entry
                order.append(tid)
            result_by_id[tid]["start_offsets"].append(i)
            i += len(matched["text"])
        else:
            unmatched_start = i
            unmatched_chars = text[i]
            i += 1
            while i < len(text):
                found = False
                for entry in vocab_entries:
                    if text.startswith(entry["text"], i):
                        found = True
                        break
                if found:
                    break
                unmatched_chars += text[i]
                i += 1

            jieba_tokens = tokenize_text(unmatched_chars)
            base_offset = unmatched_start
            for jt in jieba_tokens:
                jt_text = jt["text"]
                jt_off = base_offset + jt["start_offset"]

                existing_in_vocab = vocab.get(jt_text)
                if existing_in_vocab:
                    tid = existing_in_vocab["id"]
                    if tid not in result_by_id:
                        token_entry = {
                            "id": tid,
                            "start_offsets": [],
                            "text": existing_in_vocab["text"],
                            "style_type": existing_in_vocab["style_type"],
                        }
                        result_by_id[tid] = token_entry
                        order.append(tid)
                    result_by_id[tid]["start_offsets"].append(jt_off)
                else:
                    new_id = str(uuid.uuid4())
                    new_token = {
                        "id": new_id,
                        "start_offsets": [jt_off],
                        "text": jt_text,
                        "style_type": _classify_token(jt_text),
                    }
                    if new_id not in result_by_id:
                        result_by_id[new_id] = new_token
                        order.append(new_id)
                    else:
                        result_by_id[new_id]["start_offsets"].append(jt_off)
                    new_tokens.append({
                        "id": new_id,
                        "start_offsets": [],
                        "text": jt_text,
                        "style_type": _classify_token(jt_text),
                    })

    merged_result = [result_by_id[k] for k in order]
    return merged_result, new_tokens
