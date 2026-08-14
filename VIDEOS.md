# 영상 인덱스

원본 파일은 저장소에 포함하지 않습니다. scp로 가져가세요:
```
scp -P <SSH_PORT> -r <USER>@<SERVER>:/home/mooner92/aivideo/deliverables/ ./
```

## 현행 완성본

| 제목 | 길이 | 용량 | 경로 |
|---|---|---|---|
| 모비딕 v3.2 (고래 종 통일, 하네스 내레이션) | 31.0s | 24.7MB | `deliverables/mobydick/12_모비딕_v3.2_고래통일_31s.mp4` |
| 모비딕 v3.2 압축본 | 31.0s | 11.1MB | `deliverables/mobydick/12_모비딕_v3.2_압축본.mp4` |
| 변신 v2 (표현주의, 대사 포함 내레이션) | 31.7s | 13.3MB | `deliverables/kafka/20_변신_v2_이미지우선_32s.mp4` |
| 변신 v2 압축본 | 31.7s | 6.0MB | `deliverables/kafka/20_변신_v2_압축본.mp4` |

전부 1080×1920, h264+aac, 이미지 우선 파이프라인(README 참조) 산출물.

## 야간 자동 생산분 (2026-08-13 밤, v0.9)

승인 전이라 `deliverables/` 로 승격하지 않았고 `output/<작품>/final_night.mp4` 에 있다.
**이 7편은 v0.9 규칙으로 만들어졌다** — 현대서 소개형이 작품 세계 대신 도서관 정보를
말하는 결함이 있다(v1 에서 바로잡음, [SPEC](docs/SPEC.md) §1 참조). 파이프라인 검증용으로만 본다.

| 작품 | 길이 | 용량 | 대본 검증 |
|---|---|---|---|
| tolstoy (사람은 무엇으로 사는가) | 36.8초 | 20.3MB | 11건 |
| annyeongira_geuraeteo (안녕이라 그랬어) | 38.7초 | 8.5MB | 4건 |
| bulpyeonhan_pyeonuijeom (불편한 편의점) | 44.9초 | 7.3MB | 통과 |
| mosun (모순) | 50.3초 | 8.3MB | 4건 |
| honghakui_jari (홍학의 자리) | 44.4초 | 8.2MB | 2건 |
| goeteneun_modeun_geoteul (괴테는 모든 것을 말했다) | 40.5초 | 7.3MB | 통과 |
| naui_wanbyeokhan_jangrye (나의 완벽한 장례식) | 39.5초 | 7.0MB | 1건 |

작품별 기계 점검(길이·감속·음량·리듬)은 `logs/review/<작품>.md`.

## 진행 중

- 톨스토이 『사람은 무엇으로 사는가』 — 내레이션 완료, 키프레임부터 남음 (HANDOFF.md)

## 구버전 (`deliverables/_old/`)

- `mobydick_v3/` — v3(첫 이미지 우선판)·v3.1(하네스 내레이션판, 고래 미통일)
- `mobydick_v1/` — T2V 시절 무음 프리뷰 + 장면 클립
- `benchmark/` — 하드웨어 실측 클립 7개
- `kafka_변신_v1_29.6s.mp4` — T2V 시절 1차본

## 파이프라인 요약

대본 하네스(qwen3.6) → TTS 길이측정(Azure) → 키프레임(Qwen-Image, 스타일블록 고정)
→ 참조 편집(피사체 통일) → 크롭 → Wan 2.2 I2V 81프레임 → 문장 길이 감속 동기화 → 조립.
상세: [docs/PIPELINE.md](docs/PIPELINE.md) · 인수인계: [HANDOFF.md](HANDOFF.md)
