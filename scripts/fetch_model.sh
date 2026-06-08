#!/usr/bin/env bash
# 임베딩 ONNX 모델(all-MiniLM-L6-v2)을 prjmgmt_models 볼륨에 채운다.
# HuggingFace LFS 가 막히는 망에서도 되도록, chroma 의 S3 미러에서 받는다.
set -euo pipefail

VOL="${MODELS_VOLUME:-prjmgmt_models}"
URL="https://chroma-onnx-models.s3.amazonaws.com/all-MiniLM-L6-v2/onnx.tar.gz"

echo "→ 볼륨 $VOL 준비"
docker volume create "$VOL" >/dev/null

echo "→ 모델 다운로드 + 추출 ($URL)"
docker run --rm -v "$VOL":/models alpine sh -c "
  set -e
  apk add --no-cache curl tar >/dev/null
  mkdir -p /models/all-MiniLM-L6-v2
  cd /tmp
  curl -fsSL -o onnx.tar.gz '$URL'
  tar xzf onnx.tar.gz
  cp onnx/* /models/all-MiniLM-L6-v2/
  echo '추출 완료:'; ls -la /models/all-MiniLM-L6-v2/
"
echo "✓ 모델 준비 완료 (볼륨 $VOL)"
