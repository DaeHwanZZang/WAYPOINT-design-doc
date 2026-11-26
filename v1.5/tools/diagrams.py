"""설계서 v1.1 다이어그램 SVG 생성기 (UML 시퀀스·유스케이스·ERD·상태/흐름).

색 규칙 (제안서 v1.2 와 같음): 구현 완료 = 파랑 #1C6E8C, 이번 개발(계획) = 주황 #E8590C, 글자 #16202B.
"""
from html import escape

FONT = "Pretendard, 'Apple SD Gothic Neo', sans-serif"
INK, SUB, LINE, CARD = "#16202B", "#4B5563", "#9AA3AD", "#F3F5F7"
BLUE, ORANGE, GREEN, RED, PURPLE = "#1C6E8C", "#E8590C", "#2E8B57", "#C0392B", "#6D4AE0"
TINT = {BLUE: "#E3F0F5", ORANGE: "#FDEEE3", GREEN: "#E6F4EC", RED: "#FBE9E7", PURPLE: "#EEE9FD", INK: CARD}


def _w(text, size):
    """대략적인 글자 폭 (한글 1.0em, 그 밖 0.56em)."""
    return sum(size * (1.0 if ord(c) > 0x2E80 else 0.56) for c in str(text))


def _t(x, y, s, size=13, anchor="middle", color=INK, weight=400, italic=False):
    st = ' font-style="italic"' if italic else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" fill="{color}" '
            f'font-weight="{weight}"{st}>{escape(str(s))}</text>')


def _lines(x, y, text, size=13, anchor="middle", color=INK, weight=400, gap=1.3):
    parts = str(text).split("\n")
    y0 = y - (len(parts) - 1) * size * gap / 2
    return "".join(_t(x, y0 + i * size * gap, p, size, anchor, color, weight) for i, p in enumerate(parts))


def _defs():
    out = []
    for name, color in (("a", INK), ("b", BLUE), ("o", ORANGE), ("g", SUB), ("r", RED), ("p", PURPLE), ("gr", GREEN)):
        out.append(f'<marker id="{name}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="9" markerHeight="9" '
                   f'markerUnits="userSpaceOnUse" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 Z" fill="{color}"/></marker>')
        out.append(f'<marker id="{name}o" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="10" markerHeight="10" '
                   f'markerUnits="userSpaceOnUse" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10" fill="none" stroke="{color}" stroke-width="1.4"/></marker>')
    return "<defs>" + "".join(out) + "</defs>"


def _svg(w, h, body, title=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" width="{w:.0f}" height="{h:.0f}" '
            f'font-family="{FONT}"><title>{escape(title)}</title>{_defs()}<rect width="100%" height="100%" fill="#fff"/>{body}</svg>')


MK = {INK: "a", BLUE: "b", ORANGE: "o", SUB: "g", RED: "r", PURPLE: "p", GREEN: "gr"}


# ---------------------------------------------------------------- 시퀀스 다이어그램
def sequence(title, participants, steps, width=None):
    """participants: [(key, 이름, 종류)] 종류: actor|boundary|control|entity|ext|robot|ai
    steps: ("m", a, b, 텍스트[, "sync"|"async"|"ret"][, 색]) / ("s", a, 텍스트[, 색]) 자기호출
           ("n", a, 텍스트[, b]) 노트 / ("f", "alt|opt|loop|par|break", 조건, [steps], [(조건, [steps])...])
           ("d", a, 텍스트) 구분선/설명 / ("gap", px)
    """
    n = len(participants)
    col = max(150, max(_w(l, 15) for p in participants for l in p[1].split("\n")) + 30)
    w = width or min(1120, max(760, col * n + 40))
    col = (w - 40) / n
    xs = {p[0]: 20 + col * (i + 0.5) for i, p in enumerate(participants)}
    body = []
    head_h = 76
    y = head_h + 26
    frames = []

    def label_width(a, b):
        return abs(xs[a] - xs[b]) - 16

    def run(items, depth):
        nonlocal y
        for st in items:
            k = st[0]
            if k == "m" and st[1] == st[2]:
                st = ("s", st[1], st[3]) + ((st[5],) if len(st) > 5 else ())
                k = "s"
            if k == "m":
                a, b, text = st[1], st[2], st[3]
                kind = st[4] if len(st) > 4 else "sync"
                color = st[5] if len(st) > 5 else (SUB if kind == "ret" else INK)
                xa, xb = xs[a], xs[b]
                dash = ' stroke-dasharray="6 4"' if kind == "ret" else ""
                mk = MK.get(color, "a") + ("o" if kind in ("async", "ret") else "")
                size = 15
                maxw = label_width(a, b)
                lines = _wrap(text, size, maxw)
                y += 18 * (len(lines) - 1)
                for i, ln in enumerate(lines):
                    body.append(_t((xa + xb) / 2, y - 7 - 18 * (len(lines) - 1 - i), ln, size, color=color))
                body.append(f'<line x1="{xa:.1f}" y1="{y:.1f}" x2="{xb - (6 if xb > xa else -6):.1f}" y2="{y:.1f}" '
                            f'stroke="{color}" stroke-width="1.4"{dash} marker-end="url(#{mk})"/>')
                y += 40
            elif k == "s":
                a, text = st[1], st[2]
                color = st[3] if len(st) > 3 else INK
                xa = xs[a]
                right = xa + col * 0.95 > w
                lines = _wrap(text, 15, col * (1.6 if right else 0.95))
                for i, ln in enumerate(lines):
                    body.append(_t(xa + (-12 if right else 12), y - 4 + 18 * i, ln, 15, "end" if right else "start", color))
                yy = y + 18 * (len(lines) - 1)
                sg = -1 if right else 1
                body.append(f'<path d="M{xa:.1f} {yy + 2:.1f} h{28 * sg} v16 h{-22 * sg}" fill="none" stroke="{color}" stroke-width="1.3" '
                            f'marker-end="url(#{MK.get(color, "a")})"/>')
                y = yy + 44
            elif k == "n":
                a, text = st[1], st[2]
                b = st[3] if len(st) > 3 else a
                x1, x2 = min(xs[a], xs[b]) - col * 0.42, max(xs[a], xs[b]) + col * 0.42
                lines = _wrap(text, 14, x2 - x1 - 16)
                h = 12 + 18 * len(lines)
                body.append(f'<path d="M{x1:.1f} {y - 12:.1f} h{x2 - x1 - 10:.1f} l10 10 v{h - 10:.1f} h{-(x2 - x1):.1f} Z" '
                            f'fill="#FFF8E1" stroke="#C9A227" stroke-width="1"/>')
                for i, ln in enumerate(lines):
                    body.append(_t(x1 + 8, y + 5 + 18 * i, ln, 14, "start", SUB))
                y += h + 16
            elif k == "d":
                body.append(f'<line x1="14" y1="{y - 8:.1f}" x2="{w - 14:.1f}" y2="{y - 8:.1f}" stroke="{LINE}" stroke-dasharray="2 4"/>')
                body.append(_t(w / 2, y + 6, st[1], 15, color=SUB, weight=600))
                y += 30
            elif k == "gap":
                y += st[1]
            elif k == "f":
                kind, cond, inner = st[1], st[2], st[3]
                elses = st[4] if len(st) > 4 else []
                x1 = 10 + depth * 8
                x2 = w - 10 - depth * 8
                top = y - 10
                y += 28
                run(inner, depth + 1)
                seps = []
                for ec, es in elses:
                    seps.append((y - 12, ec))
                    y += 14
                    run(es, depth + 1)
                bottom = y - 14
                frames.append((x1, top, x2, bottom, kind, cond, seps))
                y += 10

    run(steps, 0)
    height = y + 30
    # 생명선
    for key, name, kind in participants:
        x = xs[key]
        body.insert(0, f'<line x1="{x:.1f}" y1="{head_h:.1f}" x2="{x:.1f}" y2="{height - 20:.1f}" stroke="{LINE}" stroke-dasharray="5 4"/>')
        body.append(_head(x, 8, name, kind, col))
    for x1, top, x2, bottom, kind, cond, seps in frames:
        body.insert(0, f'<rect x="{x1}" y="{top:.1f}" width="{x2 - x1:.1f}" height="{bottom - top:.1f}" fill="none" stroke="{SUB}" stroke-width="1"/>')
        lw = _w(kind, 13.5) + 14
        body.append(f'<path d="M{x1} {top:.1f} h{lw:.1f} v15 l-6 6 h{-lw + 6:.1f} Z" fill="{CARD}" stroke="{SUB}" stroke-width="1"/>')
        body.append(_t(x1 + 6, top + 15, kind, 13.5, "start", INK, 700))
        body.append(_t(x1 + lw + 8, top + 15, f"[{cond}]", 13.5, "start", SUB))
        for sy, sc in seps:
            body.append(f'<line x1="{x1}" y1="{sy:.1f}" x2="{x2}" y2="{sy:.1f}" stroke="{SUB}" stroke-dasharray="6 4"/>')
            body.append(_t(x1 + 8, sy + 15, f"[{sc}]", 13.5, "start", SUB))
    return _svg(w, height, "".join(body), title)


def _wrap(text, size, maxw):
    out = []
    for para in str(text).split("\n"):
        cur = ""
        for word in para.split(" "):
            cand = (cur + " " + word).strip()
            if _w(cand, size) > maxw and cur:
                out.append(cur)
                cur = word
            else:
                cur = cand
        out.append(cur)
    return out


def _head(x, y, name, kind, col):
    color = {"actor": INK, "boundary": BLUE, "control": BLUE, "entity": GREEN, "ext": SUB,
             "robot": PURPLE, "ai": ORANGE, "plan": ORANGE}.get(kind, INK)
    tint = TINT.get(color, CARD)
    s = []
    if kind == "actor":
        s.append(f'<circle cx="{x:.1f}" cy="{y + 8}" r="7" fill="none" stroke="{INK}" stroke-width="1.5"/>'
                 f'<path d="M{x:.1f} {y + 15} v14 M{x - 10:.1f} {y + 20} h20 M{x:.1f} {y + 29} l-8 10 M{x:.1f} {y + 29} l8 10" '
                 f'stroke="{INK}" stroke-width="1.5" fill="none"/>')
        s.append(_t(x, y + 58, name, 15, weight=600))
    else:
        tw = max(_w(l, 15) for l in name.split("\n"))
        fs = min(15, 15 * (col - 18) / tw) if tw > col - 18 else 15
        bw = min(col - 6, max(100, tw * fs / 15 + 16))
        dash = ' stroke-dasharray="5 3"' if kind in ("ext", "plan") else ""
        s.append(f'<rect x="{x - bw / 2:.1f}" y="{y + 10}" width="{bw:.1f}" height="54" rx="6" fill="{tint}" stroke="{color}" stroke-width="1.5"{dash}/>')
        s.append(_lines(x, y + 38, name, fs, weight=600))
    return "".join(s)


# ---------------------------------------------------------------- 유스케이스 다이어그램
def usecase(title, left, right, groups, links, width=1000, system="FMS"):
    """left/right: [(key, 이름)] 액터. groups: [(그룹명, [(key, 이름, 상태)])] 상태 'done'|'plan'|'ext'.
    links: [(actor_key, uc_key)] 또는 (uc, uc, '<<include>>'|'<<extend>>')"""
    pos = {}
    row_h = 46
    inner_x1, inner_x2 = 170, width - 170
    y = 70
    gcols = 2
    colw = (inner_x2 - inner_x1 - 30) / gcols
    body = []
    # 그룹을 2열로 배치
    col_y = [y, y]
    for gname, ucs in groups:
        c = 0 if col_y[0] <= col_y[1] else 1
        gx = inner_x1 + 10 + c * (colw + 10)
        gy = col_y[c]
        gh = 30 + row_h * len(ucs)
        body.append(f'<rect x="{gx:.1f}" y="{gy:.1f}" width="{colw:.1f}" height="{gh:.1f}" rx="8" fill="#FAFBFC" stroke="#DADFE4"/>')
        body.append(_t(gx + 10, gy + 18, gname, 12, "start", SUB, 700))
        for i, (key, name, st) in enumerate(ucs):
            cx, cy = gx + colw / 2, gy + 30 + row_h * i + row_h / 2 - 4
            color = {"done": BLUE, "plan": ORANGE, "ext": SUB}.get(st, BLUE)
            dash = ' stroke-dasharray="5 3"' if st == "ext" else ""
            rx = min(colw / 2 - 8, _w(name, 12) / 2 + 26)
            body.append(f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="17" fill="{TINT[color]}" stroke="{color}" stroke-width="1.4"{dash}/>')
            body.append(_t(cx, cy + 4, name, 12))
            pos[key] = (cx, cy, rx)
        col_y[c] = gy + gh + 14
    height = max(col_y) + 30
    body.insert(0, f'<rect x="{inner_x1}" y="40" width="{inner_x2 - inner_x1}" height="{height - 50}" rx="4" fill="none" stroke="{INK}" stroke-width="1.5"/>'
                + _t(inner_x1 + 12, 60, system, 13, "start", INK, 700))
    for side, actors in (("l", left), ("r", right)):
        n = len(actors)
        for i, (key, name) in enumerate(actors):
            ax = 80 if side == "l" else width - 80
            ay = 60 + (height - 120) * (i + 0.5) / max(n, 1)
            pos[key] = (ax, ay, 0)
            body.append(f'<circle cx="{ax}" cy="{ay - 26:.1f}" r="9" fill="none" stroke="{INK}" stroke-width="1.6"/>'
                        f'<path d="M{ax} {ay - 17:.1f} v20 M{ax - 13} {ay - 9:.1f} h26 M{ax} {ay + 3:.1f} l-10 13 M{ax} {ay + 3:.1f} l10 13" stroke="{INK}" stroke-width="1.6" fill="none"/>')
            body.append(_lines(ax, ay + 32, name, 12, weight=600))
    shapes = body
    body = []
    for ln in links:
        a, b = ln[0], ln[1]
        (x1, y1, r1), (x2, y2, r2) = pos[a], pos[b]
        if len(ln) > 2:
            lab = ln[2]
            sx = x1 + (r1 if x2 > x1 else -r1) * 0.2
            body.append(f'<line x1="{x1:.1f}" y1="{y1 + 17:.1f}" x2="{x2:.1f}" y2="{y2 - 17:.1f}" stroke="{SUB}" stroke-dasharray="5 4" marker-end="url(#go)"/>')
            body.append(_t((x1 + x2) / 2 + 6, (y1 + y2) / 2, lab, 10.5, "start", SUB, italic=True))
        else:
            ex = x2 - r2 if x1 < x2 else x2 + r2
            sx = x1 + (16 if x1 < x2 else -16)
            body.append(f'<line x1="{sx:.1f}" y1="{y1:.1f}" x2="{ex:.1f}" y2="{y2:.1f}" stroke="#A3ACB5" stroke-width="1"/>')
    # 그룹 상자(첫 요소들)는 선보다 뒤, 타원·액터는 선보다 앞
    groups_svg = [x for x in shapes if x.startswith('<rect x=') and 'fill="#FAFBFC"' in x]
    rest = [x for x in shapes if x not in groups_svg]
    return _svg(width, height, "".join(groups_svg + body + rest), title)


# ---------------------------------------------------------------- 상자-화살표 (상태도·흐름·구성)
def boxes(title, nodes, edges, width=1000, height=500, legend=None):
    """nodes: {key: (x, y, w, h, 텍스트, 색[, 모양])} 모양: box|round|state|start|end|diamond|db|group
    edges: [(a, b, 라벨[, 색][, 'dash'][, 경로점 리스트])]"""
    body = []
    for key, nd in nodes.items():
        x, y, w, h, text, color = nd[:6]
        shape = nd[6] if len(nd) > 6 else "box"
        tint = TINT.get(color, CARD)
        if shape == "group":
            body.insert(0, f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{tint}" fill-opacity=".45" stroke="{color}" stroke-dasharray="6 4"/>'
                        + _t(x + 12, y + 20, text, 12.5, "start", color, 700))
            continue
        if shape == "start":
            body.append(f'<circle cx="{x}" cy="{y}" r="9" fill="{INK}"/>')
            continue
        if shape == "end":
            body.append(f'<circle cx="{x}" cy="{y}" r="11" fill="none" stroke="{INK}" stroke-width="1.5"/><circle cx="{x}" cy="{y}" r="6" fill="{INK}"/>')
            continue
        if shape == "diamond":
            body.append(f'<path d="M{x + w / 2} {y} L{x + w} {y + h / 2} L{x + w / 2} {y + h} L{x} {y + h / 2} Z" fill="{tint}" stroke="{color}" stroke-width="1.4"/>')
        elif shape == "db":
            body.append(f'<path d="M{x} {y + 8} v{h - 16} a{w / 2} 8 0 0 0 {w} 0 v{-(h - 16)}" fill="{tint}" stroke="{color}" stroke-width="1.4"/>'
                        f'<ellipse cx="{x + w / 2}" cy="{y + 8}" rx="{w / 2}" ry="8" fill="{tint}" stroke="{color}" stroke-width="1.4"/>')
        else:
            rx = 18 if shape == "state" else (6 if shape == "box" else 14)
            dash = ' stroke-dasharray="6 4"' if shape == "dash" else ""
            body.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{tint}" stroke="{color}" stroke-width="1.5"{dash}/>')
        body.append(_lines(x + w / 2, y + h / 2 + 4, text, 12.5, weight=600 if "\n" not in text else 500))

    def anchor(key, toward):
        nd = nodes[key]
        x, y = nd[0], nd[1]
        shape = nd[6] if len(nd) > 6 else "box"
        if shape in ("start", "end"):
            return x, y
        w, h = nd[2], nd[3]
        cx, cy = x + w / 2, y + h / 2
        tx, ty = toward
        dx, dy = tx - cx, ty - cy
        if dx == 0 and dy == 0:
            return cx, cy
        sx = (w / 2) / abs(dx) if dx else 1e9
        sy = (h / 2) / abs(dy) if dy else 1e9
        s = min(sx, sy)
        return cx + dx * s, cy + dy * s

    def center(key):
        nd = nodes[key]
        shape = nd[6] if len(nd) > 6 else "box"
        if shape in ("start", "end"):
            return nd[0], nd[1]
        return nd[0] + nd[2] / 2, nd[1] + nd[3] / 2

    for e in edges:
        a, b, lab = e[0], e[1], e[2]
        color = e[3] if len(e) > 3 and e[3] else INK
        dash = ' stroke-dasharray="6 4"' if len(e) > 4 and e[4] == "dash" else ""
        via = e[5] if len(e) > 5 else []
        pts_mid = list(via)
        first_target = pts_mid[0] if pts_mid else center(b)
        last_source = pts_mid[-1] if pts_mid else center(a)
        p0 = anchor(a, first_target)
        p1 = anchor(b, last_source)
        pts = [p0] + pts_mid + [p1]
        d = "M" + " L".join(f"{px:.1f} {py:.1f}" for px, py in pts)
        body.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.4"{dash} marker-end="url(#{MK.get(color, "a")})"/>')
        if lab:
            if pts_mid:
                mx, my = pts_mid[len(pts_mid) // 2]
            else:
                mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
            lw = max(_w(l, 11) for l in lab.split("\n")) + 10
            nl = len(lab.split("\n"))
            body.append(f'<rect x="{mx - lw / 2:.1f}" y="{my - 9 - (nl - 1) * 7:.1f}" width="{lw:.1f}" height="{16 + (nl - 1) * 14}" rx="3" fill="#fff" fill-opacity=".92"/>')
            body.append(_lines(mx, my + 3, lab, 11, color=color if color != INK else SUB))
    if legend:
        lx = 14
        for color, text in legend:
            body.append(f'<rect x="{lx}" y="{height - 22}" width="14" height="10" rx="2" fill="{TINT.get(color, CARD)}" stroke="{color}"/>')
            body.append(_t(lx + 20, height - 13, text, 11, "start", SUB))
            lx += _w(text, 11) + 46
    return _svg(width, height, "".join(body), title)


# ---------------------------------------------------------------- ERD
def erd(title, entities, rels, width=1000, height=700):
    """entities: {name: (x, y, w, [(필드, 타입, 'PK'|'FK'|''), ...], 색, 저장소)}
    rels: [(a, b, 'a측 기수', 'b측 기수', 라벨)]"""
    body = []
    boxes_ = {}
    for name, (x, y, w, fields, color, store) in entities.items():
        h = 36 + 22 * len(fields) + 6
        boxes_[name] = (x, y, w, h)
        body.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="5" fill="#fff" stroke="{color}" stroke-width="1.5"/>')
        body.append(f'<path d="M{x} {y + 5} a5 5 0 0 1 5 -5 h{w - 10} a5 5 0 0 1 5 5 v27 h{-w} Z" fill="{TINT.get(color, CARD)}" stroke="{color}" stroke-width="1.5"/>')
        body.append(_t(x + 10, y + 21, name, 14.5, "start", INK, 700))
        body.append(_t(x + w - 8, y + 21, store, 11.5, "end", SUB))
        for i, (f, ty, key) in enumerate(fields):
            fy = y + 52 + 22 * i
            kc = {"PK": RED, "FK": BLUE}.get(key, SUB)
            if key:
                body.append(_t(x + 8, fy, key, 11, "start", kc, 700))
            body.append(_t(x + 34, fy, f, 13.5, "start", INK, 600 if key == "PK" else 400))
            body.append(_t(x + w - 8, fy, ty, 12, "end", SUB))
    for a, b, ca, cb, lab in rels:
        ax, ay, aw, ah = boxes_[a]
        bx, by, bw, bh = boxes_[b]
        acx, acy, bcx, bcy = ax + aw / 2, ay + ah / 2, bx + bw / 2, by + bh / 2
        if abs(acx - bcx) > (aw + bw) / 2 - 10:
            x1 = ax + aw if bcx > acx else ax
            x2 = bx if bcx > acx else bx + bw
            y1 = min(max(bcy, ay + 30), ay + ah - 10)
            y2 = min(max(acy, by + 30), by + bh - 10)
            mx = (x1 + x2) / 2
            d = f"M{x1:.1f} {y1:.1f} H{mx:.1f} V{y2:.1f} H{x2:.1f}"
            la, lb = (x1 + (12 if x2 > x1 else -12), y1 - 5), (x2 + (-12 if x2 > x1 else 12), y2 - 5)
            lm = (mx + 4, (y1 + y2) / 2)
        else:
            y1 = ay + ah if bcy > acy else ay
            y2 = by if bcy > acy else by + bh
            x1 = x2 = (max(ax, bx) + min(ax + aw, bx + bw)) / 2
            d = f"M{x1:.1f} {y1:.1f} V{y2:.1f}"
            la, lb = (x1 + 6, y1 + (14 if y2 > y1 else -6)), (x2 + 6, y2 + (-6 if y2 > y1 else 14))
            lm = (x1 + 6, (y1 + y2) / 2)
        body.append(f'<path d="{d}" fill="none" stroke="#7B8590" stroke-width="1.3"/>')
        body.append(_t(*la, ca, 13, "middle", INK, 700))
        body.append(_t(*lb, cb, 13, "middle", INK, 700))
        if lab:
            body.append(_t(lm[0], lm[1], lab, 10.5, "start", SUB, italic=True))
    return _svg(width, height, "".join(body), title)


# ---------------------------------------------------------------- 간트
def gantt(title, days, rows, marks=(), width=1000):
    """days: ['11/24', ...] 열 라벨. rows: [(그룹, 이름, 시작idx, 끝idx, 색)] 그룹 행은 이름=None.
    marks: [(idx, 라벨, 색)]"""
    left = 250
    cw = (width - left - 20) / len(days)
    rh = 24
    y0 = 56
    body = []
    for i, d in enumerate(days):
        x = left + cw * i
        body.append(f'<rect x="{x:.1f}" y="{y0 - 26}" width="{cw:.1f}" height="22" fill="{CARD if i % 2 else "#fff"}" stroke="#E3E6EA"/>')
        body.append(_t(x + cw / 2, y0 - 10, d, 10.5, color=SUB))
    y = y0
    for grp, name, s, e, color in rows:
        if name is None:
            body.append(f'<rect x="10" y="{y}" width="{width - 20}" height="{rh}" fill="{CARD}"/>')
            body.append(_t(18, y + 16, grp, 12, "start", INK, 700))
        else:
            body.append(_t(28, y + 16, name, 11.5, "start", INK))
            body.append(f'<rect x="{left + cw * s + 2:.1f}" y="{y + 5}" width="{cw * (e - s + 1) - 4:.1f}" height="{rh - 10}" rx="4" fill="{color}"/>')
        y += rh
    for idx, lab, color in marks:
        x = left + cw * idx + cw / 2
        body.append(f'<line x1="{x:.1f}" y1="{y0 - 4}" x2="{x:.1f}" y2="{y}" stroke="{color}" stroke-dasharray="3 3"/>')
        body.append(f'<path d="M{x:.1f} {y + 4} l6 8 l-6 8 l-6 -8 Z" fill="{color}"/>')
        body.append(_t(x, y + 36, lab, 11, color=color, weight=700))
    return _svg(width, y + 48, "".join(body), title)
