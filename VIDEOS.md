# 영상 인덱스

원본 파일은 저장소에 포함하지 않습니다. 아래 경로에서 scp로 가져가세요.

```
scp -P 764 -r mooner92@192.168.1.103:/home/mooner92/aivideo/deliverables/ ./
```

개별 파일만 받으려면:

```
scp -P 764 mooner92@192.168.1.103:'/home/mooner92/aivideo/deliverables/mobydick/*.mp4' ./
```

최종 갱신: 2026-08-11


## 모비딕 (책 속 세계 콘셉트 1차)

| 제목 | 해상도 | 길이 | 용량 | 경로 |
|---|---|---|---|---|
| 00_모비딕_무음프리뷰_30s_1080x1920 | 1080×1920 | 30.2s | 31.4MB | `deliverables/mobydick/00_모비딕_무음프리뷰_30s_1080x1920.mp4` |
| 01_장면1_5s_480x848 | 480×848 | 5.0s | 1.4MB | `deliverables/mobydick/01_장면1_5s_480x848.mp4` |
| 02_장면2_5s_480x848 | 480×848 | 5.0s | 0.9MB | `deliverables/mobydick/02_장면2_5s_480x848.mp4` |
| 03_장면3_5s_480x848 | 480×848 | 5.0s | 1.1MB | `deliverables/mobydick/03_장면3_5s_480x848.mp4` |
| 04_장면4_5s_480x848 | 480×848 | 5.0s | 1.3MB | `deliverables/mobydick/04_장면4_5s_480x848.mp4` |
| 05_장면5_5s_480x848 | 480×848 | 5.0s | 1.4MB | `deliverables/mobydick/05_장면5_5s_480x848.mp4` |
| 06_장면6_5s_480x848 | 480×848 | 5.0s | 1.6MB | `deliverables/mobydick/06_장면6_5s_480x848.mp4` |

## 벤치마크 · 검증 클립

| 제목 | 해상도 | 길이 | 용량 | 경로 |
|---|---|---|---|---|
| 01_스모크_480x832_33f_10초 | 480×832 | 1.4s | 0.4MB | `deliverables/benchmark/01_스모크_480x832_33f_10초.mp4` |
| 02_480x832_121f_6분17초 | 480×832 | 5.0s | 0.6MB | `deliverables/benchmark/02_480x832_121f_6분17초.mp4` |
| 03_544x960_121f_9분40초 | 544×960 | 5.0s | 0.9MB | `deliverables/benchmark/03_544x960_121f_9분40초.mp4` |
| 04_544x960_121f_9분40초_다른시드 | 544×960 | 5.0s | 1.0MB | `deliverables/benchmark/04_544x960_121f_9분40초_다른시드.mp4` |
| 05_720x1280_121f_29분11초_부분로드 | 720×1280 | 5.0s | 1.5MB | `deliverables/benchmark/05_720x1280_121f_29분11초_부분로드.mp4` |
| 06_악어떼_480x848_피사체검증 | 480×848 | 5.0s | 1.9MB | `deliverables/benchmark/06_악어떼_480x848_피사체검증.mp4` |
| 07_딥타임_캄브리아기_480x848 | 480×848 | 5.0s | 1.5MB | `deliverables/benchmark/07_딥타임_캄브리아기_480x848.mp4` |

## 모비딕 v3 (이미지 우선 파이프라인 — 확정 구조)

| 제목 | 해상도 | 길이 | 용량 | 경로 |
|---|---|---|---|---|
| 모비딕 v3 (Qwen-Image 키프레임 + Wan I2V) | 1080×1920 | 30.5s | 26.6MB | `deliverables/mobydick/10_모비딕_v3_이미지우선_30.5s_1080x1920.mp4` |
| 모비딕 v3 압축본 | 1080×1920 | 30.5s | 12.0MB | `deliverables/mobydick/10_모비딕_v3_압축본_12MB.mp4` |
| 카프카 변신 v1 (T2V) | 1080×1920 | 29.6s | 12.3MB | `deliverables/kafka_변신_v1_29.6s.mp4` |

파이프라인: 대본(qwen3.6) → TTS 길이측정(Azure) → 키프레임(Qwen-Image Q4, 스타일블록 고정, CFG 2.5)
→ 선별·재생성 → 캡션 크롭 → Wan 2.2 I2V 81프레임 → 문장 길이에 맞춘 감속 → 조립.
키프레임 2~3분/장, I2V 7~9분/클립. T2V 대비 스타일·피사체·일관성 문제 해결.
