"""gen/api_list.html → gen/api_roles.html (API 그룹 × 역할 권한 매트릭스).

build.py 가 gen_api 다음에 부른다. 표 번호는 src 에서 붙인다(이 파일은 표 본문만 만든다).
"""
import html
import re
from collections import OrderedDict
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
ROLES = ("공개", "viewer", "operator", "admin")


def main():
    src = (HERE / "gen" / "api_list.html").read_text(encoding="utf-8")
    rows = re.findall(r"<tr><td class='c nw'>(API-\d+)</td><td>(.*?)</td><td>(.*?)</td><td class='c'><span class='method (\w+)'>"
                      r".*?</span></td><td><code>(.*?)</code></td><td class='c'>(.*?)</td>", src)
    groups = OrderedDict()
    for api, group, _name, method, _path, role in rows:
        g = groups.setdefault(group, {"ids": [], "cnt": {r: 0 for r in ROLES}, "other": 0, "methods": set()})
        g["ids"].append(api)
        g["methods"].add(method)
        role = html.unescape(role).strip()
        if role in g["cnt"]:
            g["cnt"][role] += 1
        else:
            g["other"] += 1
    out = ["<table><thead><tr><th style='width:24%'>API 그룹</th><th style='width:15%'>ID 범위</th><th style='width:13%'>메서드</th>"
           + "".join(f"<th class='c'>{r}</th>" for r in ROLES) + "<th class='c'>기타(토큰)</th></tr></thead>"]
    total = {r: 0 for r in ROLES}
    other = 0
    for group, g in groups.items():
        ids = g["ids"]
        rng = ids[0] if len(ids) == 1 else f"{ids[0]} ~ {ids[-1][4:]}"
        cells = "".join(f"<td class='c'>{g['cnt'][r] or ''}</td>" for r in ROLES)
        out.append(f"<tr><td>{html.escape(group)}</td><td class='nw'>{rng}</td><td>{' · '.join(sorted(g['methods']))}</td>{cells}"
                   f"<td class='c'>{g['other'] or ''}</td></tr>")
        for r in ROLES:
            total[r] += g["cnt"][r]
        other += g["other"]
    out.append("<tr><th colspan='3'>합계 (" + str(len(rows)) + "개)</th>" + "".join(f"<th class='c'>{total[r]}</th>" for r in ROLES)
               + f"<th class='c'>{other}</th></tr></table>")
    (HERE / "gen" / "api_roles.html").write_text("".join(out), encoding="utf-8")
    print("권한 매트릭스:", len(rows), "개 API")


if __name__ == "__main__":
    main()
