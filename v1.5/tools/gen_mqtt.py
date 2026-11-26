"""로봇 MQTT 계약(AMR-fms common/schemas.py) → gen/mqtt_schemas.html

AMR-fms 리포 루트에서 (common 을 import 해야 하므로):
  .venv/bin/python ../설계서/v1.2/tools/gen_mqtt.py
"""
import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
from common import schemas as S  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "gen" / "mqtt_schemas.html"

MODELS = [
    ("Order", "fms/v1/{id}/order", "FMS → 로봇", "QoS 1"),
    ("OrderNode", "(Order.nodes[])", "", ""),
    ("Action", "(OrderNode.action)", "", ""),
    ("InstantAction", "fms/v1/{id}/instant", "FMS → 로봇", "QoS 1"),
    ("State", "fms/v1/{id}/state", "로봇 → FMS", "QoS 0, 200ms"),
    ("NodeProgress", "(State.node_states[])", "", ""),
    ("ActionProgress", "(State.action_states[])", "", ""),
    ("BatteryInfo", "(State.battery)", "", ""),
    ("ErrorInfo", "(State.errors[])", "", ""),
    ("LoadInfo", "(State.loads[])", "", ""),
    ("ObstacleInfo", "(State.detected_obstacles[])", "", ""),
    ("Connection", "fms/v1/{id}/connection", "로봇(또는 브로커 LWT) → FMS", "QoS 1, retained"),
    ("Factsheet", "fms/v1/{id}/factsheet", "로봇 → FMS", "retained, 선택"),
]


def typ(f):
    import re
    a = f.annotation
    s = str(a) if getattr(a, "__args__", None) else (getattr(a, "__name__", None) or str(a))
    s = s.replace("typing.", "").replace("common.schemas.", "")
    s = re.sub(r"<(?:class|enum) '([^']+)'>", r"\1", s)
    s = re.sub(r"Optional\[(.+)\]", r"\1 ?", s)
    return s.replace("NoneType", "None")


def main():
    out = []
    for name, topic, direction, qos in MODELS:
        m = getattr(S, name)
        rows = []
        for fname, f in m.model_fields.items():
            req = "Y" if f.is_required() else ""
            d = "" if f.is_required() else repr(f.default) if f.default is not None and not callable(f.default) else ""
            if f.default_factory is not None:
                d = "[]" if "list" in str(f.annotation) else "{}"
            rows.append(f"<tr><td class='nw'><code>{escape(fname)}</code></td><td>{escape(typ(f))}</td><td class='c'>{req}</td>"
                        f"<td>{escape(d[:20])}</td><td>{escape(f.description or '')}</td></tr>")
        doc = (m.__doc__ or "").strip().split("\n")[0]
        out.append(f"<div class='api'><h4>{escape(name)} <span class='small'>{escape(topic)} {escape(direction)} {escape(qos)}</span></h4>"
                   + (f"<p class='small'>{escape(doc)}</p>" if doc else "")
                   + "<table><thead><tr><th style='width:22%'>필드</th><th style='width:22%'>타입</th><th style='width:6%'>필수</th>"
                     "<th style='width:10%'>기본</th><th>설명</th></tr></thead>" + "".join(rows) + "</table></div>")
    enums = []
    for en in ("RobotState", "BusySubState", "OperatingMode", "PauseSource", "ActionType", "ActionStatus", "ErrorLevel",
               "ConnectionState", "LocalizationState", "InstantActionType"):
        e = getattr(S, en)
        enums.append(f"<tr><td><code>{en}</code></td><td>{escape(', '.join(x.value for x in e))}</td></tr>")
    out.append("<p class="tcap">&lt;표 7.3&gt; 열거형</p><table><thead><tr><th style='width:22%'>열거형</th><th>값</th></tr></thead>"
               + "".join(enums) + "</table>")
    out.append(f"<p class='small'>PROTOCOL_VERSION = <code>{escape(S.PROTOCOL_VERSION)}</code>. 모든 메시지는 공통 헤더 "
               "<code>version · header_id(송신자별 단조 증가) · timestamp · robot_id</code>를 가진다. State 는 <code>extra=forbid</code> "
               "로 파싱하므로 한쪽만 필드를 바꾸면 깨진다.</p>")
    OUT.write_text("\n".join(out), encoding="utf-8")
    print("저장", OUT)


if __name__ == "__main__":
    main()
