#!/usr/bin/env python3
"""설계서 빌드 (v1.2~).

설계서/v1.N 에서:  ../../AMR-fms/.venv/bin/python build.py [--html] [--fast] [--no-notes]
  1. tools/make_diagrams.py → assets/diagrams/*.svg,  tools/gen_api.py → gen/api_*.html
  2. src/NN_*.html 을 합치고(<!--#include 경로--> 치환) 제목·캡션에 id 를 붙인다
  3. 1차 PDF: 제목·캡션마다 보이지 않는 표식 문자열을 넣어 인쇄 → pdftotext 로 표식이 찍힌 쪽을 찾는다
  4. 2차 PDF: 표식을 빼고 목차·그림 목차·표 목차에 쪽번호를 채워 최종 인쇄
  5. notes/*.md (발표 주석) 를 쪽에 붙여 발표 주석 PDF·MD 를 만든다
옵션: --html 은 HTML 만, --fast 는 1회 인쇄(쪽번호 없음), --no-notes 는 주석 생략
"""
import html as htmllib
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

VERSION = "1.5"
DATE = "2026-11-26"
AUTHORS = "김대환,김민준,최민석,박시현,안태현"

HERE = Path(__file__).resolve().parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
OUT_HTML = HERE / f"설계서_v{VERSION}.html"
OUT_PDF = HERE / f"(3팀)설계서_v{VERSION}({AUTHORS}).pdf"
NOTES_HTML = HERE / "build" / "notes.html"
NOTES_PDF = HERE / f"(3팀)설계서_v{VERSION}_발표주석.pdf"
NOTES_MD = HERE / f"발표주석_v{VERSION}.md"
BUILD = HERE / "build"

sys.path.insert(0, str(HERE / "tools"))

ID_PREFIX = re.compile(r"^((?:SC|SD|UC|API|FR|WS|FN|TC|AL|NFR|AR|DR|S)-[A-Za-z0-9]+(?:-[0-9]+)?)\b")
NUM_PREFIX = re.compile(r"^((?:\d+|[A-Z])(?:\.\d+)*)\.?\s")


# ------------------------------------------------------------------ 합치기
def include(text: str) -> str:
    def rep(m):
        return include((HERE / m.group(1).strip()).read_text(encoding="utf-8"))
    return re.sub(r"<!--#include (.+?)-->", rep, text)


def plain(fragment: str) -> str:
    t = re.sub(r"<[^>]+>", "", fragment)
    return re.sub(r"\s+", " ", htmllib.unescape(t)).strip()


def key_of(kind: str, text: str) -> str:
    if kind == "fig":
        m = re.match(r"(그림\s*[A-Z0-9]+\.\d+)", text)
        return re.sub(r"\s+", " ", m.group(1)) if m else text
    if kind == "tab":
        m = re.match(r"<\s*(표\s*[A-Z0-9]+\.\d+)\s*>", text)
        return re.sub(r"\s+", " ", m.group(1)) if m else text
    m = ID_PREFIX.match(text)
    if m:
        return m.group(1)
    m = NUM_PREFIX.match(text)
    if m:
        return m.group(1)
    return text


class Doc:
    """합친 본문 + 제목·캡션 목록(entries)."""

    def __init__(self, body: str):
        self.entries = []          # dict(idx, kind, level, key, text, id, toc)
        self.body = self._annotate(body)

    def _annotate(self, body: str) -> str:
        pat = re.compile(
            r"<(h[1-4])((?:\s[^>]*)?)>(.*?)</\1>"            # 제목
            r"|<p class=\"(cap|tcap)\"((?:\s[^>]*)?)>(.*?)</p>"  # 캡션
            r"|<!--@(.+?)-->",                                # 주석 앵커
            re.S)
        out, pos = [], 0
        for m in pat.finditer(body):
            out.append(body[pos:m.start()])
            pos = m.end()
            idx = len(self.entries)
            if m.group(1):
                tag, attrs, inner = m.group(1), m.group(2) or "", m.group(3)
                level = int(tag[1])
                text = plain(inner)
                if level == 1 and "chap" not in attrs:      # 표지 제목
                    out.append(m.group(0))
                    continue
                kind, toc = "h", "notoc" not in attrs
            elif m.group(4):
                tag, attrs, inner = "p", f' class="{m.group(4)}"' + (m.group(5) or ""), m.group(6)
                level, text = 0, plain(inner)
                kind, toc = ("fig" if m.group(4) == "cap" else "tab"), True
            else:
                key = m.group(7).strip()
                self.entries.append(dict(idx=idx, kind="anchor", level=9, key=key, text=key, id=f"n{idx}", toc=False))
                out.append(f"@@M{idx}@@")
                continue
            eid = f"e{idx}"
            self.entries.append(dict(idx=idx, kind=kind, level=level, key=key_of(kind, text), text=text, id=eid, toc=toc))
            out.append(f"<{tag}{attrs} id=\"{eid}\">{inner}@@M{idx}@@</{tag}>")
        out.append(body[pos:])
        return "".join(out)

    def render(self, pages: dict | None, markers: bool) -> str:
        def mark(m):
            i = int(m.group(1))
            return f'<span class="pm">QQM{i}QQ</span>' if markers else ""
        body = re.sub(r"@@M(\d+)@@", mark, self.body)
        body = body.replace("<!--#toc-->", self._toc(pages))
        body = body.replace("<!--#lof-->", self._list("fig", pages))
        body = body.replace("<!--#lot-->", self._list("tab", pages))
        return body

    def _pg(self, e, pages):
        return str(pages.get(e["idx"], "")) if pages else "000"

    def _toc(self, pages):
        rows = []
        for e in self.entries:
            if e["kind"] != "h" or not e["toc"] or e["level"] > 2:
                continue
            cls = "l1" if e["level"] == 1 else "l2"
            rows.append(f'<div class="e {cls}"><a href="#{e["id"]}">{htmllib.escape(e["text"])}</a>'
                        f'<span class="d"></span><span class="p">{self._pg(e, pages)}</span></div>')
        return '<div class="toc2">' + "".join(rows) + "</div>"

    def _list(self, kind, pages):
        rows = []
        for e in self.entries:
            if e["kind"] != kind:
                continue
            t = e["text"]
            if kind == "tab":
                t = re.sub(r"^<\s*(표\s*[A-Z0-9.]+)\s*>\s*", r"\1 ", t)
            rows.append(f'<div class="e"><a href="#{e["id"]}">{htmllib.escape(t)}</a>'
                        f'<span class="d"></span><span class="p">{self._pg(e, pages)}</span></div>')
        return '<div class="toc2 lst">' + "".join(rows) + "</div>"


# ------------------------------------------------------------------ 인쇄
def wrap(body: str) -> str:
    css = (HERE / "src" / "style.css").read_text(encoding="utf-8")
    css += "\n.pm{font-size:2px;line-height:0;color:#fff;white-space:nowrap;margin-right:-14px}\n"
    doc = ("<!doctype html><html lang='ko'><head><meta charset='utf-8'>"
           f"<title>(3팀) 설계서 v{VERSION} — 다중 AMR FMS</title>"
           f"<style>{css}</style></head><body>{body}</body></html>")
    return doc.replace("__VER__", VERSION).replace("__DATE__", DATE)


def print_pdf(html_path: Path, pdf_path: Path):
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    "--virtual-time-budget=15000", f"--print-to-pdf={pdf_path}", html_path.as_uri()],
                   check=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)


def page_count(pdf: Path) -> int:
    out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    return int(re.search(r"Pages:\s+(\d+)", out).group(1))


def page_texts(pdf: Path) -> list[str]:
    out = subprocess.run(["pdftotext", "-enc", "UTF-8", str(pdf), "-"], capture_output=True, text=True).stdout
    return out.split("\f")


def locate(pdf: Path) -> dict:
    pages = {}
    for no, text in enumerate(page_texts(pdf), start=1):
        flat = re.sub(r"\s+", "", text)
        for m in re.finditer(r"QQM(\d+)QQ", flat):
            pages.setdefault(int(m.group(1)), no)
    return pages


# ------------------------------------------------------------------ 발표 주석
def md_inline(s: str) -> str:
    s = htmllib.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    return s


def md_block(text: str) -> str:
    out, para, ul = [], [], []

    def flush():
        if para:
            out.append("<p>" + md_inline(" ".join(para)) + "</p>")
            para.clear()
        if ul:
            out.append("<ul>" + "".join(f"<li>{md_inline(x)}</li>" for x in ul) + "</ul>")
            ul.clear()

    table = []

    def flush_table():
        if table:
            rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in table
                    if not re.match(r"^\s*\|?\s*:?-{2,}", r)]
            head, body = rows[0], rows[1:]
            out.append("<table><thead><tr>" + "".join(f"<th>{md_inline(c)}</th>" for c in head) + "</tr></thead>"
                       + "".join("<tr>" + "".join(f"<td>{md_inline(c)}</td>" for c in r) + "</tr>" for r in body) + "</table>")
            table.clear()

    for line in text.splitlines():
        s = line.rstrip()
        if s.lstrip().startswith("|"):
            flush()
            table.append(s)
            continue
        flush_table()
        if not s.strip():
            flush()
            continue
        if s.startswith("### "):
            flush()
            out.append(f"<h3>{md_inline(s[4:])}</h3>")
            continue
        if s.startswith("> "):
            flush()
            out.append(f'<div class="say">{md_inline(s[2:])}</div>')
        elif s.lstrip().startswith("- "):
            if para:
                out.append("<p>" + md_inline(" ".join(para)) + "</p>")
                para.clear()
            ul.append(s.lstrip()[2:])
        elif s.startswith("Q: ") or s.startswith("A: "):
            flush()
            cls = "q" if s[0] == "Q" else "a"
            out.append(f'<div class="{cls}"><b>{s[0]}</b> {md_inline(s[3:])}</div>')
        elif s.startswith("! "):
            flush()
            out.append(f'<div class="warn">{md_inline(s[2:])}</div>')
        else:
            if ul:
                flush()
            para.append(s.strip())
    flush_table()
    flush()
    return "".join(out)


def read_notes() -> list[dict]:
    notes = []
    for f in sorted((HERE / "notes").glob("*.md")):
        if f.name.startswith("_"):
            continue                       # _intro.md 등 앵커 없는 머리 문서
        cur = None
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.startswith("%"):
                continue
            m = re.match(r"^## (.+?)\s*(?:\|\s*(.*))?$", line)
            if m:
                cur = dict(key=m.group(1).strip(), title=(m.group(2) or "").strip(), body=[], file=f.name)
                notes.append(cur)
            elif cur is not None:
                cur["body"].append(line)
    for n in notes:
        n["body"] = "\n".join(n["body"]).strip()
    return notes


def build_notes(doc: Doc, pages: dict, pdf: Path, total: int):
    notes = read_notes()
    by_key = {}
    for e in doc.entries:
        if e["idx"] in pages:
            by_key.setdefault(e["key"], e)
            by_key.setdefault(e["text"], e)
    per_page = {p: [] for p in range(1, total + 1)}
    missing = []
    for n in notes:
        key = n["key"]
        shift = len(key) - len(key.lstrip("+"))      # "+표 8.13" = 표 8.13 이 있는 쪽의 다음 쪽
        e = by_key.get(key.lstrip("+"))
        if not e or pages[e["idx"]] + shift > total:
            missing.append(key)
            continue
        per_page[pages[e["idx"]] + shift].append((e["idx"] + shift * 0.001, n))
    # 쪽마다 그 쪽에 처음 나오는 제목·캡션
    on_page = {p: [] for p in range(1, total + 1)}
    for e in doc.entries:
        if e["idx"] in pages and e["kind"] != "anchor":
            on_page[pages[e["idx"]]].append(e)

    thumbs = BUILD / "thumbs"
    if thumbs.exists():
        shutil.rmtree(thumbs)
    thumbs.mkdir(parents=True)
    subprocess.run(["pdftoppm", "-r", "100", "-jpeg", "-jpegopt", "quality=70", str(pdf), str(thumbs / "p")], check=True)
    imgs = sorted(thumbs.glob("p-*.jpg"))

    sheets, md, uncovered = [], [f"# (3팀) 설계서 v{VERSION} 발표 주석\n",
                                 f"설계서 PDF 한 쪽마다 발표 요점(▶), 부연 설명, 예상 질문(Q/A)을 적었다. 작성일 {DATE}.\n"], []
    last_heading, last_any = "", ""
    for p in range(1, total + 1):
        items = sorted(per_page[p], key=lambda x: x[0])
        heads = [e for e in on_page[p] if e["kind"] == "h"]
        caps = [e for e in on_page[p] if e["kind"] in ("fig", "tab")]
        ctx = last_heading
        if heads:
            last_heading = heads[-1]["text"]
        prev_any = last_any
        if on_page[p]:
            last_any = on_page[p][-1]["text"]
        body = []
        if items:
            prev_title = None
            for _, n in items:
                title = n["title"] or n["key"]
                head = "" if title == prev_title else f"<h3>{md_inline(title)}</h3>"
                body.append(f'{head}{md_block(n["body"])}')
                prev_title = title
        else:
            uncovered.append(p)
            label = heads[0]["text"] if heads else (f"「{ctx}」 이어짐" if ctx else "표지·문서 정보")
            cont = f"앞 쪽 「{prev_any}」의 나머지가 이어지는 쪽이다." if prev_any else "앞 쪽 내용이 이어지는 쪽이다."
            body.append(f'<h3>{md_inline(label)}</h3><p class="auto">{md_inline(cont)} 따로 설명할 새 항목은 없고, 앞 쪽 주석의 요점을 가리키며 넘긴다.</p>')
        idx_line = " · ".join(e["key"] if e["kind"] != "h" else e["text"] for e in heads + caps)
        img = imgs[p - 1].relative_to(BUILD).as_posix() if p - 1 < len(imgs) else ""
        sheets.append(
            f'<section class="sheet"><div class="pic"><img src="{img}"><div class="pno">설계서 {p}쪽</div></div>'
            f'<div class="txt"><div class="ctx">{md_inline(ctx or "")}</div>'
            + (f'<div class="idx">이 쪽: {md_inline(idx_line)}</div>' if idx_line else "")
            + "".join(body) + "</div></section>")
        md.append(f"\n---\n\n## {p}쪽" + (f" — {heads[0]['text']}" if heads else (f" — ({ctx})" if ctx else "")) + "\n")
        if items:
            for _, n in items:
                md.append(f"\n### {n['title'] or n['key']}\n\n{n['body']}\n")
        else:
            md.append("\n(앞 쪽 내용 이어짐)\n")

    # 머리 문서 (_intro.md: "## 제목" 단위로 쪽을 나눈다)
    intro_html, intro_md = [], []
    intro = HERE / "notes" / "_intro.md"
    if intro.exists():
        blocks = re.split(r"^## ", intro.read_text(encoding="utf-8"), flags=re.M)
        for b in blocks[1:]:
            title, _, body = b.partition("\n")
            body = "\n".join(l for l in body.splitlines() if not l.startswith("%"))
            intro_html.append(f'<section class="intro"><h2>{md_inline(title.strip())}</h2>{md_block(body)}</section>')
            intro_md.append(f"\n## {title.strip()}\n\n{body.strip()}\n")
    # 예상 질문 색인: 모든 주석의 Q/A 를 쪽 순서로
    faq = []
    for p in range(1, total + 1):
        for _, n in sorted(per_page[p], key=lambda x: x[0]):
            lines = n["body"].splitlines()
            for k, line in enumerate(lines):
                if line.startswith("Q: "):
                    ans = next((l[3:] for l in lines[k + 1:k + 3] if l.startswith("A: ")), "")
                    faq.append((p, line[3:], ans))
    faq_rows = "".join(f"<tr><td class='pg'>{p}</td><td><b>{md_inline(q)}</b><br>{md_inline(a)}</td></tr>" for p, q, a in faq)
    faq_html = (f"<section class='intro faq'><h2>예상 질문 색인 ({len(faq)}개)</h2>"
                "<p>주석에 흩어진 예상 질문을 설계서 쪽 순서로 모았다. 왼쪽 숫자는 설계서 쪽이다. 질의응답 준비 때 이 목록만 읽어도 된다.</p>"
                f"<table class='faqt'><thead><tr><th>쪽</th><th>질문 · 답</th></tr></thead>{faq_rows}</table></section>")
    md[2:2] = intro_md
    md.append(f"\n---\n\n## 예상 질문 색인 ({len(faq)}개)\n")
    md.extend(f"\n- ({p}쪽) **{q}** — {a}" for p, q, a in faq)

    css = (HERE / "tools" / "notes.css").read_text(encoding="utf-8")
    page = ("<!doctype html><html lang='ko'><head><meta charset='utf-8'>"
            f"<title>(3팀) 설계서 v{VERSION} 발표 주석</title><style>{css}</style></head><body>"
            f"<section class='ncover'><h1>설계서 v{VERSION} 발표 주석</h1>"
            "<p>다중 AMR 작업 할당·트래픽 제어 FMS · 팀 WAYPOINT (3팀)</p>"
            f"<p>설계서 PDF 의 쪽마다 왼쪽에 그 쪽을, 오른쪽에 발표 요점(▶ 상자), 부연 설명, 예상 질문(Q/A)을 둔다. 작성일 {DATE}.</p>"
            "<p class='small'>▶ = 발표 때 그대로 말할 한두 문장 · 본문 = 질문이 오면 덧붙일 배경 · Q/A = 예상 질문과 답 · ! = 말할 때 조심할 점</p></section>"
            + "".join(intro_html) + "".join(sheets) + faq_html + "</body></html>")
    page = page.replace("__VER__", VERSION)
    NOTES_HTML.write_text(page, encoding="utf-8")
    print_pdf(NOTES_HTML, NOTES_PDF)
    NOTES_MD.write_text("\n".join(md), encoding="utf-8")
    print(f"주석: {NOTES_PDF.name} {page_count(NOTES_PDF)}쪽, 주석 {len(notes)}개, 주석 없는 쪽 {len(uncovered)}개")
    if missing:
        print("  앵커 못 찾음:", ", ".join(missing))
    if uncovered:
        print("  주석 없는 쪽:", ",".join(map(str, uncovered)))


# ------------------------------------------------------------------ main
def main():
    args = set(sys.argv[1:])
    import make_diagrams
    import gen_api
    make_diagrams.main()
    gen_api.main()
    import gen_matrix
    gen_matrix.main()
    parts = [include(p.read_text(encoding="utf-8")) for p in sorted((HERE / "src").glob("[0-9][0-9]_*.html"))]
    merged = re.sub(r'(<figure\b.*?</figure>)\s*(<p class="cap">.*?</p>)',
                    r'<div class="figbox">\1\2</div>', "\n".join(parts), flags=re.S)   # 그림+캡션을 한 덩어리로
    doc = Doc(merged)
    BUILD.mkdir(exist_ok=True)
    if "--html" in args:
        OUT_HTML.write_text(wrap(doc.render(None, False)), encoding="utf-8")
        print("HTML:", OUT_HTML.name)
        return
    pass1_html = BUILD / "pass1.html"
    pass1_pdf = BUILD / "pass1.pdf"
    # pass1.html 은 assets/ 상대 경로를 쓰므로 HERE 에 둔다
    pass1_html = HERE / "_pass1.html"
    pass1_html.write_text(wrap(doc.render(None, True)), encoding="utf-8")
    print_pdf(pass1_html, pass1_pdf)
    pass1_html.unlink()
    pages = locate(pass1_pdf)
    n1 = page_count(pass1_pdf)
    with open(BUILD / "entries.tsv", "w", encoding="utf-8") as f:
        for e in doc.entries:
            f.write(f'{pages.get(e["idx"], "?")}\t{e["kind"]}{e["level"] if e["kind"] == "h" else ""}\t{e["key"]}\t{e["text"][:80]}\n')
    lost = [e["key"] for e in doc.entries if e["idx"] not in pages]
    if lost:
        print("표식 못 찾음:", lost[:20])
    if "--fast" in args:
        shutil.copy(pass1_pdf, OUT_PDF)
    else:
        OUT_HTML.write_text(wrap(doc.render(pages, False)), encoding="utf-8")
        print_pdf(OUT_HTML, OUT_PDF)
    n2 = page_count(OUT_PDF)
    # 축소 인쇄 감지: 너무 넓은 요소가 있으면 Chrome 이 문서 전체를 줄여 찍는다. 본문 오른쪽 끝이 안쪽으로 들어오면 경고
    bbox = subprocess.run(["pdftotext", "-bbox", "-f", "12", "-l", "14", str(OUT_PDF), "-"], capture_output=True, text=True).stdout
    xmax = max((float(x) for x in re.findall(r'xMax="([\d.]+)"', bbox)), default=0)
    if xmax and xmax < 520:
        print(f"경고: 본문 오른쪽 끝 {xmax:.0f}pt — 쪽 폭을 넘는 표·그림 때문에 전체가 축소 인쇄됐을 수 있다")
    print(f"PDF: {OUT_PDF.name} {n2}쪽" + ("" if n1 == n2 else f"  (1차 {n1}쪽과 다름 — 쪽번호 확인 필요)"))
    if "--no-notes" not in args:
        build_notes(doc, pages, OUT_PDF, n2)


if __name__ == "__main__":
    main()
