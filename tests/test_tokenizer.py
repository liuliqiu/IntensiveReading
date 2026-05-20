import uuid

from services.tokenizer import (
    _classify_token,
    _tokenize_with_added_words,
    tokenize_and_merge,
    tokenize_text,
    tokenize_with_concepts,
    tokenize_with_vocabulary,
)


# ── _classify_token ──────────────────────────────────────────────────────────

def test_classify_punctuation():
    assert _classify_token("。") == "punctuation"
    assert _classify_token("，") == "punctuation"
    assert _classify_token("！") == "punctuation"
    assert _classify_token(",") == "punctuation"
    assert _classify_token(".") == "punctuation"


def test_classify_number():
    assert _classify_token("123") == "number"
    assert _classify_token("3.14") == "number"
    assert _classify_token("50%") == "number"


def test_classify_connector():
    assert _classify_token("的") == "connector"
    assert _classify_token("了") == "connector"
    assert _classify_token("因为") == "connector"
    assert _classify_token("虽然") == "connector"


def test_classify_default():
    assert _classify_token("深度学习") == "default"
    assert _classify_token("transformer") == "default"


# ── tokenize_text ─────────────────────────────────────────────────────────────

def test_tokenize_text_basic():
    tokens = tokenize_text("人工智能是未来的方向")
    texts = [t["text"] for t in tokens]
    assert "人工智能" in texts
    assert "。" not in texts  # no punctuation in input


def test_tokenize_text_structure():
    tokens = tokenize_text("人工智能技术")
    assert len(tokens) > 0
    for t in tokens:
        assert set(t.keys()) == {"id", "start_offset", "text", "style_type"}
        assert isinstance(t["start_offset"], int)
        assert isinstance(t["text"], str)


def test_tokenize_text_offsets_contiguous():
    text = "人工智能技术发展迅速"
    tokens = tokenize_text(text)
    assert tokens[0]["start_offset"] == 0
    assert tokens[-1]["start_offset"] + len(tokens[-1]["text"]) == len(text)


def test_tokenize_text_unique_uuids():
    tokens = tokenize_text("科技的科技发展")
    ids = [t["id"] for t in tokens]
    assert len(set(ids)) == len(ids)


def test_tokenize_text_empty():
    tokens = tokenize_text("")
    assert tokens == []


# ── tokenize_and_merge ────────────────────────────────────────────────────────

def test_merge_duplicates():
    tokens = tokenize_and_merge("科技的科技")
    keji_entries = [t for t in tokens if t["text"] == "科技"]
    assert len(keji_entries) == 1
    assert len(keji_entries[0]["start_offsets"]) >= 2


def test_merge_distinct():
    tokens = tokenize_and_merge("人工智能技术")
    texts = {t["text"] for t in tokens}
    assert len(texts) == len(tokens)


def test_merge_structure():
    tokens = tokenize_and_merge("深度学习")
    for t in tokens:
        assert set(t.keys()) == {"id", "start_offsets", "text", "style_type"}
        assert isinstance(t["start_offsets"], list)


def test_merge_order_stable():
    text = "苹果很甜苹果也红"
    tokens = tokenize_and_merge(text)
    texts = [t["text"] for t in tokens]
    first_apple = texts.index("苹果")
    other_after_apple = texts[first_apple + 1:]
    assert "苹果" not in other_after_apple


# ── _tokenize_with_added_words ────────────────────────────────────────────────

def test_added_word_tokenized_as_unit():
    results = _tokenize_with_added_words("学习Transformer架构", {"Transformer架构"})
    words = [r[0] for r in results]
    assert "Transformer架构" in words
    assert "Transformer" not in words  # not split


def test_cleanup_after_added_words():
    _tokenize_with_added_words("Transformer架构测试", {"Transformer架构"})
    results = _tokenize_with_added_words("Transformer架构测试", set())
    words = [r[0] for r in results]
    assert "Transformer架构" not in words


def test_added_words_empty_set():
    results = _tokenize_with_added_words("hello world", set())
    assert len(results) > 0


# ── tokenize_with_concepts ───────────────────────────────────────────────────

def test_concepts_marked_keyword():
    tokens = tokenize_with_concepts(
        "Transformer架构利用了注意力机制", ["Transformer架构", "注意力机制"]
    )
    kw = {t["text"]: t["style_type"] for t in tokens}
    assert kw["Transformer架构"] == "keyword"
    assert kw["注意力机制"] == "keyword"
    assert kw.get("利用") != "keyword"


def test_non_concept_classified():
    tokens = tokenize_with_concepts("深度学习是机器学习分支", ["深度学习"])
    defaults = [t for t in tokens if t["style_type"] != "keyword"]
    assert len(defaults) > 0
    types = {t["style_type"] for t in defaults}
    assert types.issubset({"default", "connector", "punctuation", "number"})


def test_empty_concepts_fallback():
    tokens = tokenize_with_concepts("深度学习是机器学习", [])
    assert len(tokens) > 0
    for t in tokens:
        assert t["style_type"] != "keyword"


def test_multiple_concepts():
    concepts = ["Transformer", "注意力", "并行计算", "RNN"]
    tokens = tokenize_with_concepts(
        "Transformer和注意力机制实现并行计算而RNN不能", concepts
    )
    kw_texts = {t["text"] for t in tokens if t["style_type"] == "keyword"}
    assert "Transformer" in kw_texts
    assert "注意力" in kw_texts
    assert "并行计算" in kw_texts
    assert "RNN" in kw_texts


def test_nested_concepts_longest_wins():
    tokens = tokenize_with_concepts("人工智能技术发展", ["人工智能", "人工智能技术"])
    kw = [t["text"] for t in tokens if t["style_type"] == "keyword"]
    assert "人工智能技术" in kw
    assert "人工智能" not in kw


def test_duplicate_concept_merged():
    tokens = tokenize_with_concepts("RNN优于CNN而RNN更快", ["RNN", "CNN"])
    rnn = [t for t in tokens if t["text"] == "RNN"]
    assert len(rnn) == 1
    assert len(rnn[0]["start_offsets"]) == 2


def test_cleanup_concepts_leaves_jieba_clean():
    tokenize_with_concepts("Transformer架构测试", ["Transformer架构"])
    tokens = tokenize_with_concepts("Transformer架构测试", [])
    texts = {t["text"] for t in tokens}
    assert "Transformer架构" not in texts


# ── tokenize_with_vocabulary ─────────────────────────────────────────────────

_VOCAB = [
    {"id": "v1", "start_offsets": [0], "text": "Transformer架构", "style_type": "keyword"},
    {"id": "v2", "start_offsets": [15], "text": "注意力机制", "style_type": "keyword"},
    {"id": "v3", "start_offsets": [23], "text": "并行计算", "style_type": "keyword"},
    {"id": "v4", "start_offsets": [29], "text": "RNN", "style_type": "keyword"},
]


def test_vocab_reuses_ids():
    merged, _ = tokenize_with_vocabulary("Transformer架构使用了注意力机制", _VOCAB)
    id_by_text = {t["text"]: t["id"] for t in merged}
    assert id_by_text["Transformer架构"] == "v1"
    assert id_by_text["注意力机制"] == "v2"


def test_vocab_preserves_style():
    merged, _ = tokenize_with_vocabulary("RNN优于CNN", [{"id": "v4", "start_offsets": [], "text": "RNN", "style_type": "keyword"}])
    rnn = next(t for t in merged if t["text"] == "RNN")
    assert rnn["style_type"] == "keyword"


def test_new_tokens_collected():
    merged, new_tokens = tokenize_with_vocabulary("Transformer架构用于NLP", _VOCAB)
    new_texts = {t["text"] for t in new_tokens}
    assert "用于" in new_texts
    for t in new_tokens:
        assert t["id"] not in {"v1", "v2", "v3", "v4"}


def test_vocab_multiple_with_new():
    summary = "Transformer架构利用注意力机制实现并行计算与加速"
    merged, new_tokens = tokenize_with_vocabulary(summary, _VOCAB)
    vocab_texts = {t["text"] for t in merged if t["id"] in {"v1", "v2", "v3", "v4"}}
    assert vocab_texts == {"Transformer架构", "注意力机制", "并行计算"}
    assert len(new_tokens) > 0


def test_vocab_empty():
    merged, new_tokens = tokenize_with_vocabulary("hello world", [])
    assert len(merged) > 0
    texts = {t["text"] for t in merged}
    assert "hello" in texts or "world" in texts


# ── round-trip / integration ─────────────────────────────────────────────────

def test_round_trip_concepts_into_vocabulary():
    """Use tokenize_with_concepts output as vocab for tokenize_with_vocabulary."""
    concepts = ["Transformer架构", "注意力机制", "RNN"]
    doc_tokens = tokenize_with_concepts(
        "Transformer架构利用了注意力机制，RNN无法并行。", concepts
    )

    summary = "Transformer架构的核心是注意力机制。"
    merged, new_tokens = tokenize_with_vocabulary(summary, doc_tokens)

    id_by_text = {t["text"]: t["id"] for t in merged}
    tid1 = id_by_text["Transformer架构"]
    tid2 = id_by_text["注意力机制"]

    for t in doc_tokens:
        if t["text"] == "Transformer架构":
            assert tid1 == t["id"]
        if t["text"] == "注意力机制":
            assert tid2 == t["id"]

    assert any("核心" == t["text"] for t in new_tokens)
