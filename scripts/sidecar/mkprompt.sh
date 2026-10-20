#!/bin/bash
# mkprompt.sh <work> <index> -> stdout: 배치와 같은 방식으로 만든 이미지 프롬프트
set -e
cd /home/mooner92/aivideo
W="$1"; i="$2"
line=$(grep -P "^$W\t" works/queue.txt || true); [ -z "$line" ] && line=$(grep -P "^[^\t]*\t$W\t" works/done.txt | tail -1 | cut -f2- || true)
facts=$(echo "$line" | cut -f2); style=$(echo "$line" | cut -f4)
TRE=output/$W/treatment.json; NAR=output/$W/narration_night.json
ctx=$(python3 -c "
import re
t=open('$facts',encoding='utf-8').read()
body=[l for l in t.splitlines() if l and not l.startswith('[')]
print(re.sub(r'\s+',' ',' '.join(body))[:200])")
desc=$(venv/bin/python scripts/scene_prompt.py --narration "$NAR" --index "$i" --context "$ctx" --treatment "$TRE" 2>/dev/null | tail -1)
printf '%s%s' "$style" "$desc"
