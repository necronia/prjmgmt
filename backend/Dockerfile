# Backend — FastAPI + Anthropic + FastEmbed(BGE-M3, ONNX)
FROM python:3.11-slim

WORKDIR /app

# onnxruntime 런타임 의존성
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 임베딩 모델은 이미지에 굽지 않고 /models 볼륨에 마운트해서 사용한다.
# (회사망 SSL 인터셉트로 빌드 중 HF 대용량 다운로드가 hang 되는 문제 회피 — 모델은
#  resume 재시도로 호스트/볼륨에 미리 받아둔다. scripts/fetch_model.sh 참고.)
ENV EMBED_CACHE_DIR=/models

COPY app ./app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
