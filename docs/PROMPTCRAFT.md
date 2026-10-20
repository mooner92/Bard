# 프롬프트 작법 — 사람이 직접 쓸 때의 기준

트리트먼트의 `visual`·`anchor`·`palette`·`motion` 을 사람이 쓸 때 보는 문서.
서사(무슨 이야기를 고르는가)는 [NARRATIVE.md](NARRATIVE.md), 모델 설정과 파이프라인
동작은 [PIPELINE.md](PIPELINE.md)에 있다. 여기는 **그 이야기를 그림과 움직임으로
옮기는 법**만 다룬다. 흩어져 있던 규칙([PIPELINE.md](PIPELINE.md) 스타일 블록,
[PLAN.md](PLAN.md) 모션 금지어, [SPEC.md](SPEC.md) 자막 기준)을 작법 관점으로 모았다.

대상은 키프레임 Qwen-Image, 클립 WAN I2V. 근거는 전부 이 저장소에서 실측한 성공·실패다.

## 1. 사례

### 통과한 것

| 사례 | 무엇이 좋았나 |
|---|---|
| 운수 좋은 날 | 여덟 컷이 한 지점(집 문)으로 모이고 마지막이 문턱에서 멈춘다 |
| 위대한 개츠비 앵커 | 인물 묘사 한 문장을 여덟 컷에 그대로 붙여 같은 사람이 유지됐다 |
| 영어 프롬프트 전환 | 가짜 한글 자막이 한 번에 사라졌다 |

### 떨어진 것 (전부 실측)

| 증상 | 원인 | 교훈 |
|---|---|---|
| 화면 상단에 뭉개진 한글 | 한국어 문장을 그대로 프롬프트로 넘김 | 프롬프트는 영어로만 |
| 사이렌이 확성기로 그려짐 | 소리를 사물처럼 적음 | 카메라가 못 보는 것은 몸짓으로 번역 |
| 1930년대 경성에 미국 달러 지폐 | 시대 사물을 명시하지 않음 | 화폐·의복·조명·탈것을 못 박는다 |
| 컷마다 딴 사람 | 앵커 없이 장면마다 새로 묘사 | 앵커는 여덟 컷에 **같은 문장** |
| 총이 개츠비를 겨눔 | 박자는 멈췄는데 visual 이 결말을 그림 | 그림도 문턱에서 멈춘다 |
| 크롭 6%→16%→적응형 전부 실패 | 자막이 생기는 원인을 안 없애고 잘라내려 함 | 증상이 아니라 원인 |

## 2. 특징 — 잘 된 프롬프트의 공통점

**카메라가 볼 수 있는 것만 쓴다.** 소리·감정·개념은 그려지지 않는다. 사이렌은
"siren" 이 아니라 *a man running with his mouth open, shoulders thrown back* 이다.
불안은 "anxious" 가 아니라 *a hand pressed flat against a coat pocket* 이다.

**이름 대신 물질을 쓴다.** "가난한 방"은 아무것도 지시하지 않는다.
*newspaper pasted over the wall, a chipped enamel bowl, one bare bulb* 는 지시한다.
모델은 형용사보다 명사와 재질에 반응한다.

**시대를 사물로 못 박는다.** 연도만 적으면 모델은 현대를 그린다. 화폐·신발·조명
(등불인지 전구인지)·탈것을 하나씩 적어야 그 시대가 된다. 달러 지폐 사고가 이걸
안 해서 났다.

**앵커는 복사해 붙인다.** 인물은 나이·체격·머리·옷 네 가지로 고정하고 여덟 컷에
글자 하나 바꾸지 않고 넣는다. 한 단어만 달라져도 다른 사람이 나온다.

**한 컷에 주체는 하나.** 둘 이상 넣으면 얼굴이 뭉개진다. 상대가 필요하면
뒷모습·그림자·손만 넣는다.

**글자를 부르는 물건을 넣지 않는다.** 간판·포스터·액자·편지·표지가 보이는 책.
화면에 있으면 모델이 글자를 지어내 써넣는다. 부정 프롬프트로 막는 것보다 애초에
안 부르는 쪽이 확실하다.

**움직임은 하나만 지정한다.** 같은 문장을 여덟 번 쓰면 여덟 컷이 똑같이 흔들린다.
그 컷에서 실제로 움직이는 것 하나를 적는다 — 빗줄기, 바퀴, 촛불, 커튼, 어깨의
오르내림. `slowly` · `gently` · `drifts calmly` 는 쓰지 않는다([PLAN.md](PLAN.md)의
금지어) — 뚜렷한 동작 하나가 있어야 화면이 산다.

**움직임에는 진행 방향을 적는다.** I2V 는 정지 그림에 움직임 문장으로 동작을 붙이는데,
방향을 말하지 않으면 아무 쪽으로나 움직인다(실측: 언덕을 오르는 그림에 "근육이 뭉쳤다
풀리고, 썰매가 자갈을 긁는다"만 적었더니 말이 내려오는 영상이 나왔다). 오르는지 내려오는지,
다가오는지 멀어지는지를 *up the slope*, *toward the camera* 처럼 못 박는다.

**결말은 그리지 않는다.** 박자 텍스트가 문턱에서 멈춰도 visual 이 다 보여주면 같은
위반이다. 흉기가 사람을 겨누는 구도, 죽음, 시신, 피는 쓰지 않는다.

## 3. 첫 문장은 첫 박자를 가리켜야 한다

`n`번째 문장을 들을 때 화면에 뜨는 것은 `n`번째 박자다. 그런데 첫 문장은 사람을
붙드는 훅이라 자칫 이야기 전체의 전제를 말하게 되고, 그러면 둘째 문장이 첫
박자를 설명하면서 **여덟 컷이 통째로 한 칸씩 밀린다**. 소공녀에서 "석탄 통을
안고 계단을 오르내린다"는 문장에 다락방 그림이 떴다. 실측으로 네 편이 이렇게
밀려 있었다(소공녀·심청전·홍길동전·십오 소년 표류기).

훅이면서 첫 박자이기도 하게 쓴다. 춘향전이 안 밀린 이유가 이것이다 —
"그네를 한 번 뛰었을 뿐인데, 이 처녀의 앞날이 통째로 달라져 버립니다"는
사람을 붙들면서 동시에 첫 박자(그네)를 가리킨다.

| 밀리는 훅 | 안 밀리는 훅 |
|---|---|
| 부유하게 자란 이 소녀는, 하루아침에 다락방으로 쫓겨나게 됩니다 | 값진 옷차림으로 이 학교에 들어선 소녀는, 곧 모든 것을 잃게 됩니다 |

## 4. 배역 — 두 사람 이상이 나올 때

앵커는 **주인공 한 사람**을 적는 자리다. 두 번째 인물이 나오는 컷에서 그를 적을
칸이 없으면 모델은 화면의 유일한 인물 묘사, 곧 앵커를 그 사람에게도 입힌다.
춘향전 S3 의 `a young couple facing each other` 는 이도령을 특정하지 않았고,
결과는 댕기머리 처녀 둘이 마주 앉은 그림이었다. 같은 작품 S5 의 사또는 묘사가
아예 없어서 '조선 관리'로 인터넷에 가장 흔한 그림, 곧 **임금**이 되었다 —
붉은 곤룡포에 원형 금색 보. 원형 보는 임금 전용이고 고을 수령은 사각 흉배다.

그래서 박자마다 `cast` 로 그 컷에 있는 인물·장소를 열거하고, 생김새는
[works/personas.json](../works/personas.json) 에서 가져온다. 작품 전용 배역은
트리트먼트의 `personas` 에 적는다(같은 열쇠면 그쪽이 이긴다).

```json
{"n": 5, "cast": ["joseon_sato", "joseon_cheonyeo", "joseon_gwana"],
 "visual": "a heavyset official seated on a magistrate's platform looking down at a kneeling girl"}
```

`cast` 가 있으면 앵커 대신 그것을 쓴다 — 주인공도 `cast` 에 함께 적기 때문이다.
사람이 없는 컷은 `"cast": []` 로 두면 아무도 들어가지 않는다(옛 작품의
`anchor: false` 와 같은 뜻).

배역을 적을 때:

- **성별을 반드시 박는다**(man / woman / boy / girl). 빠지면 앞 인물을 따라간다.
- 신분 표식은 모양까지 적는다 — 사각 흉배인가 원형 보인가. 무늬도 적는다(문관은 학).
- **개념어를 쓰지 않는다.** 2절의 규칙이 배역에도 그대로 걸린다. 심봉사를
  `blind` 로 적었더니 모델이 검은 안대를 씌웠다 — 눈이 머는 것은 상태이지
  카메라가 보는 물건이 아니다. `pale unfocused eyes` 처럼 보이는 것으로 바꾼다.
- 사람은 16~20단어, 장소는 10~12단어. 한 컷에 셋이 겹치면 480자에서 뒤가 잘린다.
- `avoid` 는 사람이 읽는 메모다. 프롬프트에 넣지 않는다 — "~를 그리지 마라"라고
  쓰면 모델이 오히려 그것을 그린다.

## 5. 서식

```
visual   영어 12~22단어. 카메라가 보는 것. 쉼표로 끊은 조각들.
cast     그 컷에 있는 인물·장소의 배역 열쇠 목록. 빈 목록이면 사람 없음.
anchor   (cast 이전 방식) 영어 10~18단어. 인물 + 장소. 여덟 컷 동일.
palette  영어 8~14단어. 빛의 방향과 색온도.
motion   영어 6~14단어. 그 컷에서 움직이는 것 하나(+필요하면 카메라).
```

`visual + (cast 묘사 또는 anchor) + palette` 를 이어 붙여 480자에서, 그것도
쉼표 경계에서 자른다(`scene_prompt.py`). 낱말 중간이 잘리면 모델이 엉뚱하게 읽는다.

**팔레트와 화풍 블록에는 사물을 적지 않는다.** 이 둘은 여덟 컷 **전부**에 붙기
때문에 여기 적은 물건은 모든 장면에 나타난다. 흥부전 화풍에 `giant gourds` 를
적었더니 여섯째 박자의 반전이어야 할 박이 첫 컷부터 지붕에 매달렸다. 심청전의
`thatched huts` 는 바다 한가운데 컷에 초가를 세울 참이었다. 이 자리에는 화풍과
빛·색만 적는다 — `straw gold, hanji cream, autumn ochre, warm flat washes`.
그 컷에만 있어야 할 물건은 `visual` 에, 사람과 장소는 `cast` 에 적는다.
화풍 블록은 큐가 앞에 따로 붙이므로 여기 다시 쓰지 않는다.

## 6. 쓰지 않는 말

`beautiful` · `masterpiece` · `8k` · `highly detailed` — 화면을 바꾸지 않고 자리만 먹는다.
`sad` · `lonely` · `tense` — 감정은 그려지지 않는다. 자세와 빛으로 바꿔 쓴다.
`text` · `sign` · `letter` · `book cover` — 부정 프롬프트에 이미 있고, 긍정에 쓰면 부른다.
인물 이름 — 모델이 모른다. 생김새로 적는다.

## 7. 상세 작법 (정식 — 해와 달이 된 오누이로 검증)

짧은 프롬프트는 모델에게 재량을 넘긴다. 재량은 반복·딴짓·엉뚱한 소품으로
돌아온다(실측: "sand streams past the boulder, the man's robe snaps, the crack
widens" 같은 세 절 나열이 대충 반복되는 화면을 냈다). 분량을 다음 기준으로 올린다:

```
배역(주역)   영어 700~1000자  얼굴·체격·머리·옷의 재질과 매듭까지, 자세의 버릇까지
배역(장소)   영어 400~600자   재료·구조·빛이 새는 곳
그림(visual) 영어 800~1000자  구도(프레임 어디에 무엇), 자세, 재질, 빛의 방향, 원경
움직임       영어 800~1000자  아래 규칙 (09-10 A/B 로 300~400 에서 올림 — §7 끝 '동작 프롬프트 길이')
```

**움직임 규칙 — 한 동작의 시작→끝을 서술한다:**

1. 동작은 **하나**. 그 동작이 일으키는 물리 연쇄(옷자락·먼지·그림자)는 그 동작의
   일부로 이어 쓴다 — 별개 동작을 나열하는 것과 다르다.
2. 시작 상태 → 진행 → 끝 상태가 한 문장 흐름으로 이어져야 한다. 나열("A, B, C")은
   모델이 셋을 무작위로 반복한다.
3. 움직이지 않는 것을 긍정문으로 못 박는다: *the rest of the scene holds still*.
4. 카메라는 마지막에 한 절: *camera fixed* 또는 *drifting slowly backward*.
5. 지속형으로 — 순간 동사(drop·snap·burst)는 2절 규칙 그대로 금지.

해와 달이 된 오누이로 검증됐다(실측: 문 앞의 호랑이 컷에 적은 소품 — 두드릴
높이의 앞발·한지 창의 등잔 불빛·처마 밑 장작·섬돌 — 이 전부 그림에 들어왔고,
참기름 컷에는 기름 줄기와 발톱 자국까지 나왔다). SPEC §6 이 이 절을 규격으로
가리킨다.

**원전 근거 파일.** 새 작품은 쓰기 전에 원문(정본 계열)의 인물·장소 묘사를
`works/handwritten/<작품>/source_notes.md` 로 수집한다 — 판본, 인물 묘사 대목,
지물·장소의 원전 표현. 페르소나의 모든 구체 사항은 이 파일에 근거를 둔다.
알려진 화면에 작게 잡히는 인물은 상세 묘사를 덜 받는다(실측: 나무 위 오누이가
만화체로 뭉개졌다) — 그런 컷은 구도를 당겨 인물을 키운다.

**소품 번짐.** 한 인물의 특징 소품은 곁 인물의 빈 슬롯으로 옮겨붙는다(실측:
빨간 모자가 어머니 머리에도 씌워졌다). 곁 인물의 같은 부위를 명시해 슬롯을
채운다 — 어머니에게는 흰 머릿수건을 적어 준다.

**부위는 소유자와 한 절에.** 클로즈업에서 신체 부위를 주인 없이 나열하면
모델이 부위를 아무 데나 붙인다(실측: 빨간 모자 — 'two tall grey ears' 가
소녀 머리에 돋고, 'one amber eye' 가 베개의 털뭉치에 박혔다). 반드시
the wolf's ears / his amber eye 처럼 소유자를 같은 절에 붙인다.

**가장자리 부분 등장 금지.** '화면 끝에 부리만 살짝' 류의 묘사는 공중에 뜬
잘린 부위로 그려진다(실측: 미운 오리 — 실물 부리 하나가 거대한 백조 머리로
떠올랐다). 프레임에 들이는 인물은 어깨선 이상, 몸의 맥락과 함께 넣는다.

**뒷모습은 얼굴 방향을 명시.** 등지고 걷는 컷에서 모델은 얼굴을 보여 주려고
고개만 카메라로 돌린다(실측: 브레멘 — 고양이 몸은 멀어지는데 얼굴이 정면,
영상에서는 뒤로 걷는 것처럼 보인다). back of head to camera, head held
straight ahead 를 시각·움직임 양쪽에 적는다.

**조립 예산 1900자.** 영상·이미지 모델의 텍스트 창은 UMT5 512토큰(영문 약
2000자)이다. 2600자로 조립하던 동안 두 번째 인물 묘사가 반쯤 잘리고 화풍이
창 밖으로 밀렸다. scene_prompt 는 배역을 앞 340자(쉼표 경계)만 싣는다 —
그래서 **배역 첫 340자에 실루엣·복색·머리쓰개 핵심을 몰아 쓴다.** 전문
700~1000자는 사전(뒷부분 = 버릇·소지품·이력)이다.

**같은 인물은 같은 명사로.** 배역 사전과 컷 묘사가 한 인물을 서로 다른
명사로 부르면 모델이 두 인물로 그린다(실측: 미운 오리 — 사전은 grey cygnet,
컷은 grey duckling → 웅덩이 안에 새끼가 헤엄치는데 눈밭에 오리가 한 마리 더
서 있었다). 사전 첫 명사와 컷의 호칭을 일치시킨다.

**부재 인물의 명사를 쓰지 않는다.** 화면에 없어야 할 인물의 이름은 그
인물을 소환한다(실측: 'grandmother's nightcap' 한 마디에 침대에 할머니가
누웠다). 소유는 풀어 쓴다 — a white ruffled lace nightcap.

**배역 머리에 자세 동사를 쓰지 않는다.** 사전의 자세와 컷의 자세가 다르면
같은 인물이 두 자세로 두 번 그려진다(실측: 사전 standing + 컷 lying →
침대 늑대 옆에 서 있는 늑대가 하나 더). 자세는 컷이 정한다.

**장소 배역은 실내·실외를 가른다.** 앞 340자만 컷에 실리므로 실외 우선으로
쓴 장소 사전은 실내 컷에 바깥을 끌고 들어온다(실측: 침실 컷의 창밖이 아니라
방 안에 숲이 자랐다). cottage/room 처럼 두 배역으로 나눠 컷마다 맞는 쪽을
cast 에 넣는다.

**중요 소품에는 규격 문장을 준다.** 배역만 사전에 두고 소품을 컷마다 다르게
부르면 형태가 매번 달라진다(실측: 금도끼가 자루 긴 미늘창이 되었다 — 'a
golden axe, broad and mirror-bright' 에는 자루 길이가 없다). 반복 등장
소품은 배역처럼 한 문장 규격을 정하고 **모든 컷에 같은 말로** 넣는다:
"a Korean woodcutter's axe of solid gold, its short thick wooden haft no
longer than a forearm and its head a broad heavy wedge".

**들어 보이는 동작은 '이미 들려 정지'로 적는다.** arc·turning·sweeping·
wheeling 같은 궤적어는 궤적을 그리라는 지시로 읽힌다(실측: 신령이 도끼를
머리 위로 휘둘렀다 — 원문은 'lifts in one slow steady arc… holds it there
turning slightly'). 보여 주는 물건은 already raised, stays completely
motionless … for the whole shot 으로 못박고, 그 컷에서 움직이는 것은
사람뿐임을 한 절로 밝힌다(only the man moves).

**직유는 전면 금지다.** 'like a X' 의 X 는 그려진다 — 한 작품에서 여섯 컷이
직유로 무너졌다(실측: like a minister 가 관모 쓴 사람을 세웠고, calligrapher's
brush 가 인두를 붓으로 바꿨고, calligraphy strokes 가 비단에 글씨를 새겼고,
boatman's pole 이 장대 든 사람을 불렀고, needle's eye 가 바늘꽂이에 눈알을
그렸고, gentlewoman's shadow 가 부인 본체를 소환했다). 물리 묘사만 쓴다.
전문어도 검사한다 — 바늘귀는 eye 가 아니라 threading hole 로 적는다.

**동음이의어도 소환한다.** deep formal bow(절)가 소년의 손에 활(bow)을
쥐여 줬다(실측: 서동 S7). 절은 lowered head, bent waist 로 풀어 쓴다.
모델이 모르는 사물(호미)은 뜻이 가까운 흔한 사물(삽)로 표류한다 — 그릴 수
없는 도구는 언급 자체를 뺀다.

**빛의 비유어도 사물을 소환한다.** moonish·sunlit 같은 말은 그 천체를
화면에 불러온다(실측: 한낮 컷에 초승달이 떴다 — 'a pale moonish sheen').
빛은 비유 대신 성질로 적는다 — a pale cold sheen, thin winter light. 빛의
색도 마찬가지다: 'the pea glowing faintly amber' 는 완두콩을 유리장 속
촛불로 바꿨다(실측: 공주와 완두콩 S14 — amber glow = 이 팔레트의 촛불).
사물이 빛을 받는 것은 lit pale green 처럼 그 사물의 색으로 적는다.

**직업명 속 동물은 얼굴에 섞인다.** 'swineherd' 가 돼지 옆에서 웅크리거나
절하는 컷에서 돼지 주둥이 얼굴이 되었다(실측: 돼지치기 왕자 7·12 — 선 자세
다섯 컷은 멀쩡했다). 동물 곁의 인물은 자세를 세우고 'his sooty human face'
처럼 사람 얼굴을 한 절로 못박으며, 동물은 뒤쪽으로 물린다.

**이야기의 주제어가 색을 사물로 바꾼다.** 금을 찾는 이야기에서 'yellow earth'·
'yellow spoil' 은 삽 위의 금덩이가 되었고(실측: 금 따는 콩밭 6·7), 'a red
furious face' 는 얼굴 전체를 칠한 붉은 가면이 되었다(같은 작품 7). 흙은
reddish-brown 으로, 분노는 'jaw set, eyes narrowed' 처럼 근육으로 적는다.

**재료 이름 속 동물도 온다.** 'hog's leather' 벽지가 벽에 돼지 머리 둘을
걸었다(실측: 낡은 집 7). 재료는 색과 무늬로 적는다 — dark stamped leather.
**장난감의 축척은 말로 안 잡힌다.** 'a small pewter toy soldier' 가 소년만 한
병정으로 서 있었다(실측: 낡은 집 4·8). 'figurine', 'a child's toy', 'standing on
top of the chest of drawers' 처럼 종류와 놓인 자리로 크기를 못박고, 사람 곁에
두는 컷은 가구 위에 올린다.

**자산 머리의 자세 동사는 컷의 자세와 충돌해 개체를 둘로 가른다.** 메뚜기
자산에 'standing upright' 를 두고 컷에 'sits alone' 을 적자 서 있는 제복 사람과
앉은 곤충이 함께 그려졌다(실측: 뜀뛰기 선수들 12, 같은 이유로 1). 자산엔
생김새만, 자세는 컷에만 — 규칙을 스스로 어긴 값이다.

**동물에 입힌 옷은 사람 몸을 부른다.** 벼룩에 'tailcoat' 를 입히자 꼬리 달린
신사가 되었고, 'knapsack' 은 등에 업힌 딱정벌레가 되었고, 메뚜기의 'uniform'
은 제복 입은 사람 하나를 더 세웠다(실측: 뜀뛰기 선수들 1·3·11·12 — 옷이 없는
개구리는 매번 멀쩡했다). 의인화가 목적이 아니면 옷은 크라바트 하나까지만
적고 몸은 'a plain insect, six thin legs' 처럼 동물의 해부로 못박는다.

**맨살에 붙인 색은 옷이 된다.** 'bare feet red with cold' 가 빨간 양말을,
'reddened fingers' 가 빨간 장갑을 신기고 끼웠다(실측: 성냥팔이 소녀 2·3·4·5 —
bare 라고 적어도 소용없었다). 추위·상처는 색이 아니라 pale·cold·stiff·
chapped 같은 상태로 적는다(check_craft BODY_COLOUR).

**구조·지형 비유 명사는 그 지형을 세운다.** 'bedding tower' 가 창밖에 돌
망루를 세웠고, 'striped cliff of mattresses' 가 침실 안에 절벽을 들였고,
'cloud upon cloud' 와 'soft mountain' 이 요 아래 구름과 창밖 설산을
깔았다(실측: 공주와 완두콩 6·7·8 — 세 컷 전부). 스무 장 요는 'a tall
striped stack of twenty mattresses' 다. tower·cliff·mountain·cloud·sea·
river·forest·waterfall·island·cave 는 자산 파일이나 setting 에 실물로
있을 때만 쓴다(check_craft METAPHOR 가 잡는다).

**팔레트의 색 이름이 사물이면 그 사물이 온다.** 팔레트 'rose pink' 와
배역의 'rose gown' 이 여섯 컷 구석마다 장미 덤불을 심었고, 마지막 유리장
속 완두콩 깍지에서 장미가 피었다(실측: 공주와 완두콩). rose·cherry·peach·
lemon·coral 같은 색은 dusty pink·pale red 처럼 색 이름으로만 적는다
(check_craft COLOUR_THING). plum 은 실측상 무해했다(자두가 온 적 없음).
'snow white' 도 사물이다 — 응접실 카펫과 다락 바닥, 봄 마당에 눈이 깔렸다
(실측: 전나무 8·10·11·12·13·14). 겨울 이야기라도 팔레트엔 white 만 적고
눈은 눈이 있는 컷에만 적는다. ice·frost 도 같다.
빛 이름도 같다 — 팔레트 'candle amber' 는 궁전 컷에선 촛대로 얌전히 앉지만,
**초점 자리가 빈 컷**(유리장 속 완두콩 한 알)에서는 그 자리에 촛불을 세운다
(실측: 공주와 완두콩 S13 — 텍스트에 촛불이 없는데도 두 번 연속). 광원은
팔레트가 아니라 그 광원이 있는 컷에만 적고, 팔레트엔 색 이름(amber)만 남긴다.

**수는 위치로 배분한다.** 숫자만 적으면 수가 흐른다(실측: '두 아이'가
셋이 되었다 — 하나는 안기고 둘은 바닥에 서 있었다). 명수가 중요한 컷은
자리를 하나씩 배정한다 — the boy seated on her left arm, the girl on her
right arm — 그리고 나머지 공간이 비어 있음을 한 절로 적는다.

**자리 못박기.** '침대 속 A 와 곁에 선 B' 구도는 뒤집힌다(실측: 이불 속에
소녀가 눕고 늑대가 곁에 앉았다). 구도의 첫 절에서 두 인물의 자리를 각각
못박고(A is the one lying inside the bed / B stands on the floor), 이불·모자
같은 소유 소품을 인물과 붙여 반복한다.

**원전 우선.** 배역·장소·소품은 우리가 짓는 것이 아니라 **원전에서 옮겨 오는
것**이다. 쓰기 전에 원문(또는 정본 계열 판본)의 묘사를 찾아, 나이·생김새·옷·
지물은 책이 말하는 대로 적는다(실측: 홍길동을 임의로 열여섯 소년으로 잡았다가
원전과 어긋났다). 원전이 침묵하는 부분만 시대 고증으로 채우고, 그때도 원작의
결을 벗어나는 창작은 하지 않는다. 작품 조사 단계에서 인물 묘사 대목을 함께
수집해 페르소나의 근거로 남긴다.

**직업명은 제복을 부른다.** 'sailor' 가 이슈메일에게 세일러 칼라와 금단추를 입혔고,
'captain' 이 에이해브의 챙 넓은 모자를 정모(peaked cap)로 바꿨다(실측: 모비딕 1차
S3·S4·S7). 인물은 생김새와 옷으로만 부른다 — the young man in the black knitted cap,
the old man in the wide flat-brimmed hat. 제복이 목적일 때만 직업명을 쓴다.

**빈 머리 슬롯은 곁 사람의 모자를 끌어온다.** 퀴퀘그(모자 없음)가 이슈메일의 털모자를
쓰고 나왔고, 이슈메일은 대신 정모를 받았다(실측: 모비딕 S3·S4 — 이슈메일이 모자를
벗은 컷에서 더 심했다). 모자 없는 인물은 머리를 긍정문으로 채운다 — his shaved scalp
bare except for a single tall topknot — 그리고 곁 인물의 모자는 컷마다 머리에 둔다.

**보철은 신체가 아니라 물건으로 적는다.** 'his right leg below the knee a white peg of
polished whale ivory' 가 상처 난 맨다리(S6)와 돛대에 기대 놓은 상아 조각(S7)이 됐다.
'in place of his right lower leg a smooth tapered peg of polished whalebone ending in a
blunt rounded tip' 처럼 자리(in place of)·형태(post)·끝(blunt tip)을 적고, 발이 없음은
긍정문(a plain smooth post)으로 둔다.

**장대 + 밧줄 = 활.** 작살 자산의 'a coil of thin rope spliced to its iron shank' 이
활시위가 되어 퀴퀘그가 장궁을 들었다(실측: 모비딕 S4 — 서동의 bow 와 같은 뿌리).
긴 자루 소품에는 줄을 붙이지 않는다; 줄이 꼭 필요한 컷에서만 rope 라고 따로 적는다.

**종 이름은 그 종을 소환한다.** 'whaling ship', 'whaleboat', 'whalemen', 'whale teeth'
가 낸터킷 항구에 만화 고래를 띄웠다(실측: 모비딕 S5). 동물 이름이 든 합성어는 동물이
나올 컷에만 쓰고, 나머지 컷은 old three-masted ship / narrow off-white boat / crewmen /
pointed ivory teeth 로 푼다.

**난간 장식은 난간이 된다.** 'whale teeth along the rail' 이 갑판 컷에서 흰 발루스터
난간으로 바뀌었다(S6·S7 — 선체 밖 컷 S5 에서는 이빨로 잘 나왔다). 갑판 컷은 solid
dark wooden bulwark waist-high 로 적고 이빨은 그 위에 얹는다.

**문신·흉터 같은 피부 무늬도 곁 사람에게 번진다.** 퀴퀘그의 볼 문신 사각이 이슈메일의
볼과 목에도 찍혔다(실측: 모비딕 2차 S5). 무늬 있는 인물 곁의 인물에게는 his own face
plain and unmarked 처럼 빈 피부를 긍정문으로 채운다 — 머리 슬롯 규칙과 같은 뿌리.

**절단·보철은 전신 컷에서 그려지지 않는다.** 자리·형태·끝을 물건으로 적어도(위 규칙)
모델은 다리 둘에 부츠를 신기고 뼈를 갑판·돛대에 따로 놓았다(실측: 모비딕 2차 S6·S8·S9
— 세 번 연속). 보철은 **자산에서 빼고**, 전신 컷은 허리·가슴 위로 잘라 다리를 프레임
밖에 두며, 보철이 이야기의 요점인 컷 하나만 다른 다리가 들어올 수 없는 극단 클로즈업
(구멍에 박힌 흰 기둥 + 외투 자락)으로 만든다.

**크기 형용사는 물건을 키운다.** 'a single large gold coin' 이 방패만 한 금화가 되었다
(실측: 모비딕 S8·S9). 크기는 비교 대상으로 적는다 — the size of a man's palm — 그리고
'small against the thick mast' 처럼 곁 물건과의 비율을 한 절 더 둔다.

**팔은 한 팔씩 자리를 못박는다.** 'both hands gripping the hoop rim, his body leaning far
out' 이 두 팔을 머리 뒤로 꺾인 자세로 그렸다(실측: 모비딕 3차 S14 — 검수도 통과시켰다가
사용자가 잡았다). 두 팔이 다 보이는 컷은 his left hand at his hip on the rail / his right
arm stretched out level at shoulder height 처럼 팔마다 높이와 방향을 적고, elbows unbent /
both shoulders level 같은 관절 상태를 한 절 더 둔다. **키프레임 검수 항목**: 글자·소환·정체
말고도 팔다리 관절 방향, 손·발 개수, 목·허리 꺾임을 본다.

**부정 접미사도 소환한다.** 'moonless' 가 달을 띄웠다(실측: 모비딕 S13). 없는 것은 말하지
않는다 — a deep-blue night sky with small pale stars. **비유 단위도 물건이다.** 'palm-sized'
가 금화에 야자수를 새겼다(S15). 크기는 as wide as three fingers 처럼 손가락·손·팔 길이로
적되 palm 은 쓰지 않는다. **먼 물보라 한 줌은 가까운 물건에 붙는다.** 수평선의 'a small
bushy plume of white spray' 가 보트 뱃머리에서 솟는 증기가 되었다(S11) — 가리키는 손짓만
남기고 먼 물체는 뺀다.

**'둘이 함께 서 있다'는 한 사람이 된다.** 'the cobbler and the wife are the two standing
together by the stove' 가 머릿수건을 쓴 수염 난 인물 하나로 합쳐졌다(실측: 톨스토이 S14).
곁에 선 두 사람은 자리 못박기 규칙대로 각자 한 절씩(누가 난로 쪽, 누가 그 왼쪽 반 걸음
앞) 적고 'two separate grown people side by side' 를 덧붙이며, 수염 없는 쪽에는 smooth
round chin 처럼 빈 턱을 채운다.

**날씨는 실내로 들어온다.** 배경 자산의 'rainy morning light, the panes streaked with water'
가 방 안 전체에 빗줄기를 그렸다(실측: 변신 S1). 실내 컷의 배경 자산에는 빛의 성질만 적고
(weak grey light, misted panes) 비·눈·바람 같은 날씨 낱말은 실외 컷에만 둔다.

**'shop' 은 간판을 단다.** 'low tile-roofed shops with plain wooden shutters' 가 가게
앞에 한자풍 간판을 걸었다(실측: 운수 좋은 날 S4 — 'bare of lettering' 을 적어도 소용없다).
거리는 houses with closed shutters and bare plaster walls 로 적고 shop·store·market 은
간판이 목적일 때만 쓴다. 큐의 다른 작품에서도 shop 낱말을 훑어 바꿀 것.

**한 자산에 여러 인물 유형을 적으면 다 나온다.** 손님 자산에 마님·학생·신사를 'each one
at a time' 이라 적어도 한 컷에 둘씩 탔다(실측: 운수 좋은 날 S5·S6). 번갈아 나오는 인물은
자산을 따로 만들고 컷마다 하나만 cast 하며, 'the seat beside him is empty' 처럼 빈자리를
긍정문으로 적는다.

**'wine' 은 포도주 잔이다.** 주모 자산의 'a wine ladle' 이 1930년대 봉평 주막에 붉은 포도주가
든 유리잔을 들렸다(실측: 메밀꽃 S2). 막걸리는 milky rice wine 도 위험 — rice liquor / a
wooden bowl of milky liquor, 술항아리는 earthen jars 로 적고 wine 낱말은 서양 작품에만 쓴다.
- **나무 종 이름은 열매를 소환한다.** "a bare persimmon tree" 라 적어도 주홍 감이 주렁주렁
  달린다(실측 09-10: 봄봄 S1, 동백꽃 S4·S5·S10 — 봄 이야기에 가을 감). 잎 없는 나무는
  "a bare-branched tree" 처럼 종 없이, 열매·꽃이 필요할 때만 종을 부른다.
- **"forked staff" 는 쇠스랑이 된다.** 지게 작대기를 "stout forked wooden staff" 라 적자 세 갈래
  쇠스랑을 들었다(09-10 봄봄 S12). 갈래·가지 말 없이 "a stout straight wooden staff" 로.
- **같은 화면의 두 남자는 한 몸으로 합쳐진다.** 장인+머슴이 선 채로 나란히 있으면 두루마기에
  머리띠를 두른 한 사내가 된다(09-10 봄봄 S10·S13·S14 세 번). 사람마다 자세를 다르게(하나는
  무릎 꿇고 하나는 서고), 갓·머리띠·수염을 사람 이름 옆에 다시 붙이고, 끝에 "only the
  father-in-law has a beard" 처럼 **한 사람만 가진 특징을 못박는다**. 소품(담뱃대)도
  "tucked in his own belt" 처럼 임자를 적지 않으면 다른 사람 입으로 옮겨 간다.
- **동작 프롬프트 길이 — 800~1,000자, 시간표 구조.** 사용자 지적(09-10 "그림은 자세한데 동작은
  짧다, 늘리면 잘 나올 것")으로 동백꽃 S2·S11 을 같은 키프레임·seed 42 로 284자↔1,111자,
  266자↔1,050자 A/B. I2V 모델은 그림 프롬프트를 전혀 보지 않고 키프레임+동작 텍스트만 받는다.
  결과: S11(작대기 내려놓기) 짧은 쪽은 5초 내내 작대기를 휘두르고(4구간 움직임 2.1/1.45/1.98/2.0),
  긴 쪽은 첫 1.5초에 내려놓고 멈춘다(2.42/1.61/1.04/0.92) — 적은 대로 됐다. S2 도 움직이라는 소녀
  쪽은 1.27→1.91, 그대로 있으라는 소년 쪽은 1.15→0.94. 늘리되 **동작은 여전히 하나**. 구조:
  ① 누가 유일하게 움직이는가(인물을 옷·머리로 다시 명시) ② "at the start … / over the first two
  seconds … / in the last two seconds …" 시간표로 시작→진행→끝 ③ 그 동작의 물리 연쇄(김·먼지·
  머리채·옷자락) ④ 움직이지 않는 사람은 부위별로("his gripping hand on the strap not moving,
  no step, no head turn") ⑤ 배경 사물 목록 holds completely still ⑥ "no new figures or objects
  appear" ⑦ "camera fixed, no zoom, no drift". 실측 클립: scratchpad `ab_motion/`.
- **걷는 컷은 카메라가 따라간다.** 봄봄 S1 을 긴 프롬프트로 "plods steadily toward the low wooden
  gate" 라 적자 WAN 이 머슴을 따라 카메라를 움직여 장인이 프레임 밖으로 나가고 없던 대문이
  들어왔다(프레임 차 7.5, 같은 키프레임의 옛 305자 프롬프트는 2.5 로 고정). 원인은 길이가 아니라
  **프레임 밖의 목적지를 부른 것 + 5초 내내 걷게 한 것**. 규칙: 걷기는 "over the first three
  seconds … takes two or three slow steps" 로 끊고 "in the last two seconds comes to a stop well
  inside the frame", 목적지는 프레임 안의 것만, 끝에 "the framing does not change at all; camera
  locked off, no tracking". 카메라 쪽으로/멀어지며 걷는 컷도 같은 위험(줌으로 바뀐다). 실측(감자 클립 S3): 카메라 쪽으로 걷는 두 사람은 "몇 걸음 뒤 멈춤" 을 적어도 끝까지 다가와
  프레임 아래로 잘린다(프레임 차 7.4). 카메라를 향한 걸음은 한 걸음으로 줄이거나, 아예 옆으로
  지나가는 구도(왼쪽→오른쪽)로 키프레임부터 짠다.
- **"bearers"(가마꾼)는 곰(bear)을 부른다.** 감자 S1 에 "two bearers at the poles" 라 적자 남편 뒤에
  갈색 곰이 섰다(09-10). 가마꾼은 "two carrier men", 가마는 "no wheels" 까지 적는다(바퀴 달린
  수레로 표류). 낱말 안에 다른 사물 이름이 들어 있으면(bear-ers, horse-hair) 그 사물이 나온다. "watchful" 도 손목시계(watch)를 채웠다(감자 S8) — wary 로. "a heavy silver ring" 같은 장신구는 시대와
  어긋나면 아예 적지 않는다. 부정문도 소환한다 — "no wheels" 라 적자 바퀴 달린 수레가 그대로 왔다(감자 S1 2차).
  없어야 할 것은 이름을 부르지 말고 있어야 할 것만 긍정문으로("resting on two long poles on the ground"). "no wristwatch and no ring" 도 시계·반지를 다시 채웠고(감자 S8 2차), "no tall modern buildings" 도
  빌딩을 다시 세웠다(S4 2차). 검사 항목에서 부정문(no·without·never + 사물)을 금지어로 본다. 자산 상세의 "a folded newspaper never in his hand" 도 글자 박힌 신문을 손에 쥐여 줬다(레디메이드 인생 S1).
- **"bony" 는 뼈를 그린다.** "his long bony hand" 가 해골 손이 됐다(09-11 날개 S2). 마른 손은
  "long thin hand", 손목은 "thin wrist" 로. skeletal·gaunt 도 같은 계열로 조심(gaunt 는 얼굴에만).
- **"department store" 의 store 도 간판 글씨를 부른다**(09-11 날개 S15 — 벽돌 건물에 글자 간판). shop 규칙과
  같다: 건물은 "a 1930s four-storey concrete building" 처럼 용도 없이 재료·층수로만 적는다.
- **사진 속 제복은 사람을 세운다.** "two small framed photographs of young men in dark uniforms" 가
  방 안에 제복 경찰 둘을 세웠다(09-12 태평천하 S6). 사진·그림 속 인물은 "a flat sepia picture of
  one young man's face and shoulders in a plain dark jacket" 처럼 평면·얼굴만으로 적고, 제복·무기
  같은 소환력 큰 낱말은 사진 안에도 쓰지 않는다.

- **'거대한 맨발 자국' 은 발 달린 다리를 부른다 — 'bare feet' 낱말과 긍정문의 'nobody in it' 이 함께 창턱 아래 맨다리 한 쌍을 세웠다**(프랑켄슈타인 S15 세 판): 1판(원문) 'muddy marks of two enormous bare feet … the room is empty of people' → 창 아래 맨다리 두 개가 서 있었다. 2판 'a trail of large dark mud prints, each with five round dots at its front' + 부정어 legs·feet·person → 다리는 사라졌으나 곰 발바닥 같은 자국이 됐고 탁자가 둘로 늘었다. 3판(채택) 'huge muddy footprints, each footprint the long narrow shape of a human sole with a rounded heel and toe marks' + 'the one long wooden table … the only table in the room' + 부정어 legs·feet·person·paw print·animal tracks·two tables → 사람 발자국 열이 창으로 이어졌다. 결: 발자국은 'footprints … human sole' 로 적되 'bare feet' 를 쓰지 않고 legs·feet 를 부정어에 둔다; 사람 없음은 부정문 대신 '방에는 탁자·시트·병·발자국만' 으로 적는다; 'five round dots' 는 짐승 발바닥이 된다.

- **특별석의 명판 'a single plain numeral shape' 은 숫자를 새긴다, 그리고 'gilt box' 는 무대 위 상자가 된다**(오페라의 유령 S4 두 판): 1판은 특별석 앞면에 '2' 명판, 명판 문구를 뺀 2판은 'box' 를 문자 그대로 받아 무대에 노란 궤짝을 세웠다(동음이의 규칙). 결: 숫자를 암시하는 낱말은 쓰지 않고, 숫자 명판은 재생성 대신 **가장자리 crop** 으로 지운다(원본 crop 채택).

- **한 인물의 'black-gloved hands' 는 같은 컷의 다른 인물 손에도 옮겨 붙는다 — 'bare hands, skin showing white' 는 흰 장갑이 된다**(오페라 S6 두 판·S9): 유령 자산의 검은 장갑이 크리스틴 손에 두 컷 연속 나타났고, 부정어 gloves 와 '맨손' 서술로는 흰 장갑으로 바뀔 뿐. 결: 장갑은 자산 spec 에서 빼고(long pale thin hands) 필요한 컷의 visual 에서만 적는다.

- **낱말 안의 낱말 — 'a smooth black skullcap of hair' 의 skull 이 해골 가면을 부른다**(오페라 S9): 매끈한 흰 가면이 눈·코 구멍 난 해골이 됐다. 'hair combed flat to his head' 로 바꾸자 가면이 돌아왔다. 'crown'(왕관)·'cane' 과 같은 결.

- **'black evening dress'(연미복) 는 여성 이브닝 가운을 그린다**(오페라 S14 2판): 가슴이 파인 검은 드레스 실루엣. 'black evening tailcoat and trousers' 로.

- **바닥의 '열린 함정문(a black hole in the lit floor)' 은 배경막의 검은 문이 된다**(오페라 S12): 'a square hatch cut in the floorboards, seen from above at a slant so that its black inside shows below the level of the boards, its four edges lying flat in the floor' 로 적고 부정어에 doorway·door 를 두자 바닥 구멍이 됐다. 옆에 놓인 베일은 'spread flat and loose in a low heap' 으로 — 그냥 'a long white veil' 은 베일 쓴 무릎 꿇은 형체가 된다.

- **'by the underground lake' 는 방 안까지 물을 들인다**(오페라 S14): 인물 발밑에 호수 물이 깔려 떠 있는 듯 보였다. 'its floor of dry grey flagstones running under the feet of all three figures to the bottom edge' + 부정어 water·flooded floor.

- **분장실 거울 앞의 인물은 거울 속에 정면 얼굴로 비친다 — 옆모습과 맞지 않아 딴 사람이 된다**(오페라 S5): '거울은 벽만 비춘다' 는 서술은 듣지 않는다(드라큘라 S5 는 운). 반사를 없애기보다 자세를 바꿔 반사가 환영처럼 읽히게 — 'her cheek and one ear laid flat against the cold glass, her eyes closed, listening' 이 통했다.

- **무대 컷의 '조명' 은 현대식 스포트라이트 열과 마이크 스탠드를 부른다**(오페라 S1): 부정어 microphone stand·spotlight rig·light bar 로 스탠드는 사라지고 조명 열은 작아졌다. 각광(gas footlights)만 적어도 상단 조명이 따라온다.

- **'a great hump on his back' 은 등에 멘 가죽 가방이 된다**(노트르담 S5): 곱사등이 배낭으로 그려졌다. 'a great rounded hump of his own crooked back swelling under his tunic cloth' + 부정어 backpack·satchel·bag 으로 옷 아래 부푼 등이 됐다(자산 spec 도 같이). 이 화풍에서 혹·비뚤어진 얼굴은 어차피 약하게만 나오니 컷 사이 일관성만 지킨다.

- **'the jug of water in the other' 는 물병을 허공에 띄운다**(노트르담 S10): 손이 화면에 없으면 물건만 뜬다. 'the clay jug gripped by its handle in his other big hand, both his arms stretched out toward the bed' 처럼 쥔 손과 팔을 적는다.

- **'guards in steel caps' 만 적으면 19세기 견장 군복이 나올 수 있다**(노트르담 S8 2판): 'the medieval guards in plain steel caps and brown leather jerkins with pikes' + 부정어 epaulettes·military uniform 으로 중세 병사가 됐다. 같은 컷에서 콰지모도가 수염 난 장년이 되는 것도 'his plain young face clean-shaven' + 부정어 beard 로 잡았다.

- **'a paper crown' 은 금관이 된다**(노트르담 S1): 'a crumpled crown cut from dull yellow paper' + 부정어 gold metal crown·jewelled crown 으로 종이 왕관이 됐다.

- **'his smile gone' 은 전원을 웃게 한다 — 체포 컷의 표정은 긍정문으로**(몬테크리스토 S3 세 판): 1판(원문) 은 헌병·당테스·메르세데스 전원 미소. 'his mouth open in alarm, brows drawn up, face gone pale' + 헌병 'mouths shut hard, brows lowered' 로 표정은 잡혔으나 2판은 당테스가 아이 체격, 3판(정면 헌병 둘 + 'a tall grown man as tall as the gendarmes') 은 당테스에게 헌병 견장 군복과 흰 모자가 옮겨 붙음(삼총사 S5 와 같은 색 번짐). 결: 제복 인물 여럿과 마주 선 주인공은 **제복 쪽을 뒷모습으로** 돌리고('seen from behind, their broad dark blue backs and the backs of their tall black hats toward the camera') 주인공 옷은 'plain … with no braid or badge, bareheaded' 로 못박는다 — 4판에서 통과.

- **'a portrait turned to the wall' 은 얼굴 보이는 초상이 된다**(몬테크리스토 S4): 'a gilt picture frame turned round, showing only the plain brown wooden back of its canvas and its stretcher bars, its picture hidden against the wall' 로 적자 뒤집힌 액자가 됐다(자산 spec 도 같이). 같은 컷의 'coal fire' 는 붉은 불꽃이 되기 쉬워 'low coal fire glowing dull orange' + 부정어 red fire.

- **바닥에 긁은 'lines, circles and a triangle' 은 오각별 마법진이 된다**(몬테크리스토 S9): 원과 삼각형의 조합이 펜타그램을 부른다. 삼각형을 빼고 'three plain circles of different sizes in a row with one straight line drawn under them, a geometry lesson' + 부정어 pentagram·magic circle·star shape 로 기하 도형이 됐다. 'nothing on it is a letter' 같은 긍정문 부정어도 함께 뺀다.

- **검은 바다에 '가슴까지 잠긴' 사람은 그려지지 않는다 — 다리가 물속으로 비친다**(몬테크리스토 S14 세 판): 원문 'rising above the black water from the chest up' 은 발까지 다 보이는 얕은 물, 'the flat black surface cutting straight across his chest … hidden in the opaque black water' + 부정어 legs·feet·wading·transparent water 는 허벅지까지 잠기고 발은 감춤(채택), 'swimming, treading water' 는 수면을 가슴에 놓지만 물이 투명해져 다리가 다시 비침. 결: 'opaque black water' + 부정어로 발을 감추는 데서 멈추고, 'swimming' 은 투명한 물을 부르니 쓰지 않는다.

- **땅에 놓인 '빈 망토(a long dark cloak lies spread empty)' 는 망토 입은 사람이 된다 — 'no person is seen' 이 그것을 굳힌다**(바스커빌 S3): 전설의 사냥개 컷에 1640년대 복장의 쓰러진 남자가 나타났다. 'a long dark cloak lies crumpled flat in a low heap on the ground, its cloth folded over on itself like a dropped rag' + 부정문 제거 + 부정어 man·body·corpse 로 빈 천 더미가 됐다(코트→앉은 사람, 시트 아래 형체→자는 사람과 같은 결).

- **한 인물의 'grey cloth cap' 도 같은 컷 다른 인물 머리에 옮겨 붙는다**(바스커빌 S11): 장갑·견장 전이와 같은 규칙. 다른 인물에 'bareheaded with his short brown hair uncovered' + 부정어 two caps·cap on the second man 으로 잡았다. 자산의 'beehive of piled grey stones' 만으로는 흰 회벽 돔이 나오기도 하니 visual 에 돌을 다시 적는다.

- **작은 얼굴의 'thick brown moustache' 는 턱수염으로 번지고 'clean-shaven cheeks' + 부정어 beard 로도 안 잡힌다**(바스커빌 S6 두 판·S7·S9·S10): 인물이 화면의 1/4 이하로 작으면 콧수염만 그릴 해상도가 없다. 컷 사이 일관성 문제로만 보고 허용하거나, 얼굴을 크게 잡는 컷에서만 콧수염을 기대한다.

- **'a hound the size of a small pony' 는 갈기와 발굽 달린 말이 된다**(바스커빌 S14 2판): 크기 비유의 동물이 그대로 그려진다(동음이의·비유 소환 규칙). 'a dog with a dog's long muzzle and drooping hound's ears, its back as high as a man's waist' + 부정어 horse·pony·mane·hooves 로 개가 됐다(자산 spec 도 같이). 크기는 사람 몸의 높이로 잰다.

- **'the violin case lies open on the shelf' 는 두 번째 바이올린을 그린다 — 그리고 같은 소품을 자산과 visual 에 두 번 적으면 둘이 된다**(주홍색 연구 S4 세 판): 열린 케이스에 바이올린이 그려져 연주 중인 것과 둘이 됐고, 'closed black violin case lying flat' 을 자산과 visual 양쪽에 적자 케이스가 둘이 됐다. 소품은 한 곳에만(자산) 적고 visual 은 '방의 유일한 바이올린은 턱 밑의 것' 처럼 수를 못박는다. 같은 판에서 난로가 바닥의 화로가 된 것은 'the small iron grate set into the chimney breast under the white mantelpiece' 로 잡았다.

- **'wheel ruts' 는 현대 타이어 트레드가 되고, 'iron-rimmed wheels' 는 수레바퀴 하나를 가장자리에 세운다**(주홍색 연구 S7 두 판): 마차 바퀴 자국은 'two thin plain straight grooves pressed into the wet clay, each a single unbroken line the width of a finger' 로만 적고 'wheel' 낱말은 피한다(사물 낱말이 사물을 부르는 규칙). 부정어 tire tread·tyre tracks·chevron tracks 로 트레드는 사라졌고, 남은 바퀴는 crop 으로 지웠다. 같은 작품 S8 의 '빈 방의 반지' 는 캐스트에 없는 장화·검은 천(시체 암시)을 구석에 끼워 넣었다 — crop 처방.

- **캐스트에 없는 조연('the driver on his high seat') 은 주인공의 얼굴과 옷을 복제한다 — 그리고 'wet cobbles' 는 노란 차선을 부른다**(주홍색 연구 S11 두 판): 마부가 홈스와 같은 검은 머리·회색 코트로 마차 안에 서 있었고 길에는 현대식 노란 이중선. 마부를 'a stout man of fifty in a caped dark brown coat and a low-crowned hat, seated up on the high driver's box behind the roof, face shadowed' 로 별개 인물로 적고 '두 사람: 인도의 홈스와 마부석의 마부' 로 수를 못박자 통과; 길은 'wet cobbles running plain and unbroken from kerb to kerb' + 부정어 yellow road lines·painted road markings.

- **'a plain kitchen … a stone hearth' 는 현대식 가스레인지와 수도꼭지 싱크대를 부른다**(검은 고양이 S3·S4): 'kitchen' 낱말이 현대 부엌을 기본값으로 깐다. 자산 spec 에 시대와 사물을 못박아야 한다 — 'a plain kitchen of the 1840s: an old open hearth of rough grey stones with a black iron pot hanging on a hook, a wooden dresser, a wooden water bucket, a plank back door' + 부정어 gas stove·oven·sink·faucet·tap. visual 에도 '부엌에 있는 것은 탁자·화덕·찬장·물통·문뿐' 으로 목록을 닫는다. S4 는 이 처방으로 두 번째 판에 통과, S3 는 두 판 다 딴 결함(수염)이라 원본 crop.

- **'the goldfish in its glass bowl stands on the table' 은 어항 없는 금붕어가 바닥에 놓이기도 한다**(검은 고양이 S1 2판): 'the goldfish swimming inside its round glass bowl full of clear water, the bowl standing on the round table' + 부정어 fish on the floor·fish out of water 로 3판에 통과. 같은 컷의 'coal fire glows low' 는 탁자 밑 화로가 되어 'grate set into the chimney breast under the mantelpiece on the side wall' 로.

- **'취한 남자'(hair fallen over his brow, slack face, heavy eyes) 는 수염을 부른다 — 'clean-shaven, cheeks and chin bare of any beard' + 부정어 beard 로도 두 판 다 안 잡혔다**(검은 고양이 S3): 같은 인물이 다른 컷(S1·S2·S4)에서는 수염이 없어 일관성이 깨진다. 흐트러진 외모 서술은 머리카락·옷깃에만 두고 얼굴 서술은 'the same thin clean plain face as before' 로 붙이거나, 안 되면 원본을 crop 으로 살린다.

- **아내가 고양이를 안고 웃는 응접실 투샷에서 문가의 남자는 세 판 다 웃는다 — 'grimace of disgust'·'face hidden behind his forearm' 도 안 듣는다**(검은 고양이 S11 세 판): 따뜻한 가정 장면의 기본값이 미소라 부정어 smiling 으로도 못 막았다(1판은 난로가 양탄자 위 모닥불, 2·3판은 벽난로 정상). 혐오·공포 표정이 필요한 컷은 투샷을 버리고 그 인물만 크게 잡거나 뒷모습으로 돌린다. 채택은 3판(웃되 손 흔들지 않음·흰 얼룩·벽난로).

- **실내 컷에 night_bg('a black night sky thick with stars') 가 붙으면 천장이 별하늘로 열린다 — 그리고 'the size of a clock' 은 시계 문자판을 붙인다**(타임머신 S1·S2): 식당 두 컷 모두 천장 자리에 별이 총총하고 모형 기계에 시계판이 달렸다. visual 끝에 'the panelling rises on every side to a plain white plaster ceiling that closes the room overhead, the room shut in on all sides with no window in view' + 부정어 starry sky·open ceiling 으로 천장이 닫혔고, 크기 비유는 'no bigger than a man's two hands together' 로 바꿔 시계판이 사라졌다(사냥개→말, 상자→궤짝과 같은 비유 소환 규칙). 밤 실내 컷은 night_bg 를 캐스트에서 빼는 것이 근본 처방.

- **우물의 'bronze rungs set in its wall' 은 수도꼭지·코일 도르래·사슬을 부르고, 'well … black shaft going down' 은 배경에 우물을 여럿 뚫는다**(타임머신 S10 세 판·S12 세 판): S10 1판 놋쇠 수도꼭지에서 검은 액체, 2판 코일 달린 도르래 팔, S12 1판 놋쇠 사슬투성이. 'rung' 낱말을 완전히 빼고(S10 은 'a low round ring of grey stone blocks, its open top a round black hole', S12 는 'a straight ladder of short flat bronze bars fixed into one wall like the steps of a ladder' + 손·발 자세) 부정어 winch·crank·coil·chains 로 잡혔다. 배경의 여분 우물은 'the only opening in the whole meadow' 로도 안 막혀 같은 높이의 풀 띠를 가로로 이어 붙인 PIL 패치로 덮었다(가장자리 feather 필수 — 다른 높이의 조각은 톤이 달라 사각형 자국).

- **밤 갱도·밤 좌대 안 같은 '어두운 실내' 컷에 night_bg 가 붙으면 별이 뜬다 — 캐스트에서 빼도 '밤' 문맥이 남으면 별 몇 개는 남는다**(타임머신 S12 3판): 남은 별은 '주변 14px 평균이 검은 곳의 밝은 픽셀' 만 골라 검은 원으로 덮는 PIL 패치가 빠르다(문턱값만 쓰면 아치의 돌까지 검게 칠해진다).

- **기계의 형태를 비유로 적으면 그 물건이 된다 — 'ivory … leather saddle' 은 상아 말 조각상, 'like a bicycle frame with a bicycle saddle' 은 진짜 자전거**(타임머신 S14 두 판): machine 자산 spec('squat machine of brass and ivory on nickel rails, leather saddle, two ivory levers, bars of quartz') 을 그대로 두는 편이 안전하고, 캐스트에 없는 흰 털 형체가 끼어든 원본은 이야기(어둠 속 몰록의 손)로 읽혀 그대로 뒀다.

- **'a woman's white shawl caught on the thorn' 은 여인을 세운다 — 'shawl' 낱말 자체가 사람을 부른다**(폭풍의 언덕 S15 세 판): 원문과 2판('empty piece of cloth, no one holding it') 모두 숄을 든 여인이 나왔고, 3판에서 'shawl' 을 지우고 'a torn strip of plain white cloth, no bigger than a pillowcase, snagged by one corner on a thorn' 으로 사물화하자 사람 없는 풍경이 됐다(코트→앉은 사람, 망토→누운 사람과 같은 결: 입는 물건의 이름은 입는 사람을 부른다).

- **창 밖의 손은 '창 안의 손' 이 된다**(폭풍의 언덕 S3): 'pressed against the outside of the glass' 만으로는 방 안에서 유리를 짚는 손이 됐다. 'pressed flat against the far side of the glass, outside in the dark and seen through the panes, palm and five spread fingers squashed pale against the glass from outside' + '침대의 남자 두 손은 방 안 얼굴 앞에, 이 손은 세 번째 손' 으로 안팎을 못박고 부정어 hand inside the room·arm reaching in 으로 잡혔다.

- **'a work table with sewing' 은 재봉틀을, 'the big kitchen of a moor farmhouse' 는 가스레인지를 부른다 — 시대 없는 명사는 현대 물건이 기본값**(오만과 편견 S1·폭풍의 언덕 S10): 'sewing basket of thread and needles', 'kitchen of 1770 with an open hearth of rough stones, iron pot on a hook, wooden bucket, no modern thing in it' 처럼 연대와 구체 사물을 적고 부정어 sewing machine·gas stove·sink 를 둔다.

- **'windows white with winter' 는 실내 선반·들보·문틀에 눈을 쌓는다**(투명인간 S1): 'windows frosted white on their outside panes, the room inside dry and warm' + '표면은 마른 나무·벽돌' 로 적고 부정어 snow indoors. 남은 눈은 crop 으로.

- **보이지 않는 사람의 '빈 옷' 은 문구로는 안 되고, 뒤에 보이는 것을 적어야 한다**(투명인간 S6·S11·S14): 'no head'·'on nothing'·'hollow' 는 무효. '옷깃 위로 의자 등받이 가죽이 빈 공기 사이로 그대로 보인다(S11)', '옷깃 위로 어두운 복도가 그대로 보인다(S14)' 처럼 **가려졌어야 할 배경이 보인다** 고 적으면 머리 없는 옷이 나온다. 비유('보이지 않는 옷걸이에 걸린 것처럼') 는 진짜 옷걸이 막대를 부른다. 두 인물이 병합되면 '멀리 떨어진 별개의 두 것, 사이에 빈 마루' 로 못박는다. 그래도 남는 살갗·막대·손은 PIL 로 덮는다(안경알은 마스크에서 제외).

- **'눈만 떠 있는 고양이' 는 몸통이나 머리를 부른다**(투명인간 S12 두 판): 문구로는 안 되고, 몸통 없는 판을 골라 벽지 띠로 머리를 덮고 초록 눈 한 쌍을 PIL 로 그리는 것이 확실.

- **한 컷의 'small fire'·'coal fire glows' 는 바닥 모닥불·의자 위 불을 부른다 — 화격자를 벽 안에 못박아도 안 잡히면 fire 낱말을 전부 빼고 '재만 남은 차가운 화격자' 로**(투명인간 S2 세 판·S5, 오만과 편견 S1·S6): 부정어 campfire·fire on the floor 와 PIL 패치(마룻바닥 띠) 는 실패했고, fire/flame/glow 낱말을 모두 지우자 통과. 불이 꼭 필요하면 'inside the small iron grate set into the chimney breast under the mantelpiece on the side wall, well away from the rug' 로 위치까지 적는다.

- **'open road over the downs'·'wet cobbles' 는 아스팔트와 노란 차선을, 'milestone with its face turned away' 는 숫자를 부른다**(투명인간 S8, 주홍색 연구 S11): 'narrow unpaved chalk track of packed earth and loose flints, grass down its middle, plain and unmarked' + 부정어 asphalt·road markings·lane lines. 남은 숫자는 PIL.

- **patch_clip 은 ComfyUI 큐 대기가 길면 파일 없이 exit 0 으로 끝난다 — 작업은 큐에 살아 있다**(투명인간 S2): 재조립 체인은 patch_clip 의 종료가 아니라 **클립 파일의 존재** 를 기다려야 한다(`until [ -s clip ]`). 사이드카 kf 와 클립 재생성이 한 큐에서 번갈아 돌면 각 5~20분.

- **'십자가를 목에 걸어 준다(hands raised to his neck, a cross on a cord between them)' 는 두 사람을 끈으로 잇는다**(죄와 벌 S13 세 판): 'cord' 가 두 인물 사이의 선이 되고, 'round her own neck only' 로도 안 풀렸다. 동작을 버리고 '십자가를 두 손바닥에 올려 내밀고 끈은 손바닥에 감긴 채' 로 바꾸자 끈 연결이 사라졌다(십자가는 침대 위로 갔지만 허용). 두 인물 사이의 '끈·줄·사슬' 은 동작 문구에서 아예 빼는 편이 안전.

- **'shaking the rain from her umbrella'·'rain on the window' 는 방 안에 비를 내린다**(개츠비 S8 두 판): 방 자산에 '비는 유리 바깥, 방 안은 마름' 을 적은 1판도 실내 빗줄기가 그대로였다. rain 낱말을 전부 빼고 '접힌 우산' + 'water streaks on the outside of the window glass' + 부정어 rain·open umbrella 로 적자 통과(우산은 펴진 채 나왔지만 허용).

- **'빈 파티장' 컷의 캐스트에 군중 자산이 붙어 있으면 부정어로도 군중이 남는다**(개츠비 S15 두 판): party 자산의 'hundreds of guests' 가 컷 문장의 'empty lawn' 보다 강하다. 빈 장소 컷은 **그 장소를 채우던 자산을 캐스트에서 빼고** 남은 물건(등불·빈 식탁·의자)만 적는다. 같은 원리로 빈 부두 컷(S14)은 'the lawn, the dock and the shore hold no figure, dock planks bare' 로 통과.

- **'elfin face' 는 뾰족 귀를 그린다**(주홍 글자 S7·S8, pearl 자산): 요정 같은 아이라는 뜻이어도 모델은 엘프 귀로 읽는다. 'impish round human face, small round ears hidden in her curls' + 부정어 pointed ears·elf 로 두 컷 다 통과. fairy·pixie·elfin 처럼 종족 이름이 든 형용사는 인물 자산에 쓰지 않는다.

- **옷에 붙은 표지(주홍 A)는 위치와 크기를 적지 않으면 치마의 큰 천 조각이 되고, 붉은 표지 옆에 붉은 얼룩이 번진다**(주홍 글자 S4·S6): 'high on the breast over her heart, no wider than her hand, skirt plain grey' 와 'the only red on her is the A' 를 함께 적자 통과. 인원을 줄이는 판(S5)에서 표지가 사라지면 문구로 되살리기보다 PIL 로 작은 글자를 그리는 편이 빠르다.

- **'a Paris wine shop' 은 간판 글자·전구·손목시계를, 연대 없는 'saw' 는 전기톱을, 'street' 는 노란 차선을 부른다**(두 도시 이야기 S8·S12): 가게 이름 명사는 현대 가게의 간판·조명까지 딸려 온다. 자산을 '간판 없는 돌 문간, 기름등' + 'wrists bare' 로 바꾼 판도 셋 다 남아 결국 상단 crop + PIL 로 지웠다. 도구는 '1790 two-man hand saw', 길은 'cobbles, no painted line' 처럼 연대와 재질을 붙이면 한 판에 통과한다.

- **'swollen yellowish face' 는 얼굴과 손 전체를 노랗게 칠하고, 'a police office' 는 현대 경찰서(라디에이터·배지 달린 모자)를 부른다**(죄와 벌 S3·S9·S8): 피부색 형용사(yellowish·greenish)는 병색이 아니라 물감으로 읽힌다 → 'puffy face of ordinary pale skin with a sickly greyish cast'. 관청·경찰서·사무실은 '1866 Russian, clerks in green coats, tiled stove, quill' 처럼 연대·복장·난방·필기구 넷을 적으면 한 판에 통과. 같은 작품 S11 의 사무용 회전의자도 'plain wooden chair of 1866' 으로 잡혔다.

- **'없는 것의 자국' 을 그 주인의 모양으로 적으면 주인이 돌아온다**(동물농장 S15): 'straw pressed in the shape of a big horse' 는 빈 마구간에 흰 말을 눕혔다. 빛·지형 비유와 같은 원리로, 부재를 그릴 때는 주인의 이름(horse)을 문장에서 전부 빼고 'wide shallow hollow' 처럼 자국의 크기·모양만 적는다. 한 판에 통과(짚의 검은 구멍은 허용).

- **인물 자산의 신발·작업복은 시대가 다른 컷까지 따라간다**(빵충 사육 준수 사항 S3): 귀농 뒤 복장(흰 농업용 장화)을 자산에 넣자 귀농 전 재즈바 장면에서도 장화를 신었다. 과거 회상 컷은 사이드카에서 해당 구절만 '청바지·검은 캔버스화'로 바꿔 통과. 복장이 바뀌는 작품은 처음부터 시기별 자산을 둘로 나눈다(공주와 완두콩의 princess_wet/court 처럼).

- **직업·악기 이름은 자산 세부 한 구절로도 모든 컷에 그 물건을 세운다**(빵충 S4·S6·S11·S14): 정한 자산 세부의 'long slender fingers of a trumpet player' 가 정한이 나오는 컷마다 트럼펫을 쥐여 줬고(S11 은 얼굴 앞에 트럼펫이 떴다), 'trumpet case' 는 검은 트럼펫·유포니움 잡종 악기가 됐다. 자산에서 trumpet 을 지우고, 케이스는 'a closed black rectangular hard-shell carrying case shaped like a small suitcase, latched shut' 로 악기 이름 없이 적자 통과. 자산 세부(뒷부분)도 340자 안에 들면 컷에 실린다 — 직업을 말하는 낱말(trumpet player, physiotherapist)은 세부에도 쓰지 않는다.

- **감춘 것(withheld)의 모습은 그 생물의 다른 단계 컷에서 튀어나온다**(빵충 S11): 애벌레 농장 컷에 날개 달린 성충 두 마리가 천장에 떠, 작품이 숨긴 '다 자란 모습'을 암시했다. 부정어 flying insect·wasp·beetle·moth·winged insect 로 잡혔다. 작은 결함은 PIL 확산 보정으로 지워 봤지만 흰 천장의 용마루선이 끊겨 버렸다 — 규칙적인 선이 지나는 배경은 재생성이 낫다.

- **'실패한 농사' 컷에서 과일은 싱싱한 채 남는다**(빵충 S5·S6): 'withered strawberry plants … a few shrivelled dark berries' 로도 손에 든 포기가 푸르고 빨간 딸기가 달렸다. 'every plant brown and dead, only small blackened dried-up berries' + 부정어 ripe red strawberries·fresh green leaves 로 대부분 잡힌다(몇 알은 남음).

- **'X fills the left of the frame' 같은 구도 문장은 X 의 축척을 키운다**(빵충 S8): 손에 든 애벌레가 '화면 왼쪽을 채운다'고 적자 거대한 소금빵과 공중에 뜬 거대 애벌레가 그려지고 손에는 작은 밀웜이 남았다. 크기는 'no bigger than his palm' 처럼 몸에 견주어 적고, 구도는 인물의 위치로만 말한다.

- **'bony hands' 는 해골 손을 그린다**(혼모노 S7): 마른 노인의 손을 'long bony hands' 로 적자 한 손이 뼈만 남은 해골 손이 됐고 발목까지 앙상해졌다. 'long thin hands' 로 바꾸고 부정어 skeleton·bones 로 통과. 몸을 뼈로 부르는 형용사(bony, skeletal, gaunt limbs)는 자산에 쓰지 않는다.

- **갓·도포 차림 노인은 수염을 제멋대로 기른다**(혼모노 S1~S3): 같은 문수가 짧은 콧수염, 긴 흰 턱수염, 염소수염으로 컷마다 달랐다. 수염은 한 가지로 자산에 박는다 — 두 번 재생성해 수렴한 얼굴('a thin grey moustache and a short sparse grey goatee')을 기준으로 삼았다. 'bare shaven chin' 은 오히려 수염을 불렀다(부정 성격의 서술).

- **무신도·족자는 가짜 한자 글귀와 낙관을 달고 나온다**(혼모노 S4·S8·S9·S10): 'painted cloth scrolls of folk deities' 는 네 컷 모두 세로 글귀와 붉은 낙관을 그렸다. 'showing only painted deity figures on blank paper' 로 자산을 고쳐도 이미 만든 컷은 종이 색 중앙값으로 덮는 PIL(scratchpad paper_patch.py)로 지웠다 — 밝은 픽셀 60% 이상을 종이로 보고 칠하면 티가 거의 안 난다. 족자가 여러 폭이면 **폭마다** 확대해 확인한다 — S8 은 가운데 폭만 지우고 세 번째 폭의 옅은 글귀를 놓쳐 클립을 한 번 더 구웠다.

- **'X 가 없다(empty of the crowds)' 는 X 를 부른다 — 사람 없는 장소도 마찬가지다**(이상현상 연구원 S1): 'the courtyard beyond them is empty of the crowds that should be there' 가 안뜰 원경에 군중을 세웠다. 'deserted, bare flagstones as far as the fog' 처럼 보이는 것만 적고 부정어 crowd·tourists 로 통과. 같은 컷의 '성인 딸'은 'grown daughter' 만으로는 아이가 되어 'a young adult woman as tall as her mother' 로 키를 몸에 견주어 적었다.

- **'square stone pillar bases' 가 줄지어 서면 묘지가 된다**(이상현상 연구원 S10): 짓다 만 궁궐 터의 주춧돌이 사람 키 비석처럼 서서 묘지로, 'plain grey walls' 는 창 달린 요새·감옥 담으로 읽혔다. 'low flat square granite foundation stones, knee-high with a round socket carved in its top' 로 높이와 홈을 적고, 담은 'low traditional palace wall with a curved tiled coping' + 부정어 gravestones·cemetery·prison 으로 한 판에 통과.

- **'갠 옷' 은 빈 의자에 사람 몸 모양으로 앉는다 — 그러면 결말을 지어낸다**(이상현상 연구원 S15): 마무리 컷의 'neatly folded hanbok' 이 빈 의자에 속이 빈 채 꼿꼿이 앉은 한복이 되어, 탐사원이 사라졌다는(자료에 없는) 결말을 암시했다. 옷 이름을 빼고 'a small flat square pile of neatly folded cloth, pressed flat like laundry' + 'chair pushed all the way in, seat empty' + 부정어 empty clothes sitting upright 로 통과. 소개형 영상은 그림이 결말을 암시하지 않는지도 검수 항목이다.

- **사람 없는 풍경 컷에도 먼 점 같은 사람이 끼어든다 — 절벽·길 끝이면 뜻이 생긴다**(녹색 절벽의 신자들 S7·S12): 빈 절벽 끝에 개미만 한 사람이 서서 투신을 암시했고, 귀갓길 원경에 원고에 없는 검은 인물이 섰다. 풍경 컷은 **원경까지 확대해** 사람 점을 찾고, 있으면 PIL(같은 높이 띠 복사 + 행별 좌우 보간)로 지운다. 소재가 민감한(집단 자살·실종) 작품일수록 반드시.

- **'얼굴이 뭉개져 보인다'는 설정은 문구로 안 그려진다**(녹색 절벽 S1): 'every face smeared into a soft blank blur' 를 적어도 학생 얼굴이 모두 또렷했다. 얼굴 타원마다 강한 가우시안 흐림(scratchpad face_blur.py)을 후처리로 입혔다. 클립(WAN I2V)은 그 흐린 얼굴을 그림체로 받아들여, 새로 화면에 들어오는 학생들의 얼굴까지 뭉개진 채로 이어 그렸다 — kf 후처리로 클립의 스타일을 이끌 수 있다.

- **'security guard parka' 같은 직무 복장 명사는 이름표·소매 패치를 달고, 거기에 가짜 글자를 쓴다**(영원한 천국 S6·S7·S11): 세 컷 모두 가슴 이름표와 방패형 소매 패치에 글자 모양이 생겼다. 자산을 'a plain unadorned winter parka, bare smooth fabric on the chest and sleeves' 로 바꿨다. 이미 만든 컷의 작은 가짜 글자는 **색으로 덮지 말고 가볍게 흐린다** — 색 덮기는 패치 도형이 깨져 오히려 눈에 띄었다(scratchpad 의 흐림 blur 함수).

- **'a chain of shadows' 의 chain 은 진짜 쇠사슬을 그린다 — 부정어로도 안 막힌다**(흉담 S10 두 판): 비유의 '줄줄이(chain)'가 1판에선 맨 앞 그림자 손의 쇠사슬, 2판(부정어 chain 추가)에선 그림자 행렬 전체를 꿰는 사슬이 되었다. 낱말을 'row' 로 바꾸자 사라졌다. 이 작품은 감춘 비밀이 '끌려간 사람들'이라 사슬은 스포일러이기도 했다. chain·link·thread·web·net·knot 같은 연결 비유는 실물이 아니면 쓰지 않는다.

- **창유리의 '반사'는 다른 사람이 창밖에 선 그림이 된다**(흉담 S13): 'his faint reflection shows in the dark glass' 가 머리색이 다른 남자가 창밖에서 들여다보는 장면이 되어 유령·제3자를 암시했다. 반사는 쓰지 말고 'plain clear black night with only rain streaks' 로.

- **벽시계가 화면에 있으면 I2V 는 바늘을 타임랩스로 돌린다 — 동작 문구로 못 막는다**(흉담 S14 두 판): 'the long hand ticks one small step to twelve' 는 5초 동안 바늘이 두 바퀴 가까이 돌아 2시 10분쯤에서 끝났다. 동작을 '휴대폰 화면 빛 하나만, 시계는 그린 물건처럼 고정, 바늘은 never turning/never ticking' 으로 바꿔 다시 구워도(같은 kf·시드 42) 똑같이 돌았다. 시계는 바늘 움직임을 기대하게 만드는 사물이라 그렇다. 고친 방법은 후처리: 첫 프레임에서 시계 원(검은 테 **안쪽**에 경계)을 잘라 알파 마스크 PNG 로 만들고 ffmpeg overlay 로 전 프레임에 덮었다 — 테가 검은색이라 이음매가 안 보인다. 시계를 일부러 움직이고 싶으면(S1 오프닝) 회전을 효과로 받아들이고, 정지가 필요한 컷이면 처음부터 덮어 고정할 계획을 세운다.

- **수묵 화풍의 'black fog' 는 흰 안개가 된다 — 'the moon is hidden' 은 보름달을 띄운다**(암행 S1): 먹선·담채 화풍은 안개를 종이 흰색으로 칠해 '검은 안개'가 눈밭 같은 흰 마당이 되었다. 'thick soot-black fog, dark as ink smoke and darker than the night, pours in heavy black billows' 로 **먹 연기**에 견주자 검게 나왔다(자산 fog_bg 도 같이 고쳐 뒤 컷에 전파). 부정 서술 'the moon is hidden' 은 'empty of crowds' 와 같은 소환 — 'a starless overcast black sky' 처럼 보이는 것만 적는다.

- **배역 자산은 옷까지 박는다 — 잠옷 장면에도 관복과 사모를 씌운다**(암행 S4): cast 'hyeonu' 자산(청색 관복+사모)이 visual 의 'plain white inner robe' 를 이겨 잠에서 깬 신랑이 사모를 쓰고 이불 위에 앉았다. 옷이 바뀌는 장면마다 **변형 자산**(hyeonu_prison·hyeonu_road 처럼 hyeonu_night)을 미리 만들어야 했다. 사이드카에서는 프롬프트 속 자산 문장을 'bareheaded, plain white cotton sleeping robe' 로 바꾸고 부정어 hat·official robe 로 통과. 같은 컷의 '꺼진 초'는 'no flame at all, smoke from the dead black wick' 이어야 꺼진다(그래도 작은 불꽃 남음).

- **'쓰러진 나무 기러기'는 죽은 진짜 거위가 된다 — 머리 둘 달린 채로**(암행 S7): 'a carved wooden goose fallen on its side' 가 바닥에 뒤집힌 거위 사체(머리 둘)와 머리 없는 흰 몸통이 되었다. 넘어진 조각상·인형은 시체로 읽힌다 — 넘어뜨릴 것은 촛대·그릇 같은 생물 아닌 물건으로.

- **시대극 원경의 'city roofs'·'farmhouse chimney' 는 현대를 부른다**(암행 S10·S15): 인왕산 아래 'far ridges of the city roofs' 는 고층 빌딩 숲, 새벽 들판의 'farmhouse chimney' 는 벽돌 공장 굴뚝과 서양식 박공집이 되었다. 'the tiled roofs of Hanyang', 'the low thatched straw roof of a small Joseon farmhouse' 처럼 시대 재료를 붙인다. 원경 현대 건물은 안개 그라디언트로 덮을 수 있지만(S10), 굴뚝 연기처럼 하늘을 크게 가로지르는 건 PIL 로 지우면 덩어리·이음매가 남아 재생성이 낫다(S15 두 번 실패).

- **'화면 밖 누군가의 그림자'는 화면 안의 사람이 된다**(암행 S12): 성별 미공개 호위무사를 'a third traveller's long shadow from someone walking just out of frame' 로 숨겼더니 길 끝에 갓 쓴 남자가 걸어갔다(행 보간으로 지움). 동작 문구의 'the long shadow of the third traveller moves ahead' 도 클립에서 사람을 불러낼 수 있어 같이 뺐다. 성별을 감출 인물은 그림자 문구도 쓰지 말고 아예 화면에 넣지 않는 편이 안전하다.

- **'red-rimmed eyes' 는 두 뺨을 진홍으로 칠한다 — 맞은 멍처럼 보인다**(암행 S8): 우는 얼굴의 붉은 픽셀 채도만 45% 로 낮춰 눈물 자국은 살렸다. **허수아비는 웃는 얼굴(^_^)을 단다**(암행 S14) — 서늘한 장면이면 'a blank burlap head with no face' 로 적거나 타원 마스크로 지운다.

- **I2V 동작의 'black ribbons' 는 바닥을 기는 검은 뱀 같은 띠가 된다 — 'stream in through the gate' 는 새 인물을 들였다가 지운다**(암행 S4·S6 클립): 안개를 'low black ribbons' 로 적자 이불 위를 미끄러지는 진짜 검은 띠가 생겼고, 'a soft translucent haze of dark smoke, formless and thin' 으로 바꾸자 연기 소용돌이만 남았다. 'the constables stream forward through the gate' 는 문에서 포졸 셋이 들어오다 3.6초에 증발했다 — I2V 는 **화면에 없던 사람을 새로 들이는 동작**을 끝까지 유지하지 못한다. 이미 화면에 있는 인물이 제자리에서 움직이게만 적는다.

- **배경 자산의 'rain' 은 방 안에 비를 내린다 — 장소 자산의 'window streaked with rain' 도 같다**(인비인 S1·S2·S3): 배경 rain_bg('grey rain on a dark afternoon')를 cast 에 넣은 서재 컷이 셋 다 방 안 공중에 빗줄기를 긋고 바닥을 적셨다. rain_bg 를 cast 에서 빼고 장소 자산 창을 'a tall closed window of pale grey glass' 로 바꾼 뒤, 비는 visual 에 'grey rain streams down the outer face of the glass, while inside the room the air is dry' 로만 적어 해결. 실내 장면의 날씨는 **배경 자산으로 주지 않는다**.

- **"worm's-eye view" 는 진짜 지렁이를 그린다**(인비인 S2): 앙각 촬영 용어가 바닥에 기어가는 지렁이가 되었다(bird's-eye 도 새를 부를 수 있다). 'seen from directly below' 처럼 풀어 쓴다. 책상 **밑판**처럼 카메라가 닿기 힘든 면은 'the desk turned upside down, legs pointing up, its underside facing the camera' 로 물건을 뒤집어 보여 주는 편이 확실했다.

- **'android' 에 'synthetic face·grey' 를 붙이면 만화 로봇이 된다**(인비인 S10·S14): '인간보다 인간 같은' 안드로이드가 둥근 눈의 마네킹 머리·금속 관절이 되었다. 'a lifelike humanoid android that could pass for a person at first glance … porcelain-like skin … only a thin seam line at the neck and wrists giving it away' + 부정어 robot head·mechanical face 로 사람 얼굴이 나왔다. **자산만 고치면 안 된다** — visual 문장에도 옛 묘사가 박혀 있으면(S14) 그쪽이 이긴다.

- **카메라 절의 샷 크기가 kf 보다 가까우면 I2V 가 밀고 들어간다**(인비인 S4): kf 는 책상 모서리 중간 샷인데 카메라 절이 'extreme close shot' 이라 클립이 줌인했고, 'the crack darkens into a clear line' 은 금을 검은 틈으로 벌렸다. 카메라 절은 **실제 나온 kf 의 샷 크기**로 적고('the same three-quarter view as the first frame, no push-in'), 균열·상처는 '그대로의 굵기'로 고정한다. 같은 kf·시드라 줌은 약하게 남았다.

- **인물 자산의 표정('a bright wide smile')은 모든 컷에 박힌다**(더 코워커 S4·S6): 갸웃해야 할 S4, 겁먹어야 할 S6 에서도 내털리가 활짝 웃었다. 표정은 자산에 넣지 말고 visual 에 컷마다 적는다('her face pale and frightened, no smile at all, brows pulled up' + 부정어 smiling). 'makeup slightly smudged at the eyes' 는 눈두덩 멍과 뺨의 붉은 줄(상처처럼)이 되어 피부색으로 덮었다.

- **'두 책상' 장면은 소품이 남의 자리로 옮겨 간다**(더 코워커 S4): 돈의 카디건이 내털리 의자에 걸리고 거북이가 내털리 책상에 올라 '내털리가 돈 자리에 앉은' 그림이 되었다. 'two separate side-by-side desks divided by a low partition: at frame left … her own decorated desk with flowers … at frame right the separate neighbouring desk … its own empty chair … the cardigan hanging on that empty chair' 처럼 **누구 것인지 자리마다 소유를 다시 적는다**.

- **'face down photograph' 는 앞면을 보여 준다 — 상패 'fronts turned away' 도 앞면이 나온다**(더 코워커 S8·S3·S9): 형사가 내미는 사진에 사람 얼굴 같은 형체가 나와 감춘 '시신 발견'을 암시했다. PIL 로 흰 카드에 테두리만 그렸다. 뒤집힌 물건은 부정 서술이라 안 먹힌다 — 'a plain white card' 처럼 처음부터 빈 물건으로 적는다.

- **I2V 동작의 'blue shadow' 는 화면 전체를 청색으로 물들인다**(더 코워커 S9): 'until both desks sit in blue shadow' 가 3초 만에 온 화면을 짙은 파랑으로 바꿨다. 'soft dim grey dusk, their own colours kept … never tinted' 로 해결. 동작 문구에 색 이름을 '그림자·빛'과 함께 쓰지 않는다.

- **도자기 장식품도 I2V 에선 살아 움직인다**(더 코워커 S14): 'the turtle itself stays completely still' 이라 적어도 귀여운 거북이 장식이 고개를 숙이고 다리를 옮겼다. 매 프레임 거북이 마스크(초록·윤곽선)의 **합집합**을 만들어 첫 프레임 거북이를 주변 밝기에 맞춰 덮었다 — 첫 프레임 마스크만 덮으면 움직인 몸이 바깥으로 겹쳐 보인다(흉담 시계처럼 테두리가 없는 물체는 합집합이 필요).

- **visual 의 숫자 나이('a woman of sixty')는 외모 묘사를 이긴다**(3월의 마치 S1·S2·S4): '국민 엄마 배우, proud striking face' 였는데도 'of sixty' 때문에 주름진 70대 할머니가 나왔다. 자산에 'looks barely fifty' 를 넣어도 visual 문장의 'of sixty' 가 남은 컷(S4)은 또 노인이었다. 자산·visual·anchor 에서 숫자를 모두 빼고 'a glamorous well-preserved former film star who looks barely fifty' 로 바꾸자 S6 부터 맞았다. 나이는 **낭독이 말하고 그림은 인상으로** 적는다(나이 든 인물을 품위 있게 그려야 할 때 특히).

- **'화면 밖 사람의 팔' 은 온전한 사람이 된다 — 그 사람이 성별 미공개면 위반**(3월의 마치 S6): 'a flustered receptionist's arm reaches after her' 가 청진기 찬 흰 가운 여의사가 되었다(의사 제제는 성별 미공개). 암행 S12 그림자와 같은 계열 — 신체 일부·그림자로도 부르지 않는다. 같은 작품 S3 의 'a voice from another room', 'a light is on though no one else lives here' 는 문틈에서 뻗는 검은 손을, 소파 위 '긴 검은 장갑'은 잘린 팔처럼 보이는 그림을 만들었다.

- **I2V 동작의 'turns her head to look over her shoulder' 는 몸 전체를 한 바퀴 돌린다**(3월의 마치 S2): 2초간 뒷모습이 되었다가 다시 정면. 'keeps facing the camera the entire time while her eyes drift slightly aside … her whole body and shoulders stay facing the camera without turning' 로 해결. 고개 돌림은 '눈길'로 적는다.

- **동작 문구에만 있는 소품은 클립 중간에 생겨난다**(3월의 마치 S15): kf 가 그리지 않은 'the pair of high heels … stay still' 이 3초 무렵 의자 옆에 하이힐을 세웠다 — 빈 코트+신발은 '사라진 사람'(결말)을 암시. kf 를 고친 뒤에는 **동작 문구를 kf 에 실제 있는 것으로 맞춘다**(흉담 S14 시계·암행 S12 그림자와 같은 원리).

- **'alien' 이라는 낱말은 그레이 외계인(큰 검은 눈의 머리)을 붙인다 — 'headless' 를 적어도 이긴다**(헤일메리 S12·S14): 바위 몸의 외계 존재에 매번 그레이 외계인 머리가 달렸다. 'alien' 을 빼고 'the rock creature … a broad flat five-sided boulder … seen from slightly above, its wide top facing the camera' 로 바꾸자 머리가 사라졌다. 그래도 다리 달린 바위에는 만화 얼굴(점 눈·입, 개구리 얼굴)을 그려 넣는 버릇이 남아 PIL 로 지웠다 — 의인화되기 쉬운 비인간 존재는 '위에서 내려다본 구도'로 얼굴 자리를 없애는 게 가장 잘 먹혔다.

- **크기 비교('the size of a large dog')는 그 동물을 부른다**(헤일메리 S13): 외계 존재가 개 머리를 달고 섰다. 크기는 'the size of a low footstool' 처럼 생물 아닌 물건에 견주거나 화면 속 다른 물건과의 비율로 적는다. 'boyish friendly face' 도 옆에 꼬마를 세웠다(S8) — 나이·사람을 연상시키는 형용사도 사람을 부른다.

- **'hangs' 는 줄을 단다**(헤일메리 S4·S11): 'a small planet hangs tiny', 'an alien spacecraft hangs' 가 모빌처럼 위에서 내려온 실에 매달렸다. 우주의 물체는 'floats, free and unattached' 로. 'a large pale gold star' 는 만화 오각별(★)이 되었다(S2) — 항성은 'a perfectly round pale gold sun, a softly glowing disc'.

- **'a thin bridge across the dark' 같은 은유는 진짜 다리를 놓는다**(헤일메리 S15): 두 우주선 사이가 수면 위 난간 다리와 빛나는 문이 되었다. 'joined at the middle by one short narrow pale grey tube' 처럼 물리 구조로.

- **편집 모델(--ref)에 완성 컷을 참조로 주면 구도까지 복제한다**(헤일메리 S14): 생명체 디자인만 옮기려고 S13 채택본을 참조로 물렸더니 인물 자세·카메라까지 S13 과 거의 같은 그림이 나왔다. 참조는 **배경 없는 캐릭터 시트**(흰 바탕 단독)여야 한다.

- **사물 이름이 든 색('broccoli-green')은 그 사물을 그린다**(천 개의 파랑 S4): 로봇 몸빛을 'broccoli-green' 으로 적자 로봇 머리에 진짜 브로콜리가 올라앉았다. 색은 'pale sage-green' 처럼 색 낱말로만. (salmon, lemon, olive, cherry, mint 도 위험)

- **'tired middle-aged … streaked with grey … worn face' 를 겹치면 할머니가 된다**(천 개의 파랑 S11): 10대·20대 딸을 둔 엄마가 70대로 나왔다. 피로는 '눈 밑의 옅은 피로' 하나로, 머리는 'black bob with only a few fine grey strands' 처럼 검은 머리를 먼저 적는다. 3월의 마치 'of sixty' 와 같은 계열 — 나이는 외모로 과장된다.

- **주인 없는 소지품이 마무리 컷에 남으면 '그 인물이 사라졌다' 는 결말이 된다**(천 개의 파랑 S15 빈 헬멧, 3월의 마치 S15 코트+하이힐): 마무리 정지 컷에는 인물을 떠올리게 하는 개인 물건을 두지 않는다 — 풀·새·빛처럼 중립적인 것으로.

- **동작 문구의 'orange light' 도 화면을 물들인다**(천 개의 파랑 S11): 'the last orange light slides' 가 첫 1초 화면 전체를 주황으로 칠하고 남색 카디건을 갈색으로 바꿨다(더 코워커 S9 'blue shadow' 와 같은 원리). 'a faint pale band of evening light … colours exactly as they are … never tinted' 로 해결.

- **'kite bird'(솔개)는 연줄 달린 새 모양 연이 된다 — 동음이의 동물명**(이상한 지도 S13): 'a single kite bird circles high' 가 하늘에서 마을까지 줄이 이어진 연을 그렸다. 'hawk' 로. (crane→기중기, bat→방망이, seal→도장도 같은 위험)

- **그림 속 그림(지도·족자·벽화에 그려진 인물)은 장면의 실제 인물로 튀어나온다**(이상한 지도 S12): 'on the map the painted figure of a woman walks away toward the shrine' 이 지도가 아니라 진짜 길 위를 걷는 여자를 세웠다 — 감춘 고인의 유령으로 읽혔다. 그림 속 인물은 문구에 넣지 말고, 넣어야 하면 'tiny faded ink pictures' 처럼 사물로만.

- **'흔적·자국(marks pressed into the mat)'은 가짜 글자가 된다**(이상한 지도 S4): 다다미 위 흔적이 한자 같은 획으로 그려졌다. 밝은 면 위 가는 어두운 획만 grey-closing(블랙햇) 마스크로 잡아 지우면 다다미 결은 살고 글자만 빠진다.

- **'small'·'stocky round-faced' 는 청년을 꼬마로 만든다 — 웅크린 자세가 더한다**(나미야 S1·S5): 20대 좀도둑 셋 중 하나가 키 작은 꼬마로, 바닥에 웅크린 둘은 초등학생으로 나왔다. 자산을 'three men in their early twenties, all adult height, grown-up faces' 로, 한 명은 'light stubble, wide jaw' 로 성인 표지를 박자 S6~S13 은 맞았다. 그래도 **앉거나 기는 여러 명**이 한 컷에 있으면 아이를 불렀다(S5 두 번) — 그런 컷은 한 명만 남기는 구도로 원고를 바꾸는 게 빠르다.

- **범죄 직후 인물의 옷 얼룩은 피로 읽힌다**(나미야 S1): 강도 뒤 도망치는 셋의 청바지에 적갈색 얼룩이 그려졌다. 색상(H)만 데님 파랑으로 옮기면 질감은 남고 흙때로 읽힌다(중앙값 덮기는 얼룩덜룩해졌다). 원고엔 'clean faded jeans' 처럼 깨끗함을 적는다.

- **빈 의자·벤치 위의 초상 액자·꽃 한 송이·꽃다발은 헌화다 — 인물이 빠진 마무리 컷에서 결말(이별·죽음)을 말해 버린다**(테오 S14·S15): '빈 벤치에 놓인 스케치와 들꽃' 이 노인 초상 액자+꽃 한 송이, 들꽃 다발로 그려져 감춘 이별을 암시했다. 빈 자리엔 '아직 쓰지 않은 것'(펼친 빈 스케치북 흰 장, 연필)이나 '그 자리에 자라는 것'(길가 데이지)을 둔다. 같은 계열로 렌더 전에 고친 것: 부두 끝에 개어 둔 후드(투신), 젖은 외투+벗어 둔 운동화만 남은 빈 부두(익사) → 말리는 외투·김 나는 보온병·집 쪽으로 난 발자국(아가미 S9·S15).

- **cast 자산은 visual 을 이긴다 — 바꾼 장면에 옛 소품 자산이 cast 로 남아 있으면 그 소품을 계속 그린다**(테오 S14): visual 에서 초상을 빼고 부정어 portrait·frame 을 넣어도 cast 의 parcel 자산(갈색 종이로 싼 초상 액자)이 액자를 불러왔다. 원고를 고칠 땐 cast 목록부터 본다 — 장면에 없는 것이 cast 에 있으면 뺀다.

- **'face pink with cold' 는 얼굴 전체를 분홍 가면으로 칠한다**(테오 S12): 겨울 산책 노인의 얼굴이 통째로 분홍이 되었다. PIL 로 얼굴 영역의 분홍만 살빛 쪽으로 색상 이동·채도 낮춤 하고, 원고는 'cheeks only faintly flushed'. 감정·온도를 얼굴색으로 쓰지 않는다(붉은 눈·붉은 뺨 교훈과 같은 계열).

- **물속에 떠 있는 사람은 익사체로 읽힌다 — 늘어진 손, 감은 눈, 팔 벌리고 등 대고 뜬 자세**(아가미, 렌더 전 교정): 'floats … suspended, his hands drift open at his sides', 'floats with his eyes closed', 'floats on his back, arms spread wide' 는 전부 시신 자세다. 물속 인물은 '헤엄친다·발을 찬다·손으로 젓는다(sculling)', 눈은 뜨고, 작은 표정을 준다. 수면의 '무언가 막 가라앉은 자리(something has just slipped down)' 도 '물고기가 막 뛴 자리' 로.

- **'naga' 는 뱀 꼬리를 단다 — 낱말을 빼도 '온몸 비늘·눈꺼풀 없는 눈' 만으로 꼬리가 따라온다. 옷을 입혀 막는다**(눈물을 마시는 새 S2·S4·S5·S6): 자산에 'two arms and two legs', 'tailless … no tail at all' 을 넣고 부정어 tail 을 세 겹 걸어도 매번 바닥에 똬리 튼 꼬리가 나왔다. 'naga' 를 'scaled young man' 으로 바꿔도 꼬리. 통한 건 **사람처럼 옷을 입히는 것** — 'dressed like a person in a long loose robe falling to his ankles over plain cloth trousers; only his hairless head, face, neck and hands show, and that skin is fine deep green scales'. 'naga city' 는 탑 밑동을 휘감은 거대한 뱀을 불렀다 → 'hidden tree city'. 같은 계열로 'Korean folk goblin' 은 저고리 밑 말꼬리를 달았다 → 'a Korean folk spirit shaped like a stocky bearded man, with no tail' + 저고리를 무릎까지. 비늘 있는 인물(아가미 곤)에는 미리 'two ordinary human legs and bare feet, no fish tail'.

- **과교정 주의 — 'smooth human-shaped face' 는 검은 머리카락을 심는다**(눈마새 S4): 도마뱀 주둥이를 막으려 넣은 말이 평범한 청년 머리를 그렸다. 'head completely bald and hairless, scalp and face covered in fine pale green scales' 로 털 없음까지 적어야 했다.

- **이종족 넷을 한 컷에 세우면 모델이 섞는다 — 자산 넷을 빼고 실루엣 특징만 짧게**(눈마새 S12): 네 cast 자산(나가·도깨비·레콘·인간)으로 그린 모닥불 장면이 뿔 달린 도마뱀, 웃는 긴 머리 여자(없는 인물·성별 창작), 도끼 든 고블린이 되고 레콘은 빠졌다. cast [] 로 비우고 visual 에 '로브 입은 민머리 / 흑립 쓴 수염 사내 / 볏과 부리의 거구 새 전사와 쇠몽둥이 / 망토와 칼자루' 를 한 구절씩 적자 넷이 또렷하게 나왔다.

- **'padded jacket'·'little black cap' 은 패딩 점퍼와 야구모자다**(눈마새 S11): 시대 옷은 재료와 매듭까지 — 'old-fashioned quilted hemp jacket tied with a cloth sash', 'small black horsehair cap'. 판타지·시대극의 'road' 는 노란 중앙선 아스팔트가 되어(같은 컷) 자산을 'unpaved track of packed earth and frozen wheel ruts, a strip of grass down its middle' 로 바꾸자 마무리 컷(S15)까지 흙길이 되었다.

- **'a faint halo of light rings the moon' 은 탑 허리에 빛나는 고리(UFO)를, 'milky way' 는 혜성 줄기를 그린다**(눈마새 S14): 밤하늘 장식 구절은 빼고 달·작은 별만. 검은 하늘 위 얇은 고리는 PIL 로 지우면 흐린 네모 자국이 남아 재생성이 낫다.

- **'hidden city … amber windows below' 는 현대 고층 도시를 깐다**(눈마새 S4): '아래는 거목 꼭대기와 줄기 속 작은 창뿐, no buildings anywhere' 로.

- **기대 놓은 긴 막대(당목·빗자루·노)는 I2V 에서 미끄러진다**(눈마새 S7 클립): 동작은 향 연기뿐인데 기둥에 기댄 당목이 5초 동안 기울기를 바꾸며 미끄러졌다. 첫 프레임 패치(페더 4px)를 전 프레임에 덮어 고정. 원고에선 기대 세운 막대를 '눕혀 둔' 것으로 쓰는 게 안전하다(흉담 시곗바늘·더 코워커 거북 고정과 같은 기법).

- **'weathered face' 는 젊은 어른을 60대로 만든다**(고래 S9): 갓 출소한 20~30대 춘희가 주름진 할머니로. 'calm smooth round young face without wrinkles', 'young woman' 으로 바로잡았다(천 개의 파랑 'tired middle-aged'·이상한 지도 'lined face' 와 같은 계열 — 얼굴 형용사에 세월 낱말을 쓰지 않는다). 'very large … far taller and broader than an ordinary man' 은 여전히 보통 체구로 나왔다 — 거구는 다른 인물·사물과 나란히 세워야 보인다.

- **시대극 산골의 'where the road leaves the hills' 는 회색 포장도로와 전봇대를 깐다**(고래 S2) → 'a narrow footpath of bare earth winds out between the hills'. 같은 컷의 'girl in her early teens' 는 6~8살 꼬마·분홍 볼로 나와 자산에 'tall and long-limbed for her age, oval face' 를 넣자 11~12살이 되었다. 그래도 정면 클로즈업(S5)은 다시 어려졌다 — 볼 분홍은 이마 살빛을 블러 마스크로 섞어 지운다(HSV 로 채도만 낮추면 허연 반점이 남는다).

- **'tail fluke of a diving whale' 은 고래 통째 솟구침이 된다**(고래 S14): 앞 컷(S13)과 같은 그림이 되고, 동작('꼬리가 가라앉는다')과도 어긋난다. 'only the great forked tail fluke … its whole body already hidden deep under the sea' + 부정어 whale head·breaching.

- **마당의 'silver with dew' 는 푸른 물바다, 먼 연기는 앞 사물에서 피어오른다**(고래 S15): 'the yard is dry bare brown earth and the weeds along its edges are silver with dew', 연기는 'far off … from the chimney of a low thatched cottage' 로 출처와 거리를 박고, 양동이는 'empty'.

- **노을빛이 쌓인 벽돌 더미 위에 '빛 원반(렌즈 플레어)' 이 떠다닌다**(고래 S11 클립): 동작 'low sunset light slides across the rows' 가 0.5~2.5초 동안 노란 원반으로 나타났다 사라졌다. 첫 프레임 패치를 전 프레임에 덮어 지웠다(패치는 원반이 지나간 범위 전체 + 여유 50px — 처음엔 아래로 모자라 자국이 남았다). 빛이 미끄러지는 동작은 '그림자가 길어진다' 쪽이 안전하다.

- **'slender young nun … round dark eyes, quick wide smile' 은 초등학생 수녀를 그린다**(태양 아래 올리브 S2·S3): 동그란 얼굴·분홍 볼·무릎 위 짧은 수녀복. 'in her late twenties, tall and of full adult height, grown-up oval face', 'long habit falling below the knees to the shins' 로 고치자 성인. 'young' + 둥근 눈 + 웃음은 아이 표지다(나미야 'small/stocky', 헤일메리 'boyish' 와 같은 계열). anchor 도 함께 바꾼다.

- **두 인물이 한 컷에 있으면 한쪽 옷이 다른 쪽으로 번진다 — 무지 옷 쪽에 '없는 것' 을 적는다**(올리브 S11·S12): 과학 유튜버 솔민이 수녀 이레와 같은 하늘색 수녀복·나무 십자가를 걸쳤고(S11), 바로잡은 뒤에도 솔민 가방에 십자 문양이 남았다(S12, PIL). 'dressed in her own plain charcoal linen shirt and dark trousers, with no veil and no cross' 를 둘이 나오는 모든 컷에 넣자 S13·S14 는 처음부터 맞았다.

- **주차된 차의 'exhaust curling from its tail' 은 정면 차의 보닛 연기(엔진 화재)가 된다**(올리브 S10): 차를 'rear end toward the camera' 로 적어도 정면이 나왔다. 연기를 동작에서 빼고 움직임을 다른 것(등 아래 나방)으로 옮긴 뒤 'no smoke or steam rises from the car' 를 박는다.

## 8. 레이어 자산 (2026-08-29 도입)

디자이너가 포토샵에서 레이어를 나누듯, 장면을 **자산 파일**로 분해한다.
발상: 사용자 제안 — "scene.md 에서 사물이 나오면 전부 md 로 분리하고, 뭍.md
pond.md bg.md 처럼 꼼꼼히 묘사해 유기적으로 읽어 프롬프팅하자."

지금까지의 결함이 전부 이 부재에서 왔다: 규격 문장이 없던 금도끼(소품),
실외 우선으로 쓰인 오두막(장소), 자세가 박힌 늑대 사전(인물). 인물에게만
주던 대접을 모든 층에 준다.

### 구조
```
works/handwritten/<작품>/assets/
  tiger.md  thief.md ...      (인물)
  gotgam.md ...               (소품)
  yard.md  barn.md  room.md   (장소·지면)
  night_bg.md                 (배경 — 날씨·시각·하늘)
```

### 파일 서식
```
---
name: gotgam
kind: 소품            # 인물|소품|장소|지면|물|배경
spec: a string of dried persimmons ...   # 규격 한 문장 — 항상 그대로 삽입
---
상세 묘사(영어). spec 뒤에 쉼표 경계로 예산까지 이어 붙는다.
```

### 조립 규칙
- 박자의 cast 에 자산 이름을 **z 순서**(인물 → 소품 → 장소·지면 → 배경)로 적는다.
- 삽입량은 kind 별 상한: 인물 340 / 장소 250 / 지면·물 220 / 소품 180 / 배경 160.
  spec 은 언제나 통째로, 상세는 상한까지만 — 그래서 **spec 한 문장에 정체를
  다 담는다**(규격 문장 규칙과 동일).
- 전체 예산 1900자는 그대로다. 예산이 곧 편집이다: 그 컷에 보이는 층만 cast 에
  넣는다(보이지 않는 층을 넣는 것이 소환 사고의 뿌리였다).
- 컷 고유 묘사(visual)는 구도·행동·빛에 집중하고, 반복되는 생김새는 자산이
  진다. 이러면 visual 이 짧아져도 밀도가 유지된다.
- 자산만 고치면 신선도 검사가 못 본다 — 자산을 고치면 treatment 를 touch 한다.

기존 작품(personas 사전)은 그대로 동작한다. assets/ 가 있으면 그쪽이 이긴다.

## 9. 파이프라인 v3 — 세밀 분할 + 참조 체인 (설계 2026-08-29)

사용자 결정: "시간이 더 걸려도 세밀하게 쪼개고 정확하게." 두 축으로 고도화한다.

### 9.1 밀도 분할 — 한 컷 한 사건
확산 모델의 진짜 한계는 토큰 수가 아니라 **그림 하나가 소화하는 주장의
개수**다(실측: 인물 둘+소품+장소가 겹친 컷에서 결속·수·자리가 무너졌다).
- 컷 수는 14 고정이 아니라 **14~18 가변**. 배치는 낭독 문장 수에서 N 을
  읽으므로(§ 코드) 문장을 늘리면 컷이 는다. 관문 조각 상한 20.
- 분할 기준: 인물 2 + 소품 + 새 장소가 한 박자에 겹치면 둘로 나눈다.
  각 컷은 "누가·무엇을·어디서" 중 **새 정보 하나**만 진다.
- 하한: 클립 81프레임 = 3.4초. 68초에 최대 ~19컷.

### 9.2 참조 체인 — 정체성은 픽셀로
글로 전달하던 인물 생김새를 **캐릭터 시트 이미지**로 전달한다.
- ②.7 시트: 인물 자산마다 1장(단독 등장이라 예산 경쟁 없음 — spec+상세
  전문 사용). scripts/make_sheets.py, output/<작품>_sheets/.
- ③ 키프레임: gen_keyframe --ref 시트… 로 Qwen-Image-Edit-2509 +
  TextEncodeQwenImageEditPlus(참조 3장까지). 프롬프트에서 인물 묘사가
  빠지고(scene_prompt --v3) 구도·행동·빛·소품·장소·배경만 남는다.
- 발동: treatment 에 "pipeline": "v3". 없으면 기존 경로 그대로.
- 시트 신선도: 자산 md 를 고치면 시트 png 를 지운다(재생성 유도).

### 9.2.1 시트 규범 (스모크 테스트 실측)
- **시트의 결함은 전 컷으로 복제된다** — 시트 호랑이가 도포를 입고 두 발로
  서자 시험 컷도 그대로 따라 입고 섰다. 시트는 사람이 검수한 뒤 체인에
  태운다(배치 전 확인, 결함 시 png 삭제 후 재생성).
- 동물 시트는 **네발 중립 자세·맨 털가죽**을 자산에 명시한다. 시트
  템플릿에 figure 같은 사람 어휘를 쓰지 않는다(subject).
- **참조는 텍스트보다 세다** — 자세까지 시트를 따라간다. 시트는 중립
  자세로 만들고, 컷의 자세는 프롬프트 첫 절에 강하게 적는다.

### 9.2.2 참조 운용 실측 (v3 1호 검수)
- **2인 참조는 확률적으로 탈락한다**(5컷 중 2컷 — 도둑이 넥타이 차림
  현대인으로). 연약한 정체성(사람)은 참조 1장 + 텍스트 340자가 안전하다.
  박자의 refs 로 참조 인물을 지정한다.
- **근접 참조 컷은 시트의 무지 배경이 장면을 밀어낸다** — 배경 우선 절을
  프롬프트 둘째 자리에 넣는다(구현: scene_prompt v3).
- 부재 명사 규칙 재확인: 본문의 'ox' 한 낱말이 외양간에 진짜 소를 세웠다.

- **참조 컷에서 텍스트 인물은 현대인이 된다**(실측: 340자 조선 도둑 묘사가
  선글라스 낀 현대인으로 — 참조가 생성 방식을 지배해 텍스트 인물 묘사가
  묻힌다). 컷 단위 이분법: 보이는 인물 전원을 참조하거나, 컷 전체를
  텍스트 경로(refs: [])로 되돌린다. 근접 단독 컷의 배경 소실도 같은
  처방이다 — 배경이 주인공인 컷은 텍스트 경로가 안전하다.

- **합본 참조는 구도의 왕이다 — 서사 컷에 쓰지 않는다.** 합본 시트를 문
  참조 컷은 출연 인원(부분 출연 불가)·배열(나란히)·자세(정면 응시)까지
  시트를 따라간다(실측: 브레멘 — 당나귀 혼자여야 할 도입부 네 컷에 전원이
  등장하고, 행진·뒷모습·잠자리가 모두 '나란히 서서 정면 보기'로 뭉개졌다.
  좋았던 컷은 전부 텍스트 경로였다). 합본 참조는 시트와 같은 배열의 컷
  (전원 집합 원경)에만 쓰고, 서사 컷은 텍스트 경로에 출연 인원·시각·자세를
  못박는다.

- **합본 자산은 텍스트로도 전원을 소환한다** — cast 에 합본 자산을 두면
  그 묘사(네 마리 열거)가 삽입되어 부분 출연 컷에도 전원이 등장한다(실측:
  브레멘 재작 도입부 재실패). 부분 출연 컷의 cast 는 개별 자산으로만 적는다.
  합본 자산은 전원 컷 전용이다.

- **배제 문구보다 구도.** '방은 비어 있다'를 세 번 적어도 주인공 사전확률이
  두 번째 소녀를 세웠다(실측: 엄지공주 납치 컷 3연패). 있어선 안 될 인물은
  말로 내쫓지 말고 **설 자리가 없는 근접 구도**로 프레임에서 지운다 —
  클로즈업 전환 1회로 즉시 해결됐다.

- **낯선 화풍 프리픽스는 컷마다 널뛴다** — 'Goguryeo tomb-mural' 을 모델이
  몰라 실사·중국화·민화로 제멋대로 해석했다(실측: 바보 온달 절반의 컷).
  전역 화풍은 검증된 계열(minhwa 등)만 쓰고, 실험 화풍은 장소 자산의
  묘사로 국소 적용한다 — 벽화 결이 산 컷은 hunt_field 자산 덕이었다.
- **소지품은 자산이 아니라 컷에 적는다** — 자산에 박힌 지게가 말 위까지
  따라왔다(실측: 사냥대회의 장작짐). 컷 조건부 소지품은 그 컷 visual 에만.
- reading 같은 동사도 사물을 소환한다(실측: '허공을 읽는 손'의 reading 이
  노모 손에 책을 쥐여 줬다) — 소환 어휘 검사를 늘려 간다.
- **장소 자산의 소품은 컷의 어디에든 놓인다** — 실내 자산(책상·남폿불·화로)을
  cast 에 넣은 채 툇마루 컷을 그리니 책상과 화로가 빗속 툇마루에 나왔다
  (실측: 빈처 S2). 실내 자산의 '문 너머' 컷은 그 자산을 cast 에서 빼고
  visual 에 장소를 직접 적는다("the narrow wooden veranda of a small Korean
  house at night in the rain … the paper door open showing only dim lamplight").
- **열린 문·어두운 문간은 인물을 세운다** — "the paper door dark with rain
  behind him" 이 문간에 남편을 한 명 더 세웠다(실측: 빈처 S3). 홀로 있는
  컷의 문은 "closed" 로 닫고 "exactly one man" 을 붙인다.
- **닮음 서술은 결함까지 옮긴다** — "the two faces alike in every line" 을 적으니
  처형의 멍이 아내 뺨에도 찍혔다(실측: 빈처 S12, 2회). 닮음은 자산 명세의
  같은 이목구비로만 주고, 상처·멍·분칠 같은 표식이 있는 인물은 그 인물의
  근접 컷으로 잘라 다른 얼굴을 화면에서 뺀다(뒷모습만).
- **세 사람 컷의 '뒤에 앉은' 셋째는 복제된다** — "the husband sits behind them
  at the desk" 가 창가에 남편을 하나 더 세웠고, "exactly three people" 도 막지
  못했다(실측: 빈처 S13, 2회). 낭독 문장에 없는 인물은 cast 에서 빼고 둘로
  줄인다 — 둘 구도(exactly two women)에서야 통과했다.
- **장소 이름의 현대 낱말이 물건을 소환한다** — "the gully camp" 의 camp 가
  1930년대 개울가에 흰 캠핑 텐트 두 동을 세웠다(실측: 산 S7). 장소는 지형
  낱말(hollow, bank, clearing)로 부르고 camp·station·park·lodge 같은 시설
  낱말은 피한다. 같은 결로 "A-frame carrier"(지게)는 사람이 없는 마무리
  스틸에서 A형 텐트가 됐다(실측: 산 S15) — 지게는 "wooden back-carrier".
- **사람 곁의 작은 불은 옷으로 옮겨 붙는다** — "a few small flames still licking
  a fallen log" 가 바지에 불구멍을 냈다(실측: 산 S10). 인물 컷의 잔불은
  "smoking blackened log" 처럼 연기로만 적는다.
- **팔레트의 강조색은 빈 땅에 웅덩이로 고인다** — 귤껍질 하나를 위해 넣은
  'burnt orange' 가 진흙길 빈 자리에 주황 웅덩이를 칠했다(실측: 탈출기 S2).
  한 컷의 소품 색은 그 컷 visual 에만 적고, 팔레트는 작품 대부분의 컷에
  실제로 깔리는 색만 넣는다.
- **뼈 낱말은 뼈를 그린다** — 노인의 손을 "bony spotted hand" 라 적으니 손자의
  두 손까지 해골 손이 됐다(실측: 할머니의 죽음 S3). 마른 손은 "thin wrinkled
  hand"; bony·skeletal·gaunt 같은 골격 낱말은 얼굴·손 묘사에 쓰지 않는다.
  같은 컷에서 "dharani scroll"(경문 족자)은 글자를 불렀고, 방 자산의 "quilt
  bedding laid on the warm side" 는 서양식 침대가 됐다 — 족자는 "paper scroll
  with a faded red woodblock pattern", 요는 "spread directly on the oiled paper
  floor" 로 적는다.
- **소유격도 사람을 부른다** — 빈 마당 스틸의 "the grandmother's walking stick
  and cloth shoes" 가 할머니를 툇마루에 세웠다(실측: 할머니의 죽음 S7). 부재
  인물의 물건은 "a wooden walking stick and a pair of worn cloth shoes" 처럼
  소유격 없이 적는다.
- **눈가·뺨의 색 형용은 옆 얼굴로 옮겨 간다** — 중모 자산의 "red-rimmed sleepless
  eyes" 가 잠든 할머니의 눈에 빨간 점을 찍었다(실측: 할머니의 죽음 S4). 피로는
  "tired sleepless eyes" 처럼 색 없이 적는다.
- **quilt·bedding 은 서양식 침대를 부른다** — "quilt bedding laid on the warm side"
  는 세 번 연속 침대 프레임이 됐고, "spread directly on the floor" 도 못 막았다.
  "a Korean ondol floor bedding, a thin cotton mattress and quilt spread flat on
  the oiled yellow paper floor with a low wooden pillow" 에서야 바닥에 깔렸다
  (실측: 할머니의 죽음 S3·S5). 이웃집 방도 "spread on the bare floor for
  sleeping in the Korean way" 로 적는다. 자산만으로는 부족하다 — 컷 visual 에
  "low angle at floor level … the oiled floor stretching across the lower
  frame" 을 함께 적어야 프레임이 사라진다(실측: 자산 수정 뒤에도 S9·S10·S12·
  S15 가 침대였다).
- **관계어가 나이를 끌어내린다** — grandmother 곁의 grandson 은 자산이 스물셋이라
  해도 열 살 아이로 그려졌다(실측: 할머니의 죽음 S11·S13). 자산에 "a grown
  man with a strong jaw and broad shoulders" 를 넣고 컷마다 "the grown grandson"
  이라 부른다.
- **시대 없는 물건 이름은 현대 물건이 된다** — "water-sprinkling truck" 은 요즘
  트럭, "cold-drink seller's stand" 는 빨대 꽂힌 유리컵, 거리 자산의 "shop
  awnings" 는 한글 비슷한 간판 글자가 됐다(실측: 땡볕 S1~S3). 탈것은 "a
  horse-drawn water cart with a perforated barrel", 좌판은 재료로("a block of
  ice under a straw mat, brass bowls"), 상점은 "plain cloth awnings" 로 적는다.
  "sweat-soaked jeogori 를 펄럭인다" 는 가슴을 풀어헤쳤다 — 옷은 "tied closed".
- **사람 없는 스틸의 I2V 는 사람을 지어낸다** — kf 는 빈 수레·얼음·그릇뿐이었는데
  WAN 이 체크 셔츠에 청바지 차림의 여자를 만들어 짐을 싣게 했다(실측: 땡볕 S15,
  발행 뒤 클립 검수에서 발견). 마무리 스틸의 motion 은 "the willow leaves sway …
  the carrier, the bowl and the block of ice standing still" 처럼 움직이는 주어와
  정지한 주어를 사물로만 채운다 — "empty" 같은 빈자리 낱말이 사람을 부른다.
  스틸이라도 kf 만 보고 넘기지 말고 클립 중간 프레임까지 봐야 한다.
- **small·키 작음 + 올려다봄은 아이를 그린다** — "a small wiry man … looks up at
  the tall doctor" 가 네 컷에서 아이가 됐다(실측: 붉은 산 S10·S11·S13·S14).
  작은 체구는 "a short lean grown man of thirty-five with a stubbled jaw" 처럼
  나이·수염 자국을 함께 적고, 컷마다 "exactly two grown men" 이라 센다. 허리춤의
  "knife" 는 두 번 연속 장검이 됐다 — 무기는 자산에서 빼고 필요한 컷에만 작게.
- **홀로 선 인물의 I2V 는 얼굴과 배경을 갈아 끼운다** — kf 는 눈밭의 조선 사내였는데
  클립 중간에서 서양인 청년과 현대식 건물이 됐다(실측: 붉은 산 S10). "track" 이
  철길이 된 kf 가 발단이었다. 길은 "the frozen furrows of the plain" 처럼 지형으로
  적고, motion 에 "a Korean man with black cropped hair … the snowy furrows and
  the flat horizon behind him unchanged" 처럼 인종·머리색과 배경 불변을 명시한다.
- **상투·곰방대·마른 체구의 '젊은' 농부는 소년이 된다** — "a lean farmer of thirty
  with a topknot … a bamboo pipe" 가 세 컷에서 아이로 그려졌고, 자산에 "grown, thin
  moustache" 를 넣어도 곰방대를 문 컷은 여전히 소년이었다(실측: 논 이야기 S9·S11).
  젊은 성인은 "a broad-shouldered grown man of thirty with a thin moustache" 로
  적고 곰방대는 노인 쪽에만 준다. 큰 인물이 곁에 서면 아이로 기울기 더 쉽다.
- **상품 이름은 라벨 글자를 부른다** — "sake bottle" 은 두 번 연속 글자 라벨이
  붙은 병이 됐고 "unlabelled" 도 막지 못했다(실측: 고향 S15). 병은 "a plain dark
  brown glass bottle with a cork" 처럼 재료·마개로만 적는다. 같은 컷의 창밖 "telegraph
  poles" 는 현대식 송전탑이 됐다 — "wooden telegraph poles with sagging wires".
- **blood 는 양을 지키지 않는다** — "a bead of blood" 는 손가락에서 흘러내리는
  줄기가 됐고, "a pinprick of blood" 는 장판 위 핏덩이가 됐다(실측: 술 권하는
  사회 S1, 2회). 바늘에 찔린 손가락은 "her thumb pressed to her lips, her face
  pinched" 처럼 자세로만 적고 blood 낱말은 쓰지 않는다.

- **자산 의상과 장면 의상이 다르면 사람이 둘로 갈라진다** (실측 09-06 피아노 S1, 두 번): 아내 자산(블라우스·치마)
  + "흰 웨딩드레스의 신부" → 신부 곁에 평상복 아내가 한 명 더; 남편 자산(밝은 삼피스·콧수염·안경) + "검은
  연미복" → 연미복 남자와 양복 남자 둘. 모델은 자산 명세를 한 사람, 장면 서술을 또 한 사람으로 그린다.
  고치는 법: 그 컷에서 자산을 빼고 visual 에 사람을 통째로 적거나, 자산 의상 그대로 세우고 소품(옷깃의 흰 꽃)만
  더한다. "exactly two people" 만으로는 막지 못한다.

- **악기 자산이 곁에 있으면 인물을 앉혀 연주시킨다** (실측 09-06 피아노 S12): "beside the piano, head bowed,
  hand pressed to chest" 라고 적어도 아내가 건반 앞에 앉아 치는 그림이 나온다(원문은 칠 줄 모르는 장면). 연주하지
  않는 컷에서는 악기 자산을 cast 에서 빼고 "standing upright, her hands nowhere near any keys" 처럼 자세를 못박은 뒤
  악기는 "the dark edge of a piano lid behind her shoulder" 정도로만 남긴다. 자산 명세의 "bright smiling eyes" 도
  우는 컷에 그대로 새어 들어오므로, 표정이 뒤집히는 컷은 자산 대신 visual 에 사람을 통째로 적고 "no smile" 을 적는다.
  또 "the hem of the wife's skirt at the edge of the frame" 같은 부분 등장은 사람 전체(남편 뒤에 매달린 아내)로
  커진다(S13) — 부분 등장은 쓰지 않고 그 컷에서 그 인물을 아예 뺀다.

- **홀로 선 인물에게 "걷는다" 동작을 주면 I2V 가 카메라를 얼굴로 밀고 들어가며 화풍이 바뀐다** (실측 09-06 피아노 S2):
  "her shoes step lightly along the path … the camera holds on the young wife" → 4초 사이 전신 원경이 상반신 밀착이 되고
  머리는 단발, 얼굴은 웹툰풍으로 표류, 꽃나무는 프레임 밖. 홀로 선 인물 컷의 motion 은 발걸음을 주지 않고 "stands still …,
  the tree, the wall and the bench unchanged; the camera holds still and wide on the whole garden, no zoom, her face and hair
  unchanged" 처럼 배경 사물을 이름 붙여 고정하고 카메라를 못박는다. 걸음이 꼭 필요하면 두 사람 이상인 컷에서만.

- **I2V 표류의 큰 원인은 프롬프트가 아니라 입력 크롭이었다** (실측 09-06): scripts/crop_keyframe.py 의 옛 판정이
  옅은 하늘·눈밭·담벼락 행을 종이 여백으로 오인해 위·아래 최대 30% 씩 잘라 넣었고(피아노 S2 27.7%, 빈처 S5·붉은 산
  S11 머리 절단, 최근 348컷 중 165컷), WAN 은 잘린 첫 프레임에서 얼굴·머리를 지어내며 서양 얼굴·현대 인물로 흘렀다.
  새 판정: 종이색 97% 이상 행만 여백, 자막 띠(얇고 획 전환이 많고 좌우 여백이 있는 띠 + 아래 빈 띠)가 있을 때만
  그 아래로, 없으면 가장자리 순수 여백 최대 8%, 종이가 어두운 밤 장면은 손대지 않음. 클립 검수 때 **첫 프레임이
  kf 와 같은 구도인지** 먼저 본다 — 다르면 프롬프트를 고치기 전에 로그의 `"top"/"bottom"` 크롭 값을 본다.

- **재료 이름에 든 동물이 살아 나온다** (실측 09-07 이상한 샘물 S10·S11·S15): 갓을 "black horsehair hat" 이라 적었더니
  세 컷에 말이 등장했다(옆에 선 말, 달리는 말, 샘물 굴 속의 검은 말 머리). horsehair·sheepskin·cowhide·goose-down
  같은 재료어는 쓰지 않고 형태로 적는다: "a black wide-brimmed Korean gat hat", "a fleece coat", "a leather vest".

- **장소 자산 하나에 여러 공간을 적으면 한 화면에 합성된다** (실측 09-07 홍학의 자리 S1~S3): school 자산에
  "복도·사물함·교실·책상·불 켜진 창·정문·가로등" 을 함께 적었더니 정문 앞 도로에 책상과 칠판과 사물함이 놓였다.
  장소 자산은 **한 공간 한 자산**(gate·building·classroom·corridor·staffroom)으로 쪼개고 컷마다 하나만 cast 한다.

- **두 사람의 손동작을 한 문단에 섞으면 한 사람에게 팔이 셋 달린다** (실측 09-01 서동과 선화공주 S10, 발행본 썸네일):
  "the boy's raised arm points … the princess stands with both hands at her mouth" → 소년은 사라지고 공주 한 사람이
  가리키는 팔 + 입을 가린 두 손을 가졌다. 사람마다 위치·동작을 따로 한 절씩 적고("the boy standing at the left with
  one arm raised … ; the princess a step to the right with both hands pressed to her mouth") 끝에 "exactly two people,
  each with two arms" 를 붙인다.

- **실존 지명·상호·거리 이름은 그림에 글자로 박힌다** (실측 09-08 목걸이 kf 6·8·9·10·13): 자산에
  "Palais-Royal arcade … no signboards" 라 적었더니 간판에 PALAIS 가, "Champs-Elysees" 라 적었더니
  화면 아래에 그 철자의 가짜 자막이 나왔다. "shuttered shops without signboards" 도 간판을 소환했다
  (없음은 그릴 수 없다 — 지명판). 장소는 이름 대신 **모습**으로만 적는다: "a wide Paris avenue with
  chestnut trees", "a jeweller's interior with tall glass counters, plain panelled walls above". 간판·
  상점·표지판이라는 낱말 자체를 쓰지 않는다.

- **두 인물 사이에서 "얼굴을 더 가까이 기울인다·입술이 벌어진다·카메라가 두 얼굴에 붙는다"는 입맞춤이 된다**
  (실측 09-08 목걸이 클립 14): motion 에 "her stricken face leans nearer, her lips parting; the camera holds close
  on the two faces" 라 적었더니 WAN 이 35~65% 구간에서 두 여인의 입을 맞췄다. 감정은 **손·눈·자세**로만 적고
  (손을 한 번 누르고 그대로, 눈이 마주친 채 눈물이 고인다), 두 인물 사이 거리는 유지한다고 명시하며
  ("the two women seated a hand's breadth apart"), 카메라는 거리를 두고 정지시킨다.

### 9.3 검증
지표는 "검수에서 수정이 필요한 컷 수". 빨간모자 5 → 금도끼 7 → 선녀 1.
v3 시범작 목표 0~1. 시범작은 브레멘 음악대 재작(동물 넷 = 정체성 최악
조건, 기존 발행본의 고양이 결함 해소를 겸함).
- **조립 예산은 컷마다 계산한다 — 넘치면 팔레트가 통째로 떨어진다.** scene_prompt 는 [visual, 자산…, 팔레트]
  를 쉼표 경계가 아니라 **부품 단위**로 1900자에 맞춘다: 넘치는 순간 그 뒤 부품(소품·장소·배경·팔레트)이 전부
  빠진다(09-12 실측: 추월색 S13 — visual 1140 + 인물 3 + 공원 = 2298 → 칼·공원·팔레트 탈락, 혈의 누 S4·S13,
  금수회의록 S12 도 같은 일). 인물 셋이 서면 visual 은 800 안팎, 둘이면 900, 하나면 1000 이 상한이다. 자산
  spec 이 이미 말한 옷·머리는 visual 에서 되풀이하지 않는다. `remake_queue.sh` 가 컷마다 조립 길이를 계산해
  1850 초과를 막는다.
- **소품을 자산으로도 넣고 visual 로도 적으면 둘이 그려진다.** 상록수 S9 의 놋대접이 세 번(시드 둘) 연속 손에 하나 +
  땅에 하나로 나왔다 — cast 의 coin_bowl 자산 spec("a dented brass bowl holding a few dull copper coins")과 visual
  의 대접 묘사가 서로 다른 물건으로 읽혔고, "a few copper coins already lie in the bottom of the bowl" 이 땅에 동전을
  뿌렸다(09-12). 컷에서 손에 든 소품을 visual 이 이미 말하면 cast 에서 뺀다(추월색의 칼도 같은 이유로 뺐다). 동전처럼
  '이미 있는' 잔 소품은 적지 않는다. 시드를 바꿔도 안 빠지면 낱말이 아니라 **중복 서술**을 의심한다.
- **"lectern" 은 마이크를 단다.** 금수회의록 S3·S4 의 연단 위에 작은 마이크가 섰다(09-13). "reading stand" 로 바꾸자
  마이크 대신 펼친 책이 올라왔고(S5), "a tall dark wooden stand with a plain sloped top of bare wood" 로 하자 맨 연단이
  나왔다(S6~). 연설·강단 계열 낱말(lectern·podium·pulpit·rostrum)은 현대 집회 소품을 부른다 — 가구는 재료·형태로만.
- **크기 비교 대상도 사물로 온다.** "a rounded grey boulder the size of a large water jar" 가 바위 대신 테두리 있는 회색
  물독을 머리 위에 올렸다(09-13 홍길동전 S8). 'palm-sized' 의 야자수와 같은 뿌리 — 크기는 몸(as wide as his shoulders,
  as long as a forearm)에 빗대고, 그릇·항아리·수레 같은 사물 이름으로는 재지 않는다. 'the size of a small boat'(연꽃)처럼
  그 사물이 화면에 있어도 되는 경우만 예외.
- **"locked" 은 자물쇠를 단다.** 춘향의 칼(cangue)을 "a heavy wooden board locked around the neck" 이라 적자 자물쇠 달린
  가죽 목걸이와 열쇠구멍 판이 나왔다(09-14 춘향전 S9). 'lock·locked·key' 는 현대 자물쇠를 부른다 — 결박은 "resting flat on
  the shoulders, the neck up through a round hole, held by two wooden pegs" 처럼 나무·구멍·못으로만 적는다. 칼 자체는
  모델이 모르는 물건이라 판이 등 뒤에 세워지는 정도로 나온다 — 목에 씌우는 구도가 요점이면 클로즈업으로 줄인다.
- **'bare of any ship' 도 배를 띄운다.** 심청전 S15 의 빈 바다에 "bare of any ship or person" 이라 적자 수평선에 돛배가
  섰다(09-14). 마무리 컷의 '아무것도 없음' 은 사물 이름 없이 "the water is smooth to the horizon" 처럼 있는 것만 적는다.
  같은 작품 S14 의 "lotus the size of a small boat" 는 연꽃을 나룻배 안에 앉혔다 — 크기 비유 규칙(위) 재확인.
- **프레임 밖으로 나가는 손잡이는 그 끝에 사람을 세운다.** 흥부전 S13 에 "the other handle of the saw runs out of the
  frame at the right" 라 적자 오른쪽에 톱을 든 둘째 사내가 나타났다(09-14). 두 사람이 쓰는 도구를 한 사람만 보이는
  컷에 넣을 때는 반대편 끝을 "buried in the gourd" 처럼 사물 속에 묻고 "he is the only person in the yard" 를 못박는다.
  같은 작품 S4 의 주걱은 자산+visual 중복으로 둘이 됐다(상록수 S9 규칙 재확인).
- **"crowd" 는 사람 무리를 부른다.** 별주부전 S2 의 "a crowd of sea creatures" 가 침상 뒤에 회색 사람 형체들을 세웠다(09-14).
  짐승 무리는 종류별 명수로 적는다 — "six large silver fish, one pale octopus, three pink shrimp and two small red crabs".
  같은 작품 S10 의 "crabs as big as a dog" 는 창 든 붉은 개 둘이 되었다(크기 비유 규칙 재확인 — 몸의 부위에 빗댄다).
- **짐승에 붙인 "old·wrinkled" 는 노인 얼굴을 준다.** 별주부전 S3 의 "the old soft-shelled turtle's head on its long wrinkled
  neck" 이 자라 머리를 백발 노인 얼굴로 바꿨다(09-14, 시드 1203 사이드카). 짐승의 나이는 적지 않고 생김새로만 —
  "small flat scaly reptile head, pointed snout, small round black eyes, long leathery neck" 로 고치자 바로 자라가 나왔다.
- **꽃신은 'slipper'·'silk shoe'·'pointed toe' 로는 못 그린다 — 현대 플랫·펌프스가 온다.** 콩쥐팥쥐 S11~S14(09-14): "red silk slipper with the pointed upturned toe" 는 물 위에 굽 있는 붉은 펌프스(S12)·쟁반 위 하이힐(S13)·발레 플랫(S11, 시드 둘)을 냈고, 자산 이름 'flower shoe' 는 꽃을 냈다. "shaped as a tiny boat with its toe curling up" 은 물 위에 **진짜 붉은 나룻배**를 띄우고(S11) 마당에 나무 배를 놓았다(S14) — 크기·모양 비유가 사물을 소환하는 규칙 재확인. 통과한 문구(S12·S13 실측): **"a small flat soft shoe of dull red cloth with a curved-up toe and a white stitched rim along its flat sole, no bigger than a hand"** — 재료(cloth)·평평함(flat sole)·테두리(white stitched rim)처럼 고무신·꽃신의 **생김새 요소**만 적고 shoe 종류 낱말(slipper·pump·heel)과 비유는 쓰지 않는다. 신을 한 짝만 그려야 하는 컷은 "there is one shoe in the whole yard, the one on the tray … her left foot bare with pale toes" 로 수를 못박는다(그래도 신은 발보다 트레이 쪽에 남는다).
- **'hoe' 는 시드에 붙박이면 삽이 된다.** 콩쥐팥쥐 S2·S3 의 나무 호미가 "small wooden digging tool… flat wooden blade" 로 고쳐도 긴 쇠삽으로 두 번 나왔다(09-14). "a short straight stick of pale wood no longer than a forearm, one end whittled flat and thin" 으로 도구라는 낱말 자체를 버리고 hoe 자산을 cast 에서 빼자 시드 사이드카(1202/1203)에서 막대기만 건네고·부러져 나왔다. 모델이 모르는 농기구는 '무엇에 쓰는 물건'이 아니라 '어떤 막대·판'인지로만 적는다.
- **"perched" 는 횃대를 세운다.** 피노키오 S11 의 딱따구리를 "perched all along the top of the long nose" 라 적자 시드 둘 다 새들이 코가 아니라 벽 위 **가로 횃대**에 줄지어 앉았다(09-15). 'perch' 낱말을 지우고 "clinging to the nose itself, claws gripping the wood, beaks hammering it" 로 바꾸자 코 곁에 매달려 코끝을 쪼는 그림이 나왔다. 새를 사물 위에 앉힐 때는 perch 대신 cling·stand on·grip 으로.
- **"손 대신 갈고리"는 못 그린다 — 갈고리는 손에 든 도구가 된다.** 피터 팬 후크 선장(09-15): "in place of his right hand a curved iron hook" → 두 손이 다 있고 한 손에 갈고리를 쥠. "his right sleeve ending in a hook, exactly one hand", 'hook' 낱말을 지운 "curved iron claw fixed into the sleeve where a hand would be" 까지 시드 넷·문구 셋(S9 ×4, S11, S12, S13)에서 전부 손에 든 갈고리·발톱으로 나왔고, S11·S13 은 소매 것 + 손에 든 것 둘이 됐다. 팔다리를 대체한 물건(갈고리·의족·의수)은 모델이 못 그린다 — 그 컷은 도구를 든 것으로 수용하거나, 그 팔을 프레임 밖·등 뒤로 돌린다. 'claw' 문구는 적어도 두 번째 갈고리를 덜 부른다(S11·S12 통과). 같은 작품 S2 의 'the size of a firefly' 는 벌레를 그렸고(크기 비유 규칙), "hangs in the air" 는 창틀에서 늘어진 실을 그렸다 — 공중에 뜬 것은 'floats'.
- **"as tall as three men" 은 사람 셋을 세운다.** 신드바드 S9(09-15)의 알 자산 "a huge smooth white egg as tall as three men" 이 cast 에 사람이 없는 컷에서 알 밑에 작은 사람 셋을 그렸다 — 크기 비유는 사물뿐 아니라 **사람의 수**도 소환한다. 크기는 그 컷에 이미 있는 것에 빗댄다("as tall as the great bird is long", "three times higher than his turban", "four times the span of his arms"). 같은 컷에서 자산의 알 + visual 의 알이 작은 알 하나를 더 낳았다(중복 규칙 재확인 — 자산을 빼고 "there is one egg on the plain").
- **"floating in the water / afloat" 는 얕은 물에 선 사람을 그린다.** 신드바드 S6 의 나무통 표류를 세 시드(정면·"far from any shore"·위에서 내려다본 구도)로 돌려도 전부 발이 바닥에 닿은 채 서서 통에 기댔다(09-15). 인물 자산의 '서 있는' 인상이 강할수록 그렇다 — 물에 뜬 사람은 자세를 몸으로 적어야 할 듯: "lying on his chest across the barrel, his legs trailing behind him under the water, his chin on the staves". 팔레트의 dull red 는 그림자에 번져 피처럼 보일 수 있다 → "the shadow on the sand is a soft grey" 로 못박는다.
- **사람 대 사람의 "세 배 크기"는 모델이 정규화한다 — 거대함은 사물로 보인다.** 잭과 콩나무 S8(09-15)의 "a very tall broad woman three times the boy's height", "the top of his head no higher than her knee" 는 시드 둘 다 아이보다 조금 큰 여인으로 나왔다(허리 아래만 보이는 구도 지시도 안 따름). 거인의 크기는 인물끼리 재지 말고 **거대한 돌벽·문·솥·탁자**로 보이거나, 아이를 사물 속(솥 안, S9)에 넣어 사물의 크기로 말한다. 같은 작품 S10 의 "a copper pot as tall as a boy" 는 방 안에 **소년을 하나 세웠다**(숨어야 할 잭이 드러남 — 크기 비유의 사람 소환 재확인), S6 의 "as thick as a tree trunk" 는 줄기를 껍질 있는 나무 둥치로 그렸다. 콩 몇 알을 손에 쥐게 하면 바닥에도 콩이 뿌려진다(S2·S3, 시드 둘 다) — 낱알은 "all five in his hand, the ground bare packed earth" 로 못박아도 남는다, 수용.
- **"courtroom" 은 마이크를 세운다.** 앨리스 S13·S14(09-16)의 자산 "a courtroom with a high bench…" 이 재판석에 현대 마이크 스탠드를 세웠다 — lectern·podium 규칙과 같은 뿌리(현대 집회·법정 소품). "a great hall of dark wood with a high wooden bench and two thrones on it, a railed wooden box where small animals sit holding slates" 로 낱말을 버리자 마이크가 사라졌다. 같은 작품 S10 의 "the third bent to dip his brush in the pot" 은 카드 병정 셋 외에 **사람 하나**를 더 그렸다(동작 주어가 모호하면 새 인물이 선다 — "all three standing upright with brushes raised"); S11 은 이유 없이 그림 안에 흰 액자 선이 생겨 시드만 바꿔 해결.
- **눈 색 "green eyes" 는 형광 초록 눈이 되고 곁 인물에게도 번진다.** 소공녀(09-16) 세라 자산의 'green eyes' 가 세라뿐 아니라 교장·인형·듣는 아이들 눈까지 형광 초록으로 칠했다(S1~S6, 시드 둘). 'grey-green' 도 같았고 **'grey eyes' 로 바꾸자 정상**. 팔레트에 dull green 이 있으면 'green' 낱말이 눈에 몰린다 — 눈 색은 dark/grey/brown 으로만 적는다. 같은 작품 S4 의 "firelight from the schoolroom / the firelit schoolroom" 은 방 바닥에 **모닥불**을 그렸다(불빛은 'warm yellow light' 로), 'red rough hands' 는 빨간 장갑이 됐고(chapped hands), S10 의 "baker's shop front" 는 간판에 가짜 글자를 박았다(지명판 규칙 — 'a bow window full of buns set in a brick wall').
- **시대물의 군중·쓰레기는 낱말 하나로 현대가 된다.** 왕자와 거지(09-16): 골목 자산의 "refuse in the gutter"·"a dented pail" 이 바닥에 **비닐봉지와 플라스틱·양철 들통**을 그렸고(→ "a shallow open drain of dirty water, straw and broken crockery"), S13 의 "people in holiday clothes" 는 거리를 **청바지·코트의 현대 인파**로 채웠다(→ "people in long gowns, doublets and hoods" + "every person in the street wears … of that time"). 시대를 정하는 것은 건물이 아니라 **사람의 옷과 바닥의 잡동사니**다 — 군중과 쓰레기는 그 시대의 물건 이름으로 적는다.
- **짐승 이야기에서 팔레트의 'dull red' 는 피가 된다.** 정글북(09-16) S1~S3 에서 늑대 얼굴의 붉은 상처, 호랑이 앞다리의 핏자국, 바위와 모래의 붉은 얼룩이 시드·문구를 바꿔도 되풀이됐다 — 자산의 'scarred muzzle'·'torn ear'·'teeth bared' 를 모두 걷어내도 남았고, **팔레트에서 dull red 를 빼고 ash grey 로 바꾸자 한 번에 사라졌다**. 이빨·발톱·사냥이 있는 이야기에서는 팔레트에 붉은색을 넣지 않는다(옷·천처럼 붉어야 할 것은 컷의 visual 에서 따로 적는다). 팔레트는 `works/handwritten/<w>/treatment.json` 과 `works/queue.txt` 의 화풍 문자열 **양쪽**을 고쳐야 다음 컷부터 반영된다.
- **"archery target" 은 현대 올림픽 과녁(빨강·파랑 동심원)을 그린다.** 로빈 후드 S9·S10(09-17): 자산의 'a round straw archery target' 이 세 번 모두 색 동심원 과녁을 냈고, 'target of plain coiled straw' 로 바꿔도 남았다. 과녁이 요점이 아닌 컷에서는 **과녁을 화면에서 빼고**(자산에서도 지우고) 필요한 것만 두었고, 과녁이 요점인 컷은 "the whole face is bare pale straw of one colour, wound in a flat spiral, with nothing painted on it" 로 적어 맨 짚 과녁을 얻었다. 경기·표적 계열 낱말(target·bullseye)은 현대 스포츠 용품을 부른다 — 짚·판자·재료와 모양으로만 적는다.
- **"창밖" 은 지켜지지 않는다 — 창 너머 풍경은 컷을 나누거나 벽만 찍는다.** 마지막 잎새(09-17): 다락 컷(S4·S6)에서 "창밖 벽돌담의 담쟁이" 가 **방 안 벽으로 기어들고 비까지 실내에 내렸다**. window_wall 자산을 cast 에서 빼고 창밖 풍경을 visual 한 문장으로만 적고 "방 안 벽은 맨 회벽이고 아무것도 자라지 않는다" 를 못박아 해결. 잎만 보는 컷(S11·S12·S15)은 아예 **"화면을 가득 채운 벽돌 벽, 다른 건물·지붕·마당 없음"** 으로 다시 써야 창틀·옆집·마당이 사라졌다. 잎 수는 "exactly one leaf … every other stem bare to its tip" 처럼 남은 것과 없는 것을 함께 적어야 지켜진다.
- **화가 이야기의 'paint-stained' 는 피가 된다.** 같은 작품에서 수의 'paint-stained smock' 과 베어먼의 'paint-stained shirt' 가 붉은 얼룩으로 나와 상처처럼 보였고, 'red-nosed' 는 광대코를 달았다. 물감 얼룩을 **자산에서 아예 빼고**(옷은 plain) 팔레트에서도 dull red 를 내리자 사라졌다 — 벽돌처럼 정말 붉어야 하는 것은 'dull red brick' 으로 그 자리에만 적는다.
- **두건 속 어둠은 "없음"으로 적을수록 해골이 나온다.** 크리스마스 캐럴 미래의 유령(09-17): 'the hood a black hollow with nothing to be seen inside it' 은 노란 해골 얼굴을, "flat black shadow all the way in, **no face, no skull and no eyes**" 는 더 또렷한 해골을 냈다 — 부정문 규칙(없어야 할 것은 이름을 쓰지 말 것)이 얼굴에도 그대로 적용된다. 세 시드 중 얼굴이 가장 덜 드러난 것을 골라 수용했다. 같은 작품 S13 의 'carved side turned away' 는 비석에 **노인 얼굴을 새겼고**(→ 'plain grey stone, smooth and blank'), S8 의 schoolroom 자산은 쇠다리 현대 책걸상을 냈다(→ '1790년대 긴 널판 책상과 나무 걸상, 쇠붙이 없음' — 추월색 규칙 재확인).
- **'undertaker' + 'long face'·'bony hands' 는 해골을 그린다.** 올리버 트위스트 S5(09-17)의 장의사가 해골 얼굴과 뼈만 남은 손으로 나왔다 — 죽음을 다루는 직업어에 마른 몸을 뜻하는 낱말이 겹치면 인물이 시체가 된다. "a long sober face, thin hands with ordinary fingers" 로 고치고 컷에 "the undertaker's face is a living face of ordinary skin and his hands are ordinary living hands" 를 못박자 산 사람이 나왔다.
- **소년의 옷에 붙은 'a man's coat' 의 'man' 이 어른을 세운다.** 올리버 트위스트 S8(09-17)의 도저는 "a boy of twelve … in a man's brown coat far too big" 으로 시드 셋(1208·1218·1228 이전)에서 전부 **어른 남자**로 나왔다. "a head shorter than a grown man"(비교어)과 컷의 "no grown man anywhere in the frame"(부정문)이 오히려 어른을 불렀다 — 크기 비유·부정문 규칙이 함께 걸린 자리다. 고친 문구: 자산 "a small boy of twelve with a round child's face and short legs, in **a brown coat far too big for him**, the cuffs turned back over his hands, the hem dragging at his ankles, a battered black top hat sitting down on his ears", 컷 "the two of them are small boys of the same size standing with the tops of their heads level with each other, each of them about four feet tall beside the waist-high stone milestone". 어른이 오면 안 되는 컷에서는 'man' 이라는 글자 자체를 프롬프트에서 없앤다.
- **부정은 긍정문이 아니라 negative prompt 로 옮긴다 — 사이드카에서는 그게 가능하다.** 배치의 NEG 는 고정이지만 `gen_keyframe.py --negative` 는 컷마다 바꿔 넣을 수 있다. 올리버 트위스트(09-17)에서 실제로 들은 것: 포장도로·차선·스카이라인에는 `asphalt, tarmac, paved road, painted road markings, yellow line, kerb, power lines, telephone poles, skyscrapers, modern city skyline`, 어른이 오면 안 되는 컷에는 `adult man, grown man, tall man, adult face, stubble`, 옷·벽의 붉은 얼룩에는 `blood, bloodstain, red stains, gore, splatter`. visual 에 "no …" 를 적어 그 사물을 부르는 대신 여기로 보낸다.
- **'road' 한 낱말이 현대 2차선 아스팔트를 깐다.** 올리버 트위스트 S7·S8(09-17): 'a long dusty road of packed earth between hedges' 로 적었는데도 **흰 점선이 그어진 포장도로**가 나왔다(S7 은 검수에서 "원경의 자국" 으로 한 번 통과시켰다가 전체 화면을 다시 보고 뒤집었다). 노면을 사물로 적어야 한다 — "the whole width of the road is packed earth and loose stones with two wagon ruts and a line of grass down its middle". 길 끝의 'a huddle of low tiled roofs and chimney smoke far off' 는 고층 스카이라인을 불렀다 → "a few low cottages of whitewash and ash grey slate standing beside it far off".
- **'pocket books' 는 지갑이 아니라 책더미가 된다.** 올리버 트위스트 S10(09-17)의 페이긴 다락 탁자가 책장과 펼친 책이 있는 서재가 됐다 — 옛말·다의어는 현대 뜻으로 그려진다. 'worn leather wallets' 로 고치자 탁자에 지갑과 손수건이 놓였다.
- **두 인물을 나란히 세우면 하나로 합쳐진다.** 올리버 트위스트 S9(09-17)에서 문간의 올리버(맨머리·보따리)와 도저(실크햇)가 **한 소년**이 되어 실크햇을 쓰고 보따리를 안고 있었다. 사이에 바닥을 넣고("standing a full stride to his right", "a clear gap of bare floor between them") 한쪽에만 있는 소품을 다른 쪽에 없다고가 아니라 **있는 것으로** 적어야 한다 — "his fair head bare with nothing on it" + "the taller boy wearing the top hat". 인원수도 "exactly one old man and six boys, two at the door and four round the table" 처럼 자리별로 나눠 적는다.
- **머리·수염 색을 안 적은 인물은 컷마다 나이가 달라진다.** 올리버 트위스트 S13·S14(09-17)에서 사익스 자산이 "a heavy brutal man of thirty-five … thick stubble" 뿐이라, S13 은 갈색 머리·수염의 서른다섯으로 나왔는데 S14 는 **백발에 흰 수염 난 노신사**가 되어 다른 사람이 됐다. 나이 숫자만으로는 안 되고 **머리와 수염의 색을 자산에 적어야** 컷 사이가 이어진다 — "thick dark brown hair and a short dark brown beard". 곁들여 사이드카 부정어에 `white hair, white beard, grey beard, elderly gentleman` 를 넣으면 한 번에 잡힌다.
- **팔레트의 붉은색은 옷뿐 아니라 산울타리·풀에도 내려앉는다.** 올리버 트위스트 S15(09-17)의 시골길 컷에서 오른쪽 산울타리 한 구간이 통째로 붉게 칠해졌다(시드 셋). 부정어 `blood…` 로는 안 빠지고 — 모델이 그것을 **붉은 잎**으로 그리기 때문이다 — "the hedges on both sides are the same dark brown and ash grey along their whole length" 로 색을 못박고 부정어에 `red hedge, red leaves, red foliage, autumn colours` 를 더해야 줄어든다. 그래도 한 구간은 남아 잎으로 읽히는 선에서 수용했다.
- **풀둑·산울타리 앞은 인물을 앉힌다.** 같은 작품 S8 에서 "standing … with his thumbs hooked in his coat" 라고 두 번 적었는데도 도저가 두 시드 모두 풀둑에 앉았다. 서 있어야 하면 "standing upright on their own two feet with their knees straight and their backs straight" 까지 적고, 앉아도 이야기가 상하지 않으면 **그림을 받아들이고 동작 문장을 앉은 자세로 다시 쓰는 편**이 빠르다(원작의 도저는 길가에서 빈둥대다 만난다).
- **"머리만 보인다" 식의 부분 묘사는 사물에 얼굴을 그린다 — 숨은 인물은 화면 앞쪽 실루엣으로 세운다.** 톰 소여 S6(09-17): "far off at the left edge the tops of two small heads and four eyes show above the edge of a leaning wooden marker" 라 적자 모델이 **비석에 눈 두 개를 그려 넣고** 아이 셋을 들판에 따로 세웠다. 같은 작품 S12 도 "pressed flat against the wall … only his face and one hand showing" 이 무시돼 톰이 인전 조 옆에 나란히 섰다. 두 컷 다 **"seen from close behind the crouching boys: the backs of their heads and shoulders fill the two lower corners … beyond them the man stands small in the middle of the frame"** 로 시점을 바꾸자 한 번에 나왔다. 숨는 장면은 '무엇이 가려져 보이지 않는가'가 아니라 **누가 카메라 앞에 크게 있고 누가 뒤에 작게 있는가**로 적는다.
- **자산에서 지운 소품은 컷 대사에도 지워야 한다(심봉사 안대 규칙 재확인).** 톰 소여 S12(09-17)에서 injun_joe 자산의 'a red headband' 를 지웠는데도 붉은 머리띠가 그대로 나왔다 — 컷의 visual 에 "the lean man … with the long black hair and the red headband" 이 남아 있었기 때문이다. 자산을 고칠 때는 `grep` 으로 모든 beat 를 함께 훑는다.
- **한 컷에 네 사람 이상이 서면 특징이 서로 옮겨 붙는다.** 허클베리 핀 S9(09-17)에 사기꾼 둘·헉·짐 넷을 넣었더니 **왕의 흰 구레나룻이 짐에게 옮겨 가** 짐이 백발 노인이 되고, 헉은 둘로 늘고, 사기꾼은 하나만 나왔다(인물 넷을 전부 자세히 적은 1,000자짜리 대사였다). **cast 에서 그 컷에 꼭 필요하지 않은 사람을 빼고 세 사람으로 줄이자 한 번에 맞았다.** 사람이 넷 이상 필요하면 뒤쪽 사람은 자세히 적지 말고 "두 사람이 뒤에 서 있다" 정도로 뭉뚱그리거나 컷을 나눈다.
- **인물의 옷 색을 안 적으면 컷마다 바뀌고 다른 인물과 겹친다.** 허클베리 핀 S6 에서 헉의 셔츠가 파랑이 되어 짐의 파란 셔츠와 같아졌다(앞 컷들은 흰색). 자산에 'a cast-off **off-white linen** shirt' 로 색을 박자 S7 부터 바로 돌아왔다 — 머리·수염 색 규칙(올리버 사익스)과 같은 자리다.
- **그림만 떼어 놓고 봤을 때의 위아래를 본다.** 같은 작품 S4 는 원작대로 짐이 놀라 웅크리고 헉이 선 순간인데, 정지 화면으로는 흑인 어른이 백인 소년 앞에 무릎 꿇은 것처럼 읽혔다. 이야기가 맞더라도 **"두 사람의 얼굴이 같은 높이"** 를 못박고 앉을 사람은 통나무·의자에 앉히면 뜻이 그대로면서 읽기가 바뀐다(부정어에 kneeling/bowing/cowering 도 함께).
- **오르내리는 '방향'은 그림에 잡히지 않는다 — 결과 상태로 적는다.** 십오 소년 표류기 S1(09-18)에서 "널판을 걸어 올라 배에 오른다"를 두 시드·두 문구로 적었는데 둘 다 **널판을 내려오는** 그림이 나왔다(한 번은 널판이 부두에 평평히 눕기까지 했다). "이미 갑판 난간에 늘어서서 부두를 내려다본다"로 **도착한 상태**를 적자 한 번에 맞았다. 들어간다/나온다·오른다/내린다처럼 방향이 요점인 컷은 그 동작을 그리려 하지 말고 그 다음 순간의 배치를 적는다.
- **배 밖에서 본 시점과 갑판 위 인물을 한 컷에 적으면 배가 둘이 된다.** 같은 작품 S2 에서 "seen from a little off her stern quarter" 와 "두 소년이 고물 난간에 서서" 를 함께 적었더니 **배 두 척**이 나왔다(아이들이 탄 배 + 멀리 떠가는 배). 시점을 갑판 하나로 통일하고 "화면에 배는 하나뿐" 을 못박아 해결. 한 컷에 **바깥 시점과 안쪽 시점을 섞지 않는다.**
- **큰 수는 무시된다 — 인원을 줄이고 '일곱 중 다섯'처럼 적는다.** 같은 작품 S11 의 투표 컷에서 "아홉이 팔을 들어 올린다"를 적었는데 **손이 하나만** 올라갔다. 사람을 일곱으로 줄이고 "일곱 중 다섯이 팔을 곧게 들어 같은 높이로, 나머지 둘은 손을 내린다"로 적자 다섯 팔이 한 줄로 섰다. 수를 지키게 하려면 **전체 인원을 그릴 수 있는 만큼으로 줄이고 든 쪽과 안 든 쪽을 함께** 적는다.
- **자산의 'bare feet' 는 눈 오는 컷까지 따라온다.** 같은 작품 S12 에서 겨울 장작 컷의 아이들이 눈밭을 맨발로 걸었다. 그 컷의 visual 에 "발을 자루천으로 싸고 발목에 끈으로 묶었다"를 적으면 일부는 고쳐지지만 전부는 아니다 — 계절이 바뀌는 작품은 **인물 자산에 신발을 적지 않고** 컷마다 발을 적는 편이 낫다.
- **'~에서 키를 잡는다'는 자세가 안 잡힌다 — 사물의 자리로 적는다.** 같은 작품 S4 에서 "standing at the spoked wheel with both hands gripping the spokes" 가 **키 앞에 서서 팔을 뒤로 걸친** 그림을 냈다. "키가 그와 카메라 사이에 통째로 놓이도록 반대편에 서고, 얼굴은 키 위로 보인다"로 **사물과 카메라의 관계**를 적자 조타 자세가 나왔다.
- **낭독의 뜻이 그림에서 뒤집히는 자리를 먼저 찾는다 — 구하는 장면·가르치는 장면.** 로빈슨 크루소 S11(09-18)의 "쫓기던 사람을 구해 주었다"가 **총을 겨눈 그림**으로 나왔다(문구는 "musket held level across his body… the young man down on one knee"). 무기를 든 사람과 무릎 꿇은 사람을 한 컷에 두면 모델은 그것을 위협으로 그린다. 고친 문구: 총은 "held straight down at his side, its muzzle pointing down into the sand away from everybody", 상대는 "just risen to his feet", 그리고 **"두 사람의 얼굴이 같은 높이"** + 두 손이 마주 잡히는 순간. 같은 작품 S12 는 크루소를 걸상에, 프라이데이를 맨바닥에 앉힌 **내 대사 자체가** 위아래를 만들었다 — 둘 다 바닥에 마주 앉히자 해결. 허클베리 핀 S4 와 같은 자리이므로 규칙으로 굳힌다: **인물 둘이 한 컷에 있을 때 앉은 자리·선 자리·손에 든 것을 먼저 보고, 정지 화면만으로 위아래가 생기면 이야기가 맞더라도 고친다.**
- **바닷가에 누운 사람은 반드시 등을 대고 그려진다.** 로빈슨 크루소 S2 에서 'lying on his front', 'his chest and cheek flat against the sand', 'his back uppermost' 에 부정어(lying on his back, sunbathing)까지 넣고도 두 시드 모두 **등을 대고 누웠다**. 다만 팔을 벌리고 머리를 젖힌 판은 '쓰러진 것'으로 읽혀 수용할 만하다 — 엎드림을 포기하고 **팔의 자세로 탈진을 말하는 편**이 빠르다.
- **거인과 소인은 한 화면에 나란히 세우면 반드시 정규화된다 — 거인의 몸 일부로 화면을 채워야 크기가 선다.** 걸리버 여행기(09-18)에서 "little people each no taller than the man's thumb is long" 을 자산·컷에 모두 적었는데도 S2·S4 에서 소인들이 **무릎 높이의 빨간 고깔 난쟁이**로 나왔다(걸리버는 서 있고 소인은 그 옆). 통한 구도는 셋이다: ① **거인의 몸 일부를 앞쪽에 크게** 두기 — "one enormous buckled shoe and the leg above it fill the right half of the frame… thirty little people, none taller than the buckle of that shoe"(S7), "the side of that face fills the left third of the frame… the horse and its rider together no taller than this man's eye is wide"(S8); ② **뒤에서 본 시점** — 수레에 묶인 걸리버를 발치에서 잡고 밧줄을 끄는 두 줄이 성문까지 뻗어 가는 구도(S6)가 이 작품 최고 컷이 됐고, 함대를 끄는 컷(S11)도 같은 방식으로 통했다; ③ **사물로 말하기** — 회중시계·작은 배처럼 크기를 아는 물건을 소인 곁에 두면 잘 나온다(S10). 반대로 **소인 서넛을 거인의 얼굴 곁에만 두면 모델이 그들을 얼굴 크기에 맞춰 키운다** — 그런 컷은 소인을 아예 빼고 실·말뚝 같은 흔적만 남기는 편이 낫다(S2). 그리고 "the face fills the whole frame" 류의 **극단적 클로즈업 지시는 세 판 모두 무시됐다** — 이 모델에게 클로즈업은 프롬프트가 아니라 **무엇을 화면 밖으로 내보내느냐**로 만든다.
- **부품 이름이 도구를 부른다 — 'hammer', 'pan', 'lock' 은 총의 부품이라도 망치·냄비·자물쇠가 된다.** 보물섬 S3(09-18)에서 부싯돌 권총을 "a hammer holding a flint over the pan" 이라 적자 권총은 제대로 나왔지만 **장도리 한 자루가 바닥에 함께** 놓였다. 옛 무기·기계의 부품은 이름 대신 생김새로 적는다: "a curved steel piece that holds a flint, set above a small brass plate". 같은 작품 S11 의 'paper cartridges' 도 **놋쇠 탄피 더미**가 됐다 — 'cartridge' 는 현대 탄약이다. "small twists of grey paper, each holding a charge of powder… no metal anywhere among them" 처럼 재료와 모양으로만.
- **'name board'·'nameplate' 는 간판과 같은 뿌리 — 글자를 쓴다.** 보물섬 S5(09-18)에서 배의 고물을 "her name board at her stern is a plain unpainted panel" 이라 적자 그 판에 **작은 가짜 글자**가 찍혔다(부정 프롬프트의 text·signboard 를 뚫고). 이름·글자가 들어갈 자리를 암시하는 낱말(sign, board, plate, label, tag)은 아예 쓰지 않고, 필요하면 "a plain strip of dark wood across her stern" 처럼 재료만 적는다.
- **목발·의족처럼 팔다리를 대체하는 물건은 '없는 부위'를 사물 뒤에 숨기면 한 판에 된다.** 보물섬 S6(09-18): "standing behind a lashed water cask that hides him from the waist down" 은 물통이 옆으로 비켜서 두 다리가 다 나왔지만, **"a big lashed water cask on the deck directly in front of him between him and the camera… only his upper body shows above it; the head of a stout wooden crutch rises under his left armpit and its shaft goes down out of sight behind the cask"** 로 물통의 자리를 카메라 기준으로 못박자 목발이 겨드랑이에 제대로 섰다. 피터 팬의 갈고리(손을 대체)는 네 시드로도 안 됐지만, 다리는 **가리기**가 가능해서 다르다 — 대체 부위가 화면 아래쪽이면 사물로 가리고, 손처럼 위쪽이면 등 뒤로 돌린다.
- **'track' 은 철길을 깐다 — 숲길은 'footpath' 로.** 보물섬 S13(09-18)에서 "a track through the pine wood… two ruts worn by dragged timber" 가 **쇠레일과 침목이 깔린 철로**를 냈다(실버가 레일 위를 걷는다). 'road' 가 아스팔트를 까는 것(올리버 트위스트)과 같은 뿌리 — 길 낱말은 시대를 정하지 않는다. 옛 숲길은 "a narrow footpath of packed earth, no wider than a man's shoulders, with roots crossing it" 처럼 **폭과 재료와 뿌리**로 적고, 'track'·'trail'·'ruts' 는 쓰지 않는다. 같은 컷의 'spades and picks' 옆에 **쇠스랑**이 섞여 나온 것도 도구 이름이 이웃 도구를 부른 것.
- **여럿이 한 방향으로 가는 장면은 '맨 뒤 사람의 등 뒤에서' 잡는다 — 방향과 크기를 한꺼번에 푸는 구도.** 세 작품에서 같은 실패가 났다: 십오 소년 S13·보물섬 S13 은 앞장선 이는 멀어지는데 뒤따르는 무리가 카메라 쪽으로 걸어왔고(문구에 'walking behind him' 을 적어도 그렇다), 톰 소여 S6·S12 는 숨어 보는 아이가 표적 옆에 나란히 섰다. 여섯 컷 모두 **"seen from close behind X: the back of X's head and shoulders fills the lower right/left of the frame… ahead of X, every one of them with his back to the camera, walking away up the path"** 로 바꾸자 한 판에 맞았고, 걸리버 S6·S11 에서는 같은 구도가 거인·소인의 크기까지 잡아 주었다. 인물들의 **상대 방향**이 요점인 컷은 처음부터 이 구도로 쓴다. 삼총사 S5(09-18)에서는 같은 구도가 **색 번짐**까지 막았다 — 넷과 다섯, 아홉 명이 마주 서자 두 판 모두 달타냥이 근위대의 노란 외투와 강철 모자를 얻어 입고 파란 무리에 노란 외투가 섞였는데, 넷을 뒷모습으로 앞에 세우자 옷색이 옮겨 갈 얼굴·자리가 없어져 한 판에 맞았다. **한 컷에 다섯 명이 넘으면 절반을 등 뒤 구도로 돌린다.**
- **'sword' 는 칼집을 아무리 적어도 칼날을 그린다 — 칼집과 자루만 적는다.** 삼총사 S1·S3(09-18)에서 "the long sword hangs sheathed in its scabbard, the whole blade inside the scabbard" 에 부정어(drawn sword, bare blade, unsheathed)까지 넣었는데 두 시드 모두 **칼을 뽑아 들거나 칼날이 칼집 없이 허리에 늘어졌다**. 낱말 'sword' 자체가 칼날을 부르기 때문이다. 아이들 영상에서 칼이 뽑히면 안 되는 컷은 자산·컷 모두에서 'sword' 를 지우고 **눈에 보이는 것만** — "a dark leather scabbard hanging at his left hip with a plain steel hilt showing at its top" — 적는다(뽑는 컷에서만 'sword… drawn' 을 쓴다). 'hoe'→삽, 'lamp'→전기등과 같은 자리: **물건의 이름이 아니라 물건의 겉모습을 적는다.** — 그런데 'scabbard'·'hilt' 로 바꿔도 세 번째 판(S1·S3·S5)에서 **칼집 없는 맨 칼날이 허리에 걸렸다**. 다만 같은 문구가 S2·S4 에서는 통해 칼집이 허리 가죽 주머니로 나왔다 — 시드 다섯 중 둘. **믿을 수 없는 문구**라는 뜻이다. 처방: 칼이 뽑히면 안 되는 컷은 **무기를 자산·컷에서 아예 없앤다**(손은 '허리띠에 걸쳐'·'빈 손'으로), 뽑는 컷 하나에서만 'sword… drawn' 을 쓴다. 인물의 신분은 망토·모자·색으로 충분히 선다.
- **모자의 'crown'(정수리)은 왕관을 부른다 — 동음이의 낱말 목록에 추가.** 삼총사 S10(09-18)에서 길에 떨어진 모자를 "lies crown down with its feather bent" 이라 적자 길 위에 **금 왕관**이 놓였다. 'bow'→활(호미의 표류), 'hammer'→장도리(보물섬)와 같은 뿌리: 낱말의 다른 뜻이 사물이면 그 사물이 온다. 모자가 뒤집힌 것은 "upside down with its brim to the sky", 모자 정수리는 'the top of the hat' 로 적는다. 큐에 든 80일간 S1·S15 의 'sits crown down' 도 미리 고쳤다.
- **공구 이름은 현대 공구를 부른다 — 'pliers' 는 파란 플라스틱 손잡이 펜치가 된다.** 삼총사 S13(09-18)의 1620년대 세공 작업대에 "a pair of pliers" 라 적자 **파란 고무 손잡이의 현대 펜치**가 놓였다. 'hoe'→삽, 'hammer'→장도리, 'cartridge'→탄피와 같은 자리: 옛 도구는 이름을 쓰지 말고 **재료와 손잡이와 모양**으로만 적는다 — "a pair of narrow iron tongs with plain wooden grips", "a small mallet with a round wooden head". 부정어에 modern pliers/plastic handles 를 함께 넣는다.
- **'발자국 흔적'과 '거울이 불꽃을 되비친다'는 그을음 발자국과 거울 속 불길이 된다.** 삼총사 S15(09-18)의 빈 무도회장에 "the marks of many feet on the polished floor", "the mirrors give back the few low flames", "long runs of wax down the candle stubs" 를 적자 **검은 발자국이 온 마루에 찍히고 거울마다 불길이 타고 촛농이 탁자로 흘러** 홀이 불타는 그림이 됐다. 흔적·반사·흘러내림은 모델이 과장한다 — 빈 방의 여운은 사물 하나(바닥의 흰 장갑 한 짝, 빈 칸의 실 끝)로 말하고, 거울은 "shows only the pale wall opposite" 로, 초는 "burned down short but standing straight with a small steady flame" 로 적는다.
- **카메라를 향한 걸음·질주는 클립에서 반드시 커진다 — 한 걸음으로 끊거나 제자리로 바꾼다(감자 S3 규칙 재확인).** 삼총사 S7(09-18)의 "walk slowly forward toward the camera… growing only slightly larger" 는 끝 프레임에서 네 사람의 장화가 프레임 아래로 잘렸다. 동작을 "each of them takes one single short step forward and stops… a clear band of street between them and the bottom edge" 로 고쳐 patch_clip 하자 해결. 같은 위험이 있던 S9(달려오는 기수 넷)는 배치가 클립을 굽기 전에 "the riders keep their exact size and place… the cloaks ripple and the dust drifts" 로 **미리** 고쳐 한 번에 통과했다 — 키프레임 검수 때 '다가오는' 동작이 보이면 클립이 나오기 전에 motion 을 바꿔 두는 편이 재생성 12분을 아낀다.
- **열린 문 너머의 실내 물건을 적으면 그 물건이 바깥에 선다 — '창밖' 규칙의 반대 방향.** 장발장 S4(09-19)에서 바깥 문간의 사내를 그리며 "through the door behind him the corner of the long table with its white cloth shows, and the glow of the hearth beyond" 이라 적자 **식탁과 의자 넷이 집 밖 눈밭에** 차려지고 불은 문지방에 놓였다. 마지막 잎새의 담쟁이가 방 안으로 기어든 것과 같은 뿌리 — 모델은 안팎을 나누지 못한다. 카메라가 밖에 있으면 안은 **빛으로만** 적는다: "only the dull yellow glow of the room, warm and even, with no furniture to be made out in it", 그리고 바깥 바닥을 "bare frozen earth with nothing standing on it" 으로 못박는다. 안의 물건이 요점이면 카메라를 안으로 들여 별도 컷으로 만든다.
- **한 인물의 소지품은 두 사람 컷에서 상대에게 옮겨 붙는다 — 소지품을 두 사람 모두에게서 떼어 놓는다(벙어리 삼룡이의 담뱃대 규칙 보강).** 장발장 S6(09-19)에서 valjean 자산의 'a canvas knapsack on one strap, a thick knotted walking stick' 이 식탁 건너편의 **주교에게 배낭과 지팡이를 지웠다**. 앉아서 먹는 컷에서 장발장이 그것을 들고 있을 이유도 없다. **첫 처방(소지품의 자리를 따로 적기)은 실패했다** — "lean together against the wall… neither man wears or holds them" 에 부정어(priest wearing a backpack)까지 넣은 둘째 판에서 **배낭 멘 주교가 둘**이 되고 지팡이까지 들었다: 낱말이 프롬프트에 있는 한 소지품은 사람에게 붙고, 붙을 사람을 하나 더 만든다. 통하는 처방은 **소지품 없는 별도 인물 자산**이다(소공녀의 sara/sara_poor 와 같은 방식) — 'valjean_indoor: … his hands empty and nothing on his back' 를 만들어 앉거나 서서 빈손인 컷마다 그 자산을 배정하고, 컷의 visual 에서 소지품 낱말을 **한 번도** 쓰지 않는다. 인물 자산에 붙박이 소지품을 넣을 때는 처음부터 두 벌(지닌/빈손)로 만든다.

- **다섯 사람에 '얼굴은 하나만'은 실행되지 않는다 — 배역이 뒤바뀐다**(장발장 S10 실측): '헌병 셋의 등 뒤에서, 장발장도 등, 주교만 정면' 을 적었더니 문간에 장발장 얼굴이 서고 가운데 등이 주교(자주 모자 위에 샤코 합성)가 됐다. 처방은 **네 사람으로 줄이고 자리를 사물로 못 박기** — '주교는 문간 안쪽에서 정면, 그 앞 계단에 장발장은 뒤통수와 어깨만, 헌병 둘은 좌우 가장자리에 크게 잘려서' 로 쓰고 부정어에 'shako with purple top, soldier wearing a skullcap, ragged man facing the camera' 를 넣자 한 번에 맞았다. 같은 컷의 둘째 판에서는 '문 뒤의 식탁'(the long table shows behind the old man)이 **마당 앞쪽에** 그려졌다 — 바깥에서 문을 보는 컷에는 실내 가구를 한 낱말도 적지 말고 '방의 어두운 초록 그늘' 같은 빛·색만 적는다(§7 문간 교훈의 재확인).

- **'unlit candlestick' 은 켜진다** — 'candlestick' 이라는 낱말에 초와 불꽃이 따라온다. 장발장 S13·S14 에서 'unlit', 'without any flame', 부정어 'lit candles, candle flame' 을 다 넣어도 두 판 모두 대낮 길 위에서 촛불이 켜졌다. 꺼진 촛대가 필요하면 **초를 없앤다** — 'two small silver candle holders with their sockets empty' 처럼 초·불꽃 낱말을 한 번도 쓰지 않는다(공주와 완두콩의 '거울 속 불꽃', 상록수 '종 기둥' 과 같은 계열: 사물 이름이 딸린 상태를 부른다).

- **벽난로 위 선반의 촛대는 지워지지 않는다**(장발장 S15, 세 판): '선반이 비어 있다', '선반이 없다', 부정어 'mantelpiece, candlesticks' 를 다 써도 벽난로가 있는 한 선반과 촛대 둘이 붙어 나왔다 — 이 작품의 앞 컷 프롬프트(은촛대)와 무관하게 '벽난로' 자체가 촛대를 부른다. 이야기상 촛대가 사라진 방을 보여 주려면 **벽난로를 화면 밖으로** 빼고(식탁과 문 쪽만) 촛대 없음을 다른 사물(빈 자리의 먼지 자국)로 말해야 한다. 세 번째 판부터는 수확이 없으니 두 판에서 멈춘다.

- **'red earth' 는 땅 전체를 새빨갛게 칠한다**(80일간 S5·S6 실측): 팔레트가 아니라 컷의 visual 과 장소 자산에 적은 'red earth', 'red rubble' 도 인도의 라테라이트가 아니라 선홍색 카펫이 됐다. 흙·길·바위의 붉은 기는 'dull orange-brown' 으로 적고, 붉은색은 정말 붉은 작은 사물(벽돌 한 면, 군복 한 벌)에만 남긴다. 인물 자산의 'side whiskers' 는 컷마다 턱수염으로 자라난다(포그 S3·S5·S6) — 얼굴 털은 'a small neat moustache and a clean-shaven chin' 처럼 있는 것과 없는 것을 함께 적는다.

- **'stands as one solid wall' 도 직유다** — 'like a' 가 없어도 'as one solid wall' 은 벽을 세운다(80일간 S5 3판: 정글 대신 왼쪽에 잿빛 돌담). 'as one ~', 'stands as a ~' 꼴을 check_craft SIMILE 에 추가했다. 빽빽함은 'unbroken and close-grown from the ground up' 처럼 물리로 적는다.

- **잠수복·갑옷·붕대처럼 '몸을 덮는 옷' 컷에는 인물 자산을 cast 에서 뺀다**(해저 2만리 S9 실측): aronnax(프록코트) 자산이 diving_suit 와 함께 들어가자 헬멧 아래 프록코트가 나오고, '같은 옷의 둘째 인물'은 헬멧 없는 맨얼굴이 됐다. 덮개 옷 자산만 남기고 visual 에 '헬멧이 온 머리를 덮어 얼굴·머리칼·평상복이 어디에도 안 보인다' 를 인물마다 적는다.

- **신체 일부 클로즈업(턱·손·장화·손가락)에는 인물 자산을 cast 에서 뺀다**(걸리버 S4 실측, 해저 S9 와 같은 결): '얼굴이 화면 왼쪽을 가득 채운 옆얼굴, 가슴 위의 엄지만 한 사람들' 을 적어도 cast 에 gulliver 자산이 있으면 전신이 서 있는 그림이 나오고 소인은 무릎 높이가 된다. 자산의 spec 이 '사람 하나'를 통째로 부르기 때문이다. 처방: 그 컷의 cast 에서 인물 자산을 빼고 visual 에 '코트의 천이 화면 아래 3분의 2를 채우고, 턱과 목수건만 위쪽 가장자리로 들어온다', '큰 사람의 전신은 어디에도 없다' 를 적고 부정어에 'full body, standing man, whole figure' 를 넣는다. 규모 비교는 '단추 하나가 수레바퀴만 하다' 처럼 같은 화면의 사물로 한다.

- **안경도 소지품처럼 옆 사람에게 옮겨 붙고, 낱말을 빼도 자산의 안경이 건너간다**(지구 속 여행 S4, 세 판): 안내인에게 'bare of any spectacles' 를 적으면 안경이 오고(unlit 촛대와 같은 꼴), 낱말을 빼고 '면도한 맨얼굴' 만 적으면 안경은 빠지지만 같은 컷의 travellers 합성 자산에 든 교수의 'small round spectacles' 가 여전히 둘 중 누구에게든 갈 수 있다. 세 사람 합성 자산에서 한 사람에게만 안경을 주려면 **안경 낱말을 그 사람의 첫 어구에 붙이고**("the spectacled thin man of fifty") 나머지는 얼굴을 '맨얼굴' 로 적는다. 또 '조용한 분화구' 를 적고 eruption 부정어를 넣어도 두 판 다 분화구에 불빛이 났다 — 'volcano'+'crater' 가 함께 있으면 불이 따라오니, 오르는 컷에는 'crater' 대신 'the snow-filled hollow at the top' 처럼 쓴다.

- **세 사람 합성 자산(travellers) + 소품 든 컷은 사람이 넷이 된다**(지구 속 여행 S13, 두 판 모두): '정확히 세 사람 — 노인·큰 사내·젊은이 하나, 둘째 젊은이 없음' 을 적고 부정어에 four people·twins 를 넣어도 젊은이(원판) 또는 노인(2판)이 복제됐다. 세 사람이 한 컷에 다 얼굴을 보이며 서는 구도는 피하고, **둘은 등을 보이게 하거나 한 사람은 화면 밖에 두는** 편이 확실하다(허클베리 핀 S9 의 '넷 이상 전이' 교훈이 셋에서도 소품이 있으면 되풀이된다).

- **'부러진 지팡이 반쪽' 은 그려지지 않는다 — 'cane' 낱말이 통짜 지팡이를 부른다**(지킬 S8 두 판·S9): '반쪽', '부러진 단면이 뾰족한 흰 나무', '손잡이 없음', 부정어 whole cane·crook handle 을 다 넣어도 은 손잡이 달린 온전한 지팡이가 나왔고, 둘째 판은 갈고리 손잡이까지 붙었다. 'cane/walking stick' 은 자산 spec 에 있는 한 통째로 온다. 토막을 원하면 **'cane' 낱말을 빼고** 'a short broken piece of polished dark wood, the length of a hand, one end splintered' 처럼 막대로 적는다 — **S9 3차(1711)에서 검증됨**: cast 에서 cane 자산을 빼고 본문의 'cane' 을 전부 지우자 한 번에 손 길이의 부러진 토막이 나왔다. 같은 원리: 자산 spec 의 사물 이름은 '온전한 그 사물' 을 부르므로, 부서진·반쪽·조각 상태는 이름 없이 재료와 크기로 적는다.

- **'의자에 걸쳐 놓은 코트' 는 앉은 사람이 된다**(지킬 S15 두 판): 'lying slack across its back and one arm', '빨래처럼 빈 옷', '손·몸 없음', 부정어 hands·gloves·headless figure 를 다 넣어도 팔걸이에 손(1판)·장갑(2판)을 얹은 머리 없는 인물이 나왔다. 팔걸이의자 + 어깨 자리의 옷은 '사람이 앉은 자세' 그 자체라 낱말로는 못 막는다. 3판은 **코트를 의자 등받이에 옷깃으로 걸어 소매가 바닥까지 늘어지게**(옷걸이의 옷 꼴) 바꿨다 — **3판(1721)에서 검증됨**: 코트는 벽의 옷걸이에 빈 채로 걸리고 의자는 비었다(등받이가 아니라 벽에 걸렸지만 '사람 없는 옷' 은 확실). 빈 옷을 보여 주려면 의자·침대처럼 몸이 놓이는 자리가 아니라 **옷걸이·못·빨랫줄** 에 건다.

- **'액자 안의 초상' 자산은 벽에 건다 — 이젤 위 그림은 액자 없는 캔버스로**(도리언 S1 실측): portrait 자산 spec 에 'inside a wide carved gilt frame' 이 있으면 '이젤이 그 그림을 든다' 고 적어도 액자 그림은 벽에 걸리고 이젤에는 빈 캔버스가 선다. 그리는 중·완성 직후 컷(S1·S3)은 자산을 빼고 'a tall unframed canvas standing on the easel's ledge, the raw edges of the canvas showing round the paint; the wall behind the easel is bare' 로 적었더니 한 번에 맞았다. 액자는 벽에 거는 컷(S4 이후)에만 준다. 같은 컷에서 화가의 수염이 소파의 신사에게 옮겨 붙었다 — 수염 있는 인물과 없는 인물이 한 컷이면 없는 쪽에 'a clean-shaven chin' 을 적는다.

- **장소 자산의 이름('gentlemen's club')이 간판 글자를 부른다**(도리언 S11): 부정어에 text·signboard 가 다 있어도 건물 위에 'GENLETMEN'S CLUB' 이 새겨졌다 — 'shop'→간판 교훈과 같은 결. 장소 spec 은 이름 대신 생김새로('a tall stone porch with pillars and two gas lamps'). 글자가 화면 가장자리 띠에만 있으면 재생성 대신 **crop** 이 싸다: 원본을 보관하고 그 띠를 잘라 9:16 으로 다시 맞춰 720×1280 으로 저장(도리언 S2 의 노란 테두리, S11 의 간판 모두 이렇게 해결).

- **'거꾸로 매달려 기어 내려간다' 는 그려지지 않는다 — 머리가 위인 '벽 타기' 까지가 한계**(드라큘라 S7 두 판): 'head downward' 도, 결과 서술('구두 밑창이 가장 높고 흰 머리가 소나무 쪽으로 늘어진다·망토 자락이 창턱 쪽')도 소용없었다. 1판은 아예 벽에 기대 선 사람, 2판은 창 아래 벽에 발톱으로 매달려 오르는 자세(채택). 도마뱀 자세의 핵심('벽 바깥·발톱·망토·아래로 떨어지는 성벽')은 2판 서술로 나오니, 거꾸로는 포기하고 낭독만 그대로 두는 편이 낫다 — 그림책에서 방향 어긋남은 눈에 덜 띈다.

- **'천 아래의 형체' 는 침대의 사람이 된다 — 그리고 긍정문의 'no face, no pillow' 가 얼굴과 베개를 부른다**(프랑켄슈타인 S6 두 판): 'a huge shape under a sheet on a table' 은 두 판 다 베개 베고 잠든 소년(얼굴·양말 발)이 됐고, 자산 spec 에 'no head, no face, no pillow, no feet' 를 적은 2판이 오히려 더 또렷이 그렸다(부정어는 부정 프롬프트에만 — 규칙을 스스로 어겼다). 3판 처방: 사람 냄새 나는 낱말(shape·sheet over the chest·feet)을 다 빼고 **'끈 세 개로 묶은 긴 꾸러미(bundle wrapped in sheeting, bound with cords)'** 로 사물화한다 — **3판(2011)에서 검증됨**: 끈 세 개로 묶인 회색 꾸러미가 탁자 길이로 놓이고 얼굴·발·베개가 전혀 없다.
