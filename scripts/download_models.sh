#!/usr/bin/env bash
# Wan 2.2 모델 다운로드 (Quadro RTX 6000 24GB x2 / Turing sm_75 구성용)
# 1차: I2V 파이프라인(~38GB)  2차: T2V 추가(~25GB)
# 재실행 안전: 이미 받은 파일은 건너뜀
set -uo pipefail

BASE=/home/mooner92/aivideo
M=$BASE/ComfyUI/models
STAGE=$BASE/.hf_stage
source $BASE/venv/bin/activate

mkdir -p "$STAGE" "$M/unet" "$M/text_encoders" "$M/vae" "$M/loras"

# repo, repo내경로, 목적지디렉터리, 최종파일명
DL () {
  local repo="$1" path="$2" dest="$3" name="$4"
  if [ -f "$dest/$name" ]; then
    echo ">>> SKIP (이미 있음): $name"
    return 0
  fi
  echo ">>> DOWNLOAD: $repo :: $path"
  if hf download "$repo" "$path" --local-dir "$STAGE"; then
    mv -f "$STAGE/$path" "$dest/$name"
    echo ">>> OK: $dest/$name  ($(du -h "$dest/$name" | cut -f1))"
  else
    echo ">>> FAIL: $repo :: $path"
    return 1
  fi
}

echo "======== 1차: I2V 파이프라인 ========"
DL QuantStack/Wan2.2-I2V-A14B-GGUF \
   HighNoise/Wan2.2-I2V-A14B-HighNoise-Q6_K.gguf \
   "$M/unet" wan2.2_i2v_high_noise_Q6_K.gguf

DL QuantStack/Wan2.2-I2V-A14B-GGUF \
   LowNoise/Wan2.2-I2V-A14B-LowNoise-Q6_K.gguf \
   "$M/unet" wan2.2_i2v_low_noise_Q6_K.gguf

# Turing은 FP8 네이티브 연산이 없어 fp8 가중치도 업캐스트됨 -> fp16 선택
DL Comfy-Org/Wan_2.2_ComfyUI_Repackaged \
   split_files/text_encoders/umt5_xxl_fp16.safetensors \
   "$M/text_encoders" umt5_xxl_fp16.safetensors

DL Comfy-Org/Wan_2.2_ComfyUI_Repackaged \
   split_files/vae/wan2.2_vae.safetensors \
   "$M/vae" wan2.2_vae.safetensors

DL lightx2v/Wan2.2-Distill-Loras \
   wan2.2_i2v_A14b_high_noise_lora_rank64_lightx2v_4step_1022.safetensors \
   "$M/loras" wan2.2_i2v_high_noise_lightx2v_4step.safetensors

DL lightx2v/Wan2.2-Distill-Loras \
   wan2.2_i2v_A14b_low_noise_lora_rank64_lightx2v_4step_1022.safetensors \
   "$M/loras" wan2.2_i2v_low_noise_lightx2v_4step.safetensors

echo "======== 2차: T2V 추가 ========"
DL QuantStack/Wan2.2-T2V-A14B-GGUF \
   HighNoise/Wan2.2-T2V-A14B-HighNoise-Q6_K.gguf \
   "$M/unet" wan2.2_t2v_high_noise_Q6_K.gguf

DL QuantStack/Wan2.2-T2V-A14B-GGUF \
   LowNoise/Wan2.2-T2V-A14B-LowNoise-Q6_K.gguf \
   "$M/unet" wan2.2_t2v_low_noise_Q6_K.gguf

DL lightx2v/Wan2.2-Distill-Loras \
   wan2.2_t2v_A14b_high_noise_lora_rank64_lightx2v_4step_1217.safetensors \
   "$M/loras" wan2.2_t2v_high_noise_lightx2v_4step.safetensors

DL lightx2v/Wan2.2-Distill-Loras \
   wan2.2_t2v_A14b_low_noise_lora_rank64_lightx2v_4step_1217.safetensors \
   "$M/loras" wan2.2_t2v_low_noise_lightx2v_4step.safetensors

echo "======== 전체 완료 ========"
find "$M" -type f -size +10M -printf '%s\t%p\n' | sort -rn | awk -F'\t' '{printf "%7.2f GB  %s\n", $1/1e9, $2}'
rm -rf "$STAGE"
