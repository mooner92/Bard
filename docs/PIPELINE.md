# 파이프라인 상세

완성본 1편(6장면, 30초 안팎)을 만드는 전 과정. 모든 명령은 저장소 루트에서 실행하며
ComfyUI(:8188)와 Ollama(:11434)가 떠 있어야 한다. 실측 시간은 Quadro RTX 6000(Turing) 기준.

## 0. 사실 파일

원작의 핵심 사실과 배경을 담은 텍스트. LLM 환각 방지의 근거가 되므로
**여기 없는 내용은 대본에 못 들어간다**는 전제로 쓴다.

`scripts/fetch_book_facts.py` 가 자동 수집한다 — 고전은 위키백과의 줄거리·배경 절
(`--format narrative`), 현대서는 정보나루 출판사 소개문 + 위키 첫 문단. 어느 쪽이든
**세계 단서**(장소·계절·사물 단어)를 세어 고전 4개·현대 5개 미만이면 만들지 않는다.
얇은 재료를 도서관 통계로 채웠다가 영상이 책 소개가 된 사고가 있었다 — 아래 실패 사례 참조.

```bash
venv/bin/python scripts/fetch_book_facts.py --title 날개 --author 이상 --format narrative
venv/bin/python scripts/refill_queue.py --classics --max-add 4    # 고전 원장에서 큐로
venv/bin/python scripts/refill_queue.py --limit 40 --max-add 4    # 인기대출 ∩ KEI 소장
```

```
허먼 멜빌 『모비딕』(1851). 화자는 선원 이슈메일. 포경선 피쿼드호의 선장 에이해브는
과거 흰 향유고래 모비딕에게 한쪽 다리를 잃었고, 고래뼈로 깎은 의족을 짚는다. …
장면 순서: S1 밤 갑판의 에이해브(의족), S2 흰 향유고래 등장, …
```

## 1. 대본 (하네스)

```bash
venv/bin/python scripts/write_script.py --title 모비딕 \
  --facts facts/mobydick.txt --scenes 6 \
  --ending "소설 모비딕에서 만날 수 있습니다" \
  --out output/mobydick/narration.json
```

- 어미 계열 배정: `[합니다체, 구어체, 명사종결, 합니다체, 구어체, 합니다체]`
- 4회 재수정 후에도 남는 문제는 사람이 마감하는 게 재실행보다 싸다 (실측: 회당 ~10분)
- `passed: false`여도 JSON은 저장된다 — issues 목록이 고칠 위치를 정확히 알려준다
- 기계가 못 잡는 의미 왜곡("던진→남기신")은 반드시 사람이 읽고 확인

## 2. TTS와 길이 측정

```bash
# 문장별 wav 생성 (Azure Speech REST, riff-24khz-16bit-mono-pcm)
# rate='-5%' 로 약간 느리게. 실측: 한국어 초당 약 6.5자
ffprobe -show_entries format=duration <wav>   # 이 길이가 해당 클립의 목표 길이
```

30초 목표면 총 180~200자. 문장 길이(22~42자)가 곧 클립 길이(3.4~6.5초)가 된다.

## 3. 키프레임 (Qwen-Image)

```bash
venv/bin/python scripts/gen_keyframe.py --seed 42 --prefix "mobydick_kf/s1" \
  --prompt "<스타일 블록> + <장면 묘사>" --negative "photorealistic, ..., caption, letters"
```

- **스타일 블록을 모든 장면 프롬프트의 맨 앞에, 바이트 동일하게** 넣는 것이 일관성의 전부
- 720×1280 / 20스텝 / CFG 2.5 / AuraFlow shift 3.1 / 약 5분
- CFG가 1이 아니므로 네거티브가 실제로 작동한다 — T2V와의 결정적 차이
- 피사체 형태는 기하학 용어("blocky rectangular")가 아니라 **해부학 묘사**로:
  "둥글게 부푼 이마, 유선형 몸통, 좁은 아래턱" (실측: 기하 용어는 문자 그대로 상자가 나옴)
- 고서 도판 스타일은 가짜 캡션 글자를 유도한다 → 네거티브로 줄이고 크롭으로 마감

### 3-1. 피사체 통일 (Qwen-Image-Edit)

```bash
venv/bin/python scripts/gen_edit.py --ref approved_whale.png \
  --prefix "mobydick_kf/s6" --prompt "The exact same white sperm whale from the
  reference image — <해부학 유지 문구> — now <새 장면 묘사>, <스타일 블록>"
```

- **참조는 피사체 단독으로.** `--scene`으로 장면 참조를 함께 주면 장면 쪽 피사체가 이긴다 (2회 실측)
- 약 15분/장. 같은 캐릭터·같은 사물이 여러 장면에 나올 때만 사용

## 4. 크롭

```bash
# 상하 6% 크롭(가짜 캡션 제거) → 9:16 중앙 크롭 → 480×848
ffmpeg -i kf.png -vf "crop=iw:ih*0.88:0:ih*0.06,crop='min(iw,ih*480/848)':'min(ih,iw*848/480)',scale=480:848:flags=lanczos" ComfyUI/input/kf1.png
```

## 5. I2V (Wan 2.2)

```bash
venv/bin/python scripts/gen_i2v.py --image kf1.png --prefix "mobydick_i2v/s1" \
  --length 81 --seed 42 --prompt "<모션·카메라만: mist drifts, slow dolly in>"
```

- 스타일은 이미지가 결정했으므로 **프롬프트에는 모션·카메라만** (Alibaba 공식 I2V 권장)
- 81프레임 고정 (121은 첫 프레임 손상 보고), 8스텝, 약 7.3분/클립
- 배치: unet은 cuda:0, VAE는 cuda:1, 텍스트 인코더는 CPU — 24GB 완전 로드 유지
- A14B는 Wan **2.1** VAE(16채널)를 쓴다. wan2.2_vae(48채널)는 TI2V-5B 전용 — 물리면 채널 불일치로 죽는다

## 6. 조립

```bash
# 클립별 감속 배율 = 문장 wav 길이 / 3.375초(81f@24fps) → setpts
# concat(영상) + concat(wav) → 1080×1920 lanczos, h264 high crf20, aac 192k 48kHz
# 30MiB 초과 대비 crf26 압축본도 함께 생성
```

감속(1.3~1.8배)은 판화풍 느린 모션에서 자연스럽다. 대본이 바뀌면 이 단계만 다시 돌린다.

## 실패 사례 기록 (재발 방지)

| 증상 | 원인 | 해결 |
|---|---|---|
| 스타일 무시, 네거티브 무효 | 증류 LoRA의 CFG=1 | 이미지 우선 전환 |
| 고래가 장면마다 다른 종 | 키프레임 독립 생성 | Edit 참조 편집(단독 참조) |
| 향유고래가 지우개 모양 | "blocky rectangular" 직역 | 해부학 묘사로 교체 |
| 대본 전부 "~한다"체 | 어미 자유 방임 | 문장별 계열 배정 + 검증기 |
| 영어 사고 텍스트가 문장에 유입 | qwen3.6 think 누출 | API `think:false` + 한글 비율 검증 |
| `<제목>` 이 TTS를 깨뜨림 | SSML(XML) 태그로 해석 | 파서에서 꺾쇠 원천 제거 |
| 720p T2V 29분 | Turing 무FA → VRAM 선점 → 부분 로드 | 480×848 유지 |
| `git add -A` 멈춤 | models/ 63GB 해싱 | models/ .gitignore + 명시 경로 add |
| 업로드/다운로드 간헐 실패 | 서버 아웃바운드 불안정 | 재시도 + scp/deliverables 우회 |
| **영상이 책 소개가 됨** | 얇은 재료를 도서관 통계로 채움 | 통계 제거 + `meta_issues` + `world_material` 하한 |
| **"별표는 강조를 나타내며"** | 프롬프트 지시어의 낱말을 소재로 삼음 | 지시문에 기호만 쓰고 이름 금지 + `leak_issues` |
| 위키 '모순' → 논리학 문서 | 제목이 일반명사 | 본문에 저자명 있는지 확인 후 채택 |
| 다른 책 제목이 내용으로 섞임 | 함께 빌린 책 목록을 사실파일에 넣음 | 사실파일에서 제외 |
| 마무리 문구가 사라짐 | 자료 대조 수리가 마지막 문장을 다시 씀 | 수리 수용 조건에 마무리 문구 확인 추가 |
| 정지 후 재기동이 "이미 실행 중" | 부모만 죽여 자식이 flock 보유 | 트랩에서 `pkill -P $$` |
| 감속이 1.5배를 살짝 초과 | 프레임을 4n+1 로 내림 | 올림으로 변경 |
| 완성본 −17 LUFS | 조립에 정규화 없음 | 인코딩에 `loudnorm=I=-14` |
| 20:00 타이머가 새벽 5시에 동작 | 서버 시계 UTC | 타이머·스크립트에 `Asia/Seoul` 명시 |
| 강제 종료된 밤의 생산 요약 없음 | 정상 경로에만 기록 | `SIGTERM` 트랩에서 기록 |
