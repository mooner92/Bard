# HANDOFF — 세션 인수인계 (2026-08-12 기준)

다른 Claude Code 세션(또는 사람)이 이 프로젝트를 이어받기 위한 상태 요약.
기술 절차는 [docs/PIPELINE.md](docs/PIPELINE.md), 개요는 [README.md](README.md).

## 프로젝트 한 줄

퍼블릭 도메인 고전 → 30초 한국어 내레이션 쇼츠. 이미지 우선 파이프라인
(대본 하네스 → TTS 길이 측정 → Qwen-Image 키프레임 → Wan 2.2 I2V → ffmpeg 조립)이
**검증 완료**돼 있고, 완성본 3편이 나온 상태.

## 작품 상태

| 작품 | 상태 | 위치 |
|---|---|---|
| 모비딕 v3.2 | ✅ 완성 (고래 종 통일까지) | `deliverables/mobydick/12_*` |
| 변신(카프카) v2 | ✅ 완성 (표현주의 스타일, 대사 포함) | `deliverables/kafka/20_*` |
| 사람은 무엇으로 사는가(톨스토이) | 🔶 **내레이션만 완료** — `output/tolstoy/narration.json` (passed) | 키프레임부터 진행 필요 |

톨스토이 다음 단계: 스타일 블록 제안 — "Russian lubok folk art / icon painting inspired
illustration, snowy village, warm candlelight interiors, deep blue night palette" 계열로
6장면 키프레임(`scripts/gen_keyframe.py`) → 크롭 → I2V → TTS(문장별) → 조립.
장면 배정은 narration.json의 문장 내용에서 복원 가능 (S1 눈보라 교회 옆 청년 …
S6 하늘로 돌아가는 천사).

## 서비스 (재부팅 후 자동 기동)

| 서비스 | 방식 | 확인 |
|---|---|---|
| ComfyUI :8188 | `systemd: comfyui.service` (enabled) | `systemctl status comfyui` |
| Ollama :11434 (qwen3.6:27b) | `systemd: ollama` (enabled) | `ollama list` |

재부팅 직후 체크: `nvidia-smi`가 **595.84**로 정상 출력되는지 (재부팅 사유가
NVML 버전 불일치였음. 커널 6.8.0-137 + 모듈 5개 배치 확인 완료 상태에서 재부팅).
GPU 확인 후 `curl -s localhost:8188/queue` 로 ComfyUI 응답 확인.

## 환경 요점

- 저장소: `/home/mooner92/aivideo` = https://github.com/mooner92/wan22-shorts-pipeline (public)
  - git push는 SSH 별칭 `github-sub` (ssh.github.com:443 — **이 서버는 22번 아웃바운드 차단**)
- venv: `venv/` (torch 2.11 cu128, sm_75 포함). HF 로그인 완료(mooner92)
- Azure Speech 키: `.env` (gitignore됨). 음성 ko-KR-SunHiNeural, F0 무료 티어
- 모델: `ComfyUI/models/` (Wan2.2 T2V/I2V Q6_K, Qwen-Image Q4, Qwen-Image-Edit-2509 Q4,
  umt5 fp16, VAE는 **wan_2.1_vae** 사용), `models/gguf/`(qwen3.6 원본)
- 커스텀 노드: ComfyUI-GGUF, ComfyUI-MultiGPU, ComfyUI-Manager

## 운영 함정 (반드시 읽기)

1. **`git add -A` 금지** — models/ 63GB 해싱으로 멈춤. 명시 경로만 add
2. **`ollama run` 금지** — 스피너가 로그 오염. HTTP API + `"think": false`
3. `pkill -f "패턴"` 은 자기 자신을 잡는다 — `[패]턴` 형태로
4. 서버 **아웃바운드 간헐 불안정** — 파일 업로드/일부 다운로드 타임아웃. 재시도 또는 scp 우회
5. 장시간 백그라운드 감시 프로세스가 종종 kill됨 — 10분 내 감시 + 재장전 패턴 사용
6. ECC GateGuard 훅이 Bash/Write마다 사실 제시 요구 — 끄려면
   `ECC_DISABLED_HOOKS="pre:bash:gateguard-fact-force,pre:edit-write:gateguard-fact-force"`
7. 긴 GPU 작업은 `setsid nohup ... & disown` + 로그 파일 (Bash 2분 타임아웃 회피)
8. 완료 판정은 종료코드가 아니라 **산출 파일 + ffprobe 스트림 확인**으로 (거짓 성공 사례 2회)

## 미완 로드맵 (우선순위 순)

1. **톨스토이 완성** — 위 참조. 소요 약 1.5~2시간 GPU
2. **prepare_work.py** — Wikipedia action API로 사실 파일 자동화. 설계 확정됨:
   ko 우선/en 폴백, UA `aivideo-pipeline/0.1 (contact: mooner92@kakao.com)`, maxlag=5,
   작품당 1회 호출 후 SQLite 캐시(backend/db.py에 works 테이블 추가)
3. **검수 UI** — Next.js :3001 (Node 20 설치됨), FastAPI :8000 + backend/db.py 큐 연동.
   대본 의미 왜곡("던진→남기신" 실측)은 기계 검증 불가 → 사람 승인 게이트가 필수인 근거
4. 자막(내레이션과 **다른** 정보 — 연구 근거) / CC0 효과음 / BGM
5. YouTube 업로드 + 고정 댓글 자동화 (댓글 문구는 하네스로 생성 가능)
6. KEI 도서관 신착 연동 — **막힌 지점**: 목록이 JS 렌더링이라 브라우저 Network 탭에서
   실제 API URL 확인 필요 (사용자에게 요청해둔 상태). 신간은 위키 없음 → 알라딘/네이버 API 검토

## 영상 받기

```bash
scp -P 764 -r mooner92@192.168.1.103:/home/mooner92/aivideo/deliverables/ ./
```
인덱스: [VIDEOS.md](VIDEOS.md). 구버전은 `deliverables/_old/`.
