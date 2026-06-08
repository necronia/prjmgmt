"""로컬 ONNX 임베딩 (onnxruntime + tokenizers). 기본 all-MiniLM-L6-v2, dense 384-dim.

HuggingFace 다운로드 의존 없이 /models 볼륨의 ONNX 파일을 직접 실행한다.
(회사망 SSL 인터셉트로 HF 대용량 다운로드가 hang 되는 문제 회피.)
mean pooling(attention mask) + L2 normalize → sentence embedding.
"""
import os
from functools import lru_cache

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

from ..core.config import settings


@lru_cache(maxsize=1)
def _load():
    path = settings.embed_model_path
    sess = ort.InferenceSession(
        os.path.join(path, "model.onnx"),
        providers=["CPUExecutionProvider"],
    )
    tok = Tokenizer.from_file(os.path.join(path, "tokenizer.json"))
    tok.enable_truncation(max_length=settings.embed_max_tokens)
    tok.enable_padding(pad_id=0, pad_token="[PAD]")
    input_names = {i.name for i in sess.get_inputs()}
    return sess, tok, input_names


def _embed(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    sess, tok, input_names = _load()
    encs = tok.encode_batch(texts)
    input_ids = np.array([e.ids for e in encs], dtype=np.int64)
    attention_mask = np.array([e.attention_mask for e in encs], dtype=np.int64)

    feeds = {"input_ids": input_ids, "attention_mask": attention_mask}
    if "token_type_ids" in input_names:
        feeds["token_type_ids"] = np.zeros_like(input_ids)

    last_hidden = sess.run(None, feeds)[0]  # (B, T, H)
    mask = attention_mask[:, :, None].astype(np.float32)
    summed = (last_hidden * mask).sum(axis=1)
    counts = np.clip(mask.sum(axis=1), 1e-9, None)
    mean = summed / counts
    norm = np.clip(np.linalg.norm(mean, axis=1, keepdims=True), 1e-9, None)
    return (mean / norm).astype(np.float32).tolist()


def embed_passages(texts: list[str]) -> list[list[float]]:
    """문서 청크 임베딩."""
    p = settings.embed_passage_prefix
    return _embed([f"{p}{t}" for t in texts])


def embed_query(text: str) -> list[float]:
    """질의 임베딩."""
    return _embed([f"{settings.embed_query_prefix}{text}"])[0]


def warmup() -> None:
    """기동 시 모델 미리 로드."""
    embed_query("warmup")
