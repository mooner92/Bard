# wan22-shorts-pipeline

로컬 GPU 2장으로 굴러가는 **문학 각색 유튜브 쇼츠 자동 제작 파이프라인**.
퍼블릭 도메인 고전(모비딕, 변신, 톨스토이 단편 등)을 30초 안팎의 세로 영상으로 만든다 —
대본 생성부터 키프레임, 영상화, 한국어 내레이션, 조립까지 전부 이 서버 안에서.

완성 영상 목록과 받는 방법은 [VIDEOS.md](VIDEOS.md) 참고.

## 왜 이미지 우선(image-first)인가

처음에는 텍스트→영상(T2V)으로 직행했다가 세 가지 실패를 겪었다:

1. **스타일 무시** — "19세기 동판화풍" 지시가 광택 나는 디지털 아트로 나옴
2. **피사체 부정확** — 흰 향유고래가 회색 혹등고래로, 19세기 선원이 현대 작업복으로
3. **클립 간 비일관** — 6장면이 6가지 화풍

원인은 Lightning 증류 LoRA가 강제하는 **CFG=1에서 네거티브 프롬프트가 아예 계산되지 않는 것**.
해법은 스타일이 실제로 통제되는 이미지 모델(CFG 2.5)에서 키프레임을 확정하고,
영상 모델(I2V)은 그 이미지를 움직이는 역할만 맡기는 구조 전환이었다.

```
대본 하네스 ──> TTS 길이 측정 ──> 키프레임 생성 ──> 선별/교정 ──> I2V ──> 조립
(qwen3.6:27b)   (Azure Speech)     (Qwen-Image)     (Qwen-Image    (Wan 2.2   (ffmpeg)
 검증 8종        문장별 wav 실측     스타일 블록 고정    -Edit 참조)     81프레임)   문장 길이 동기화
```

- **내레이션이 시계다**: 문장별 TTS 실측 길이에 맞춰 각 클립을 감속하므로
  장면 전환이 문장 시작과 정확히 일치한다. 대본이 바뀌어도 영상 재생성 없이 재조립.
- **스타일 블록은 바이트 단위로 동일하게**: 모든 키프레임 프롬프트가 같은 스타일 문구로
  시작한다. 작품마다 다른 화풍(모비딕=해양 동판화, 변신=표현주의 잉크)을 블록 교체로 얻는다.
- **피사체 일관성은 참조 편집으로**: 같은 고래를 여러 장면에 쓰려면 Qwen-Image-Edit에
  승인된 이미지를 **단독 참조**로 넣는다. 장면 참조와 같이 주면 장면 쪽 피사체가 이긴다(실측).

## 하드웨어와 실측

Quadro RTX 6000 24GB × 2 (Turing, sm_75). **FlashAttention·bf16·fp8 미지원** — 이 제약이 설계 전반을 결정했다.

| 작업 | 실측 | 비고 |
|---|---|---|
| 키프레임 1장 (Qwen-Image Q4, 20스텝) | 약 5분 | 재생성·선별이 싸다 |
| 참조 편집 1장 (Qwen-Image-Edit) | 약 15분 | 피사체 통일용 |
| I2V 1클립 (Wan 2.2, 81프레임, 8스텝) | 약 7.3분 | 문장 하나 = 클립 하나 |
| T2V 720×1280 (비교용) | 29분 | 부분 로드로 붕괴 — 사용 안 함 |
| 한국어 TTS | 초당 약 6.5자 | 문장 30자 ≈ 4.6초 |
| **완성본 1편 (6장면)** | **GPU 약 2시간** | 교정 반복 포함 |

Turing에서 확인된 함정: latent가 커지면 ComfyUI가 추론용 VRAM을 선점해 12GB 모델이
부분 로드(9GB CPU 오프로드)되고 스텝당 400초대로 무너진다. 480×848이 완전 로드 유지선.
121프레임은 첫 프레임 손상이 보고돼 있어 81프레임을 쓴다. SageAttention·torch.compile은
sm_75에서 동작하지 않으므로 시도하지 말 것.

## 대본 하네스 (`scripts/write_script.py`)

LLM에게 "다양하게 써라"는 지시는 강제되지 않는다. 코드가 판정하고 불합격 문장만 되돌린다:

```
초안 → 스타일 패스 → 기계 검증 → 불합격 문장별 재작성(최대 4회) → 비문 교정 패스
```

검증 규칙: 문장 길이(22~42자) / 같은 어미 연속 금지 / **문장별 어미 계열 배정**
(합니다체·구어체·명사종결 교차 — 자유를 주면 한 계열로 쏠린다) / 한다체·고어체 차단 /
한국어 본문 비율(LLM 사고 텍스트 오염 차단) / 꺾쇠 원천 제거(`<제목>`이 SSML을 깨뜨림) /
마무리 문구 강제 / 금지어. 원작 사실은 `--facts` 파일로 주입해 환각을 막는다.

기계가 못 잡는 것: **의미 왜곡** ("아버지가 던진 사과"→"남기신 사과" 순화 실측).
최종 검수는 사람 몫이다.

## 스크립트

| 파일 | 역할 |
|---|---|
| `scripts/write_script.py` | 대본 하네스 (검증·재수정 루프) |
| `scripts/gen_keyframe.py` | Qwen-Image 키프레임 (ComfyUI API) |
| `scripts/gen_edit.py` | Qwen-Image-Edit 참조 편집 (피사체 통일) |
| `scripts/gen_i2v.py` | Wan 2.2 I2V 영상화 (81프레임) |
| `scripts/gen_t2v.py` | Wan 2.2 T2V (벤치마크·보조용) |
| `scripts/download_models.sh` | 모델 일괄 다운로드 |
| `backend/db.py` | SQLite 작업 큐 (UI·cron·에이전트 공용) |

상세 파라미터와 실행 예시는 [docs/PIPELINE.md](docs/PIPELINE.md), 서사 설계 근거는 [docs/NARRATIVE.md](docs/NARRATIVE.md), 로드맵·스펙은 [docs/PLAN.md](docs/PLAN.md).

## 모델과 라이선스

| 모델 | 양자화 | 라이선스 | 용도 |
|---|---|---|---|
| Wan 2.2 A14B (T2V/I2V) | GGUF Q6_K | **Apache 2.0** | 영상 생성 |
| Wan2.2-Lightning LoRA | — | Apache 2.0 | 4~8스텝 증류 |
| Qwen-Image | GGUF Q4_K_M | Apache 2.0 | 키프레임 |
| Qwen-Image-Edit-2509 | GGUF Q4_K_M | Apache 2.0 | 참조 편집 |
| Qwen3.6-27B | GGUF Q4_K_M (Ollama) | Apache 2.0 | 대본 |
| Azure Speech (ko-KR Neural) | 클라우드 | F0 무료 티어 | 내레이션 |

전부 상업적 이용이 가능한 조합이다. 소재는 퍼블릭 도메인 고전만 쓴다 —
저작권과 유튜브의 "본인이 만들지 않은 자료의 낭독" 수익화 제한을 동시에 비켜간다.
유튜브 정책상 완전 양식화(비실사) 콘텐츠는 AI 고지 의무가 없고, 60초 초과 쇼츠에
저작권 클레임이 걸리면 전 세계 차단이므로 30초 안팎을 유지한다.

## 설치 요약

```bash
python3 -m venv venv && source venv/bin/activate
pip install "huggingface_hub[cli]" fastapi "uvicorn[standard]"
pip install --index-url https://download.pytorch.org/whl/cu128 torch torchvision torchaudio
git clone https://github.com/comfyanonymous/ComfyUI  # + ComfyUI-GGUF, ComfyUI-MultiGPU
bash scripts/download_models.sh                      # Wan 2.2 세트 (~63GB)
cp .env.example .env                                 # Azure Speech 키 입력
python ComfyUI/main.py --listen 127.0.0.1 --port 8188
```

## 로드맵

- [ ] `prepare_work.py` — Wikipedia action API로 줄거리·인물 자동 수집 → 사실 파일 생성
- [ ] 작품 설정 파일(`works/*.json`) — 스타일 블록·어미 배정·마무리 문구를 데이터로
- [ ] Next.js 검수 UI (:3001) — 대본·키프레임·완성본 승인 게이트
- [ ] 자막(내레이션과 다른 정보) · CC0 효과음 · BGM 레이어
- [ ] 업로드 자동화 (YouTube Data API) + 고정 댓글 자동 등록
- [ ] 신간 감지 (도서관 신착 → 주제 발굴, 알라딘/네이버 API)
