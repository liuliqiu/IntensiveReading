import uuid
import jieba


def tokenize_text(text: str) -> list[dict]:
    results = jieba.tokenize(text)
    return [
        {
            "id": str(uuid.uuid4()),
            "start_offset": start,
            "text": word,
            "style_type": "default",
            "ref_type": None,
            "ref_target_token_id": None,
            "ref_url": None,
            "ref_explanation": None,
        }
        for word, start, end in results
    ]
