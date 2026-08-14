#!/usr/bin/env python3
"""docs/SPEC.md 대조 테스트 — 구현이 명세와 어긋나면 여기서 걸린다.

외부 API·GPU 를 쓰지 않는다. 규격 상수와 검증기 동작만 본다(수초 내 종료).
실행: venv/bin/python tests/test_spec.py
"""
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "scripts"))

FAIL = []


def check(name, cond, detail=""):
    print(f"  {'OK ' if cond else '!! '}{name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        FAIL.append(f"{name}: {detail}")


def section(t):
    print(f"\n[{t}]")


# ---------- 1. 대본 규격 ----------
section("대본 규격 (SPEC §2)")
import write_script as W  # noqa: E402

check("종결어미 계열 8슬롯", len(W.ENDING_PLAN) == 8, str(W.ENDING_PLAN))
check("마지막 슬롯 합니다체", W.ENDING_PLAN[-1] == "합니다체", W.ENDING_PLAN[-1])
check("톤 6종", sorted(W.TONE_RULES) == sorted(
    ["담담", "따뜻", "서늘", "긴장", "속삭임", "생동"]), str(sorted(W.TONE_RULES)))

W.LEN_MIN, W.LEN_MAX = 29, 40
ok_sent = "어두운 방에 놓인 약병 하나가 창으로 든 빛을 조용히 받습니다"
end = "소설 날개에서 만날 수 있습니다"
check("한다체 종결 불합격", any("한다체" in m for _, m in W.validate(["방문을 조용히 닫는다"], "", [])))
check("고어체 분류", W.ending_class("바라보았노라") == "고어체", W.ending_class("바라보았노라"))
check("길이 하한 검출", any("길이" in m for _, m in W.validate(["짧다"], "", [])))
check("마무리 문구는 길이 상한 예외",
      not W.validate([ok_sent, "빈 방과 젖은 골목을 지나서, " + end], end, []),
      str(W.validate([ok_sent, "빈 방과 젖은 골목을 지나서, " + end], end, [])))
check("두문자어 통과(KEI)",
      not [m for _, m in W.validate(["이 책은 KEI 도서관에서 만나볼 수 있습니다"], "", [])
           if "한국어" in m])
check("영문 오염 검출",
      any("한국어" in m for _, m in W.validate(["Here is a thinking process for this task"], "", [])))

section("사실 검증 3중 (SPEC §2)")
facts = "[백과 설명]\n1936년 조광에 발표되었다. 33번지 방에서 아내와 산다."
check("자료에 없는 수치 검출",
      any("수치" in m or "수량" in m
          for _, m in W.fact_issues(["스물아홉 해를 그 방에서 보냈습니다"], facts)))
check("자료에 있는 수치 통과", not W.fact_issues(["1936년 그 방에는 아무도 없었습니다"], facts))
check("메타 어휘 검출(소개형)",
      len(W.meta_issues(["문학동네 김애란의 소설입니다", "빈 방", "끝 " + end], end)) == 1)
check("지시어 누출 검출",
      len(W.leak_issues(["*별표*는 강조를 나타내며 핵심을 전달한다", "빈 방에 남은 그림자"])) == 1)
check("강세 지시문에 낱말이 없다", "별표" not in W.EMPHASIS_RULE, W.EMPHASIS_RULE)
check("메타 어휘 마지막 문장 예외",
      not W.meta_issues(["빈 방에 남은 그림자", "이 책은 KEI 도서관에서 만나볼 수 있습니다"],
                        "이 책은 KEI 도서관에서 만나볼 수 있습니다"))

# ---------- 2. 영상 규격 ----------
section("영상 규격 (SPEC §3)")
import review_output as R  # noqa: E402

check("길이 명세 45±3", (R.SPEC_SEC, R.SPEC_TOL) == (45.0, 3.0), f"{R.SPEC_SEC}±{R.SPEC_TOL}")
check("감속 상한 1.5", R.MAX_SLOWDOWN == 1.5, str(R.MAX_SLOWDOWN))


def frames(d):
    import math
    f = max(81, math.ceil(d * 24 / 1.5))
    return f + (4 - (f - 1) % 4) % 4


over = [d for d in (3.5, 4.4, 5.2, 5.7, 6.4, 7.1, 8.5) if d / (frames(d) / 24) > 1.5]
check("프레임 올림이 감속 상한을 지킨다", not over, f"초과: {over}")

section("TTS 톤 (SPEC §2)")
import tts_render as T  # noqa: E402

check("톤 이름이 하네스와 일치", sorted(T.TONES) == sorted(W.TONE_RULES))
check("텐션 곡선 8슬롯", all(len(v) == 8 for v in T.ARCS.values()))
ssml = T.build_ssml("빈 방에 *약병* 하나", "서늘", 3)
check("강세가 emphasis 태그로", "<emphasis level='strong'>약병</emphasis>" in ssml)
check("prosody 에 곡선 반영", "rate='-5%'" in ssml, ssml[:160])
try:
    ET.fromstring(ssml)
    xml_ok = True
except Exception as e:
    xml_ok, xml_err = False, str(e)
check("SSML 이 XML 로 파싱된다", xml_ok, "" if xml_ok else xml_err)

# ---------- 3. 제작 대상 판정 ----------
section("제작 대상 판정 (SPEC §1)")
import fetch_book_facts as F  # noqa: E402
import refill_queue as Q  # noqa: E402

check("세계 단서 하한 고전 4 / 현대 5",
      (Q.WORLD_MIN_CLASSIC, Q.WORLD_MIN_MODERN) == (4, 5))
thin = "[출판사 소개]\n젊은 거장의 신작. 베일에 가려져 있던 그 작품이 마침내 공개된다."
rich = "[줄거리와 배경]\n1930년대 경성, 33번지 어두운 방에서 비 내리는 골목을 내다본다. 겨울 아침."
check("홍보문뿐인 자료는 하한 미만", F.world_material(thin) < Q.WORLD_MIN_MODERN,
      str(F.world_material(thin)))
check("세계가 있는 자료는 하한 이상", F.world_material(rich) >= Q.WORLD_MIN_CLASSIC,
      str(F.world_material(rich)))
check("민감 소재 차단", Q.reason_to_skip({"title": "소년이 온다", "author": "한강"}, set()) != "")
check("작품ID 는 ASCII", F.slug("날개").isascii() and F.slug("메밀꽃 필 무렵").isascii(),
      F.slug("메밀꽃 필 무렵"))

# ---------- 4. 야간 자동화 ----------
section("야간 자동화 (SPEC §5)")
nb = (BASE / "scripts" / "night_batch_v2.sh").read_text(encoding="utf-8")
check("Asia/Seoul 고정", "export TZ=Asia/Seoul" in nb)
check("착수 08:00 기본값", "START_BY=${START_BY:-800}" in nb)
check("마무리 09:40 기본값", "FINISH_BY=${FINISH_BY:-940}" in nb)
check("정지 신호에도 요약 기록", "trap 'cleanup 정지신호" in nb)
check("정지 시 자식 프로세스 정리", "pkill -P $$" in nb)
check("완료 판정은 스트림 확인", "stream=codec_type" in nb)
check("음량 정규화 인코딩", "loudnorm=I=-14" in nb)
check("자가점검 단계", "review_output.py" in nb)
check("그림 프롬프트를 영어로 변환", "scene_prompt.py" in nb)
check("적응형 크롭 사용", "crop_keyframe.py" in nb)
import scene_prompt as SP  # noqa: E402
check("장면 묘사에 한글이 남으면 버린다", SP.to_scene.__doc__ is not None and
      SP.HANGUL.search("방") is not None)
check("장면 묘사 실패 시 한글 없는 기본 프롬프트", not SP.HANGUL.search(SP.FALLBACK))
svc = Path("/etc/systemd/system/aivideo-night.service")
if svc.exists():
    t = svc.read_text()
    check("서비스가 v2 를 가리킴", "night_batch_v2.sh" in t)
    check("SIGTERM 을 정상 종료로", "SuccessExitStatus=SIGTERM" in t)

section("공개 게이트 (SPEC §4)")
sys.path.insert(0, str(BASE))
from backend.main import _classify  # noqa: E402

check("야간 산출물은 final 이 아니다", _classify("final_night.mp4")[0] == "night",
      _classify("final_night.mp4")[0])
check("승인본은 final", _classify("final_v3_2.mp4")[0] == "final")
check("장면 클립은 scene", _classify("s3_00001_.mp4")[0] == "scene")

# ---------- 5. 큐 형식 ----------
section("큐 형식 (SPEC §6)")
rows = [r.split("\t") for r in
        (BASE / "works" / "queue.txt").read_text(encoding="utf-8").splitlines() if r.strip()]
check("큐가 비어 있지 않다", bool(rows), "0줄")
check("모든 줄이 3열 이상", all(len(c) >= 3 for c in rows))
check("작품ID ASCII", all(c[0].isascii() for c in rows))
missing = [c[1] for c in rows if len(c) > 1 and not (BASE / c[1]).exists()]
check("사실파일 존재", not missing, str(missing))

# ---------- 6. 구문 ----------
section("구문 검사")
for f in sorted((BASE / "scripts").glob("*.py")):
    err = ""
    try:
        compile(f.read_text(encoding="utf-8"), str(f), "exec")
        ok = True
    except SyntaxError as e:
        ok, err = False, str(e)
    check(f.name, ok, err)
r = subprocess.run(["bash", "-n", str(BASE / "scripts" / "night_batch_v2.sh")],
                   capture_output=True, text=True)
check("night_batch_v2.sh", r.returncode == 0, r.stderr.strip()[:120])

print("\n" + "=" * 60)
if FAIL:
    print(f"불합격 {len(FAIL)}건")
    for x in FAIL:
        print(" -", x)
    sys.exit(1)
print("명세 대조 전부 통과")
