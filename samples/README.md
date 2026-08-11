# Wan 2.2 T2V 테스트 클립

Quadro RTX 6000 24GB x2 (Turing sm_75) / ComfyUI + Wan2.2-A14B GGUF Q6_K
+ Lightning 4-step 증류 LoRA, CFG=1, euler/simple, shift=8.0, 24fps.

## 핵심 발견

Turing은 FlashAttention을 지원하지 않아 어텐션 활성화 메모리가 크다.
latent이 커지면 ComfyUI가 추론용으로 21GB를 예약해 12GB 가중치가
부분 로드되고(2.5GB 상주 / 9GB CPU 오프로드) 스텝당 400초대로 붕괴한다.
디바이스 배치(인코더 GPU 이동, unet 카드 분산)로는 해결되지 않았다.
해상도를 낮춰 완전 로드를 유지하는 것이 유일한 해법.

| 파일 | 해상도 | 프레임 | 로드 | 소요 |
|---|---|---|---|---|
| 01 | 480x832 | 33 | 완전 | 10초 |
| 02 | 480x832 | 121 | 완전 | 6분 17초 |
| 03 | 544x960 | 121 | 완전 | 9분 40초 |
| 04 | 544x960 | 121 | 완전 | 9분 40초 |
| 05 | 720x1280 | 121 | **부분(9GB 오프로드)** | 29분 11초 |
| 06 | 720x1280 | 121 | **부분(9GB 오프로드)** | 29분 11초 |
| 07 | 480x848 | 121 | 완전 | 6분 55초 |

03/04는 연속 생성. 두 번째도 동일 시간 -> 모델 로딩이 아닌 순수 연산이며,
배치로 묶어 로딩을 분할상환할 여지는 없다.
05/06은 디바이스 배치만 다르고 결과가 같다(배치는 원인이 아님을 확인).

## 프롬프트

01~06: "cinematic aerial shot flying over a vast misty forest at dawn,
volumetric god rays through tall pine trees, slow drifting camera,
atmospheric, film grain"

07 (딥타임 양식화 검증): "painterly illustrated animation of a shallow
Cambrian sea floor 500 million years ago, alien trilobites and anomalocaris
drifting through green-lit water, swaying primitive algae, visible brushwork
and paper texture, muted ochre and teal palette, natural history book
illustration style, slow steady camera push forward, NOT photorealistic"
negative: photorealistic, photograph, live action, 3d render, cgi, human,
people, text, watermark, blurry, distorted, modern objects

## 확정 프로덕션 규격

480x848 (9:16) / 121프레임 / 5초 / 4스텝. 클립당 약 7분.
ffmpeg로 1080x1920 업스케일 후 업로드.
