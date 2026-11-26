#!/usr/bin/env python3
"""설계서 일관성 검사.

설계서/v1.N 에서:  python3 tools/check.py
  - 캡션 없는 표 (화면 설명·와이어프레임·유스케이스 명세·생성 API 상세 제외)
  - 본문에서 언급했지만 정의되지 않은 표·그림 번호
  - 표·그림 번호 중복, 장 안에서 순서가 어긋난 번호
  - 정의되지 않은 ID 참조 (FR/SC/SD/UC/API/FN/TC/NFR/AR/DR/S)
"""
import html
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


def load() -> str:
    def inc(t):
        return re.sub(r"<!--#include (.+?)-->", lambda m: inc((HERE / m.group(1).strip()).read_text(encoding="utf-8")), t)
    return "\n".join(inc(p.read_text(encoding="utf-8")) for p in sorted((HERE / "src").glob("[0-9][0-9]_*.html")))


def text_of(s):
    return html.unescape(re.sub(r"<[^>]+>", " ", s))


def main():
    src = load()
    problems = 0

    # 1. 캡션 없는 표
    skip_cls = ("screen-desc", "kv", "plain")
    for m in re.finditer(r"<table([^>]*)>", src):
        attrs = m.group(1)
        if any(c in attrs for c in skip_cls):
            continue
        before = src[max(0, m.start() - 400):m.start()]
        if "class='api'" in before[-200:] or "<div class='api'>" in before[-120:]:
            continue
        if '<div class="wf"' in src[max(0, m.start() - 3000):m.start()] and "</div>" not in src[src.rfind('<div class="wf"', 0, m.start()):m.start()].split("<table")[0][-5:]:
            # 와이어프레임 안 표는 건너뛴다 (가까운 wf 블록 안인지 대략 판단)
            wf_start = src.rfind('<div class="wf"', 0, m.start())
            if wf_start != -1 and src.count("<div", wf_start, m.start()) > src.count("</div>", wf_start, m.start()):
                continue
        if not re.search(r'class="tcap"[^>]*>[^<]*(?:<[^>]+>[^<]*)*</p>\s*$', before):
            line = src.count("\n", 0, m.start()) + 1
            ctx = text_of(before[-160:]).strip().replace("\n", " ")[-70:]
            print(f"[캡션 없음] 줄 {line}: …{ctx}")
            problems += 1

    # 2. 표·그림 정의와 참조
    tdefs = re.findall(r'class="tcap"[^>]*>\s*&lt;표\s*([A-Z0-9]+\.\d+)&gt;', src)
    fdefs = re.findall(r'class="cap"[^>]*>\s*그림\s*([A-Z0-9]+\.\d+)', src)
    for kind, defs in (("표", tdefs), ("그림", fdefs)):
        for k, n in Counter(defs).items():
            if n > 1:
                print(f"[중복] {kind} {k} × {n}")
                problems += 1
        # 장 안 순서
        last = {}
        for d in defs:
            ch, no = d.split(".")
            no = int(no)
            if ch in last and no != last[ch] + 1:
                print(f"[순서] {kind} {ch}.{last[ch]} 다음이 {d}")
                problems += 1
            last[ch] = no
    body = text_of(src)
    for kind, defs in (("표", set(tdefs)), ("그림", set(fdefs))):
        for m in re.finditer(kind + r"\s*([A-Z0-9]+\.\d+|\d+\.x)", body):
            if m.group(1) not in defs:
                ctx = body[max(0, m.start() - 40):m.end() + 10].replace("\n", " ")
                print(f"[없는 {kind}] {kind} {m.group(1)}: …{ctx}…")
                problems += 1

    # 3. ID 정의와 참조 (정의 = 표의 첫 칸 또는 제목 맨 앞)
    id_pat = r"(?:FR-[USAE]-\d{2}|SC-\d{2}|SD-\d{2}|UC-\d{2}|API-\d{3,4}|FN-\d{2}|TC-[A-Z]+-\d{2,3}|NFR-\d{2}|AR-\d{2}|DR-\d{2}|AI-0\d|WS-\d{2}|AL-\d{2})"
    defined = set()
    for m in re.finditer(r"<tr><td[^>]*>\s*(?:<[^>]+>)*(" + id_pat + r")", src):
        defined.add(m.group(1))
    for m in re.finditer(r"<td>(SC-\d{2})</td>", src):
        defined.add(m.group(1))
    for m in re.finditer(r"<h[34][^>]*>\s*(" + id_pat + r")", src):
        defined.add(m.group(1))
    for m in re.finditer(r"<td>(FN-\d{2}) ~ (\d{2})</td>", src):
        for i in range(int(m.group(1)[3:]), int(m.group(2)) + 1):
            defined.add(f"FN-{i:02d}")
    for m in re.finditer(r"API-(\d{3,4}) ~ (\d{3,4})", src):
        for i in range(int(m.group(1)), int(m.group(2)) + 1):
            defined.add(f"API-{i}")
    used = Counter(re.findall(id_pat, body))
    for k in sorted(used):
        if k not in defined:
            print(f"[정의 없는 ID] {k} ({used[k]}회)")
            problems += 1
    # 범위 표기 (SD-01·03, FN-03~06) 의 개별 확인은 생략

    print(f"\n표 {len(tdefs)}개 · 그림 {len(fdefs)}개 · 정의된 ID {len(defined)}개 · 문제 {problems}건")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
