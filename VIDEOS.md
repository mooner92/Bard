# 영상 인덱스

원본 파일은 저장소에 포함하지 않습니다. scp로 가져가세요:
```
scp -P 764 -r mooner92@192.168.1.103:/home/mooner92/aivideo/deliverables/ ./
```

## 디렉터리 구조
```
deliverables/
├── mobydick/     현행 완성본 (v3, 이미지 우선 파이프라인)
├── kafka/        카프카 변신 v1 (T2V — v3 파이프라인 재제작 예정)
└── _old/
    ├── benchmark/     하드웨어 벤치마크 클립 7개 (해상도·속도 실측)
    └── mobydick_v1/   T2V 시절 모비딕 (무음 프리뷰 + 장면 클립)
```

## 현행

| 제목 | 해상도 | 길이 | 용량 | 경로 |
|---|---|---|---|---|
| 모비딕 v3 (Qwen-Image 키프레임 + Wan I2V) | 1080×1920 | 30.5s | 26.6MB | `deliverables/mobydick/10_모비딕_v3_이미지우선_30.5s_1080x1920.mp4` |
| 모비딕 v3 압축본 | 1080×1920 | 30.5s | 12.0MB | `deliverables/mobydick/10_모비딕_v3_압축본_12MB.mp4` |
| 카프카 변신 v1 | 1080×1920 | 29.6s | 12.3MB | `deliverables/kafka/kafka_변신_v1_29.6s.mp4` |

## 파이프라인 (v3 확정 구조)
대본(qwen3.6) → TTS 길이측정(Azure) → 키프레임(Qwen-Image Q4, 스타일블록 고정, CFG 2.5)
→ 선별·재생성 → 캡션 크롭 → Wan 2.2 I2V 81프레임 → 문장 길이 감속 동기화 → 조립(ffmpeg)

실측: 키프레임 5~9분/장, I2V 7~9분/클립, 완성본 1편(6장면) GPU 약 2시간(교정 포함).
