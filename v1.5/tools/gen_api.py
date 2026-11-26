"""FMS OpenAPI(gen/openapi.json) → 설계서 7.2 API 정의표·7.3 API 상세 HTML.

openapi.json 은 AMR-fms 리포 루트에서 다시 뽑는다:
  FMS_DATA_ROOT=$(mktemp -d) FMS_MQTT_PORT=18859 .venv/bin/python -c \
    "import json;from fms_server.main import app;json.dump(app.openapi(),open('<설계서>/v1.1/gen/openapi.json','w'),ensure_ascii=False,indent=1)"
"""
import json
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent

# (그룹 ID 접두, 그룹명, 태그, 관련 화면)
GROUPS = [
    ("API-1", "현장·맵·로봇 등록", "sites", "SC-08 맵 관리 · SC-12 현장 설정 · SC-03 로봇"),
    ("API-2", "목적지·맵 위치", "locations", "SC-09 목적지·도킹"),
    ("API-2", "맵 위 위치 추가", "map points", "SC-01 실시간 맵(＋ 메뉴)"),
    ("API-2", "픽업스테이션", "pickup stations", "SC-01 실시간 맵 · SC-09"),
    ("API-3", "구역(점유 존·금지·감속)", "zones", "SC-01 구역 편집기"),
    ("API-3", "교통 제어", "traffic", "SC-12 선택 맵 교통 제어"),
    ("API-4", "작업", "jobs", "SC-05 작업 게시판"),
    ("API-4", "작업 프리셋", "presets", "SC-06 작업 프리셋"),
    ("API-4", "충전 정책·예약 실행", "charging", "SC-10 운영 제어 · SC-06"),
    ("API-5", "로봇 상태·즉시 명령", "robots", "SC-01 · SC-03 로봇 팝업"),
    ("API-5", "현장 정지·대피", "ops", "SC-10 운영 제어"),
    ("API-6", "승강기", "elevators", "SC-11 엘리베이터"),
    ("API-7", "이력·통계·알림·webhook", "observe", "SC-04 알림 · SC-13 통계"),
    ("API-7", "이벤트 조회", "events", "SC-14 이력"),
    ("API-8", "인증·API 키", "auth", "SC-12 현장 설정(인증)"),
    ("API-9", "상태 점검", None, "—"),
]

KO = {
    "GET /api/v1/robots": "플릿 전체 로봇 상태 조회",
    "GET /api/v1/robots/{robot_id}": "로봇 한 대 상태 조회",
    "POST /api/v1/robots/{robot_id}/init-position": "위치 힌트 전송(INIT_POSITION)",
    "POST /api/v1/robots/{robot_id}/pause": "로봇 일시정지(PAUSE)",
    "POST /api/v1/robots/{robot_id}/resume": "로봇 재개(RESUME)",
    "POST /api/v1/robots/{robot_id}/reset-error": "로봇 오류 해제(RESET_ERROR)",
    "GET /api/v1/sites": "현장 목록",
    "POST /api/v1/sites": "현장 등록",
    "GET /api/v1/sites/{site_id}": "현장 상세",
    "DELETE /api/v1/sites/{site_id}": "현장 삭제",
    "POST /api/v1/sites/{site_id}/maps": "맵 업로드(검증·굽기·버전 생성)",
    "GET /api/v1/sites/{site_id}/maps": "맵 목록",
    "GET /api/v1/sites/{site_id}/maps/{map_id}": "맵 상세(버전 목록)",
    "GET /api/v1/sites/{site_id}/maps/{map_id}/manifest": "맵 버전 메타(manifest)",
    "GET /api/v1/sites/{site_id}/maps/{map_id}/bundle": "맵 번들 zip(로봇 SET_MAP 다운로드)",
    "GET /api/v1/sites/{site_id}/maps/{map_id}/files/{filename}": "맵 버전 파일",
    "POST /api/v1/sites/{site_id}/maps/{map_id}/activate": "맵 버전 활성화",
    "POST /api/v1/sites/{site_id}/robots": "로봇 등록·맵 배정",
    "GET /api/v1/sites/{site_id}/robots": "현장 로봇 목록",
    "PUT /api/v1/sites/{site_id}/robots/{robot_id}": "로봇 재배정·점검·그룹 변경",
    "DELETE /api/v1/sites/{site_id}/robots/{robot_id}": "로봇 등록 해제",
    "GET /api/v1/sites/{site_id}/locations": "목적지 목록",
    "POST /api/v1/sites/{site_id}/locations": "목적지 등록",
    "GET /api/v1/sites/{site_id}/locations/{name}": "목적지 상세",
    "PUT /api/v1/sites/{site_id}/locations/{name}": "목적지 수정·이름 변경",
    "DELETE /api/v1/sites/{site_id}/locations/{name}": "목적지 삭제",
    "POST /api/v1/sites/{site_id}/jobs": "작업 생성(외부 주문 멱등 키 지원)",
    "GET /api/v1/sites/{site_id}/jobs": "작업 목록",
    "PATCH /api/v1/sites/{site_id}/jobs/{job_id}": "대기 작업 우선순위 변경",
    "GET /api/v1/sites/{site_id}/jobs/{job_id}": "작업 상세",
    "DELETE /api/v1/sites/{site_id}/jobs/{job_id}": "종료 작업 삭제",
    "POST /api/v1/sites/{site_id}/jobs/{job_id}/retry": "종료 작업 재시도",
    "POST /api/v1/sites/{site_id}/jobs/{job_id}/dispatch": "작업 수동 배정",
    "POST /api/v1/sites/{site_id}/jobs/{job_id}/cancel": "작업 취소",
    "GET /api/v1/sites/{site_id}/presets": "프리셋 목록",
    "POST /api/v1/sites/{site_id}/presets": "프리셋 생성",
    "PUT /api/v1/sites/{site_id}/presets/{preset_id}": "프리셋 수정",
    "DELETE /api/v1/sites/{site_id}/presets/{preset_id}": "프리셋 삭제",
    "POST /api/v1/sites/{site_id}/presets/{preset_id}/publish": "프리셋 게시(작업 생성)",
    "POST /api/v1/sites/{site_id}/maps/{map_id}/zones": "구역 생성(새 맵 버전)",
    "PUT /api/v1/sites/{site_id}/maps/{map_id}/zones/{zone_id}": "구역 수정(새 맵 버전)",
    "DELETE /api/v1/sites/{site_id}/maps/{map_id}/zones/{zone_id}": "구역 삭제(새 맵 버전)",
    "GET /api/v1/sites/{site_id}/maps/{map_id}/traffic": "교통 상태 조회(정원·예약·존·교착·정체)",
    "PUT /api/v1/sites/{site_id}/maps/{map_id}/traffic": "층 정원·경로 교차 정지 설정",
    "POST /api/v1/sites/{site_id}/maps/{map_id}/locations": "맵에서 목적지 추가",
    "POST /api/v1/sites/{site_id}/maps/{map_id}/docking-stations": "맵에서 충전·도킹 지점 추가",
    "GET /api/v1/sites/{site_id}/pickup-stations": "픽업스테이션 목록·연결 상태",
    "POST /api/v1/sites/{site_id}/maps/{map_id}/pickup-stations": "픽업스테이션 생성",
    "PUT /api/v1/sites/{site_id}/maps/{map_id}/pickup-stations/{station_id}": "픽업스테이션 수정",
    "DELETE /api/v1/sites/{site_id}/maps/{map_id}/pickup-stations/{station_id}": "픽업스테이션 삭제",
    "GET /api/v1/sites/{site_id}/elevators": "승강기 목록·운행 상태",
    "POST /api/v1/sites/{site_id}/elevators": "승강기 연결(층별 구역)",
    "POST /api/v1/sites/{site_id}/elevators/{elevator_id}/recover": "칸 내 로봇 복구",
    "POST /api/v1/sites/{site_id}/elevators/{elevator_id}/fault": "승강기 장애 주입(내장 시뮬레이터)",
    "GET /api/v1/sites/{site_id}/elevators/unlinked": "연결되지 않은 승강기 구역",
    "GET /api/v1/sites/{site_id}/elevators/{elevator_id}": "승강기 상세",
    "PUT /api/v1/sites/{site_id}/elevators/{elevator_id}": "승강기 수정",
    "DELETE /api/v1/sites/{site_id}/elevators/{elevator_id}": "승강기 삭제",
    "GET /api/v1/events": "이벤트 이력 조회",
    "GET /api/v1/sites/{site_id}/ops": "현장 운영 상태(정지·대피)",
    "POST /api/v1/sites/{site_id}/pause": "현장(또는 맵) 전체 정지",
    "POST /api/v1/sites/{site_id}/resume": "현장 정지 해제",
    "POST /api/v1/sites/{site_id}/evacuation": "대피 모드 시작·해제",
    "GET /api/v1/sites/{site_id}/kpi": "KPI 집계(시간·일 단위)",
    "GET /api/v1/alerts": "알림 목록",
    "POST /api/v1/alerts/{alert_id}/ack": "알림 확인",
    "GET /api/v1/webhooks": "webhook 목록",
    "POST /api/v1/webhooks": "webhook 등록",
    "PUT /api/v1/webhooks/{hook_id}": "webhook 수정",
    "DELETE /api/v1/webhooks/{hook_id}": "webhook 삭제",
    "GET /api/v1/auth/me": "현재 키·역할 확인",
    "GET /api/v1/auth/keys": "API 키 목록",
    "POST /api/v1/auth/keys": "API 키 발급",
    "DELETE /api/v1/auth/keys/{name}": "API 키 폐기",
    "GET /api/v1/sites/{site_id}/charging": "자동 충전·대기 정책 조회",
    "PUT /api/v1/sites/{site_id}/charging": "자동 충전·대기 정책 변경",
    "GET /api/v1/sites/{site_id}/charging/spots": "충전소·주차 지점 점유 현황",
    "GET /api/v1/sites/{site_id}/schedules": "예약 실행 목록",
    "POST /api/v1/sites/{site_id}/schedules": "예약 실행 등록",
    "PUT /api/v1/sites/{site_id}/schedules/{schedule_id}": "예약 실행 수정",
    "DELETE /api/v1/sites/{site_id}/schedules/{schedule_id}": "예약 실행 삭제",
    "GET /health": "서버·MQTT 상태 점검",
}


FIELD_KO = {
 "site_id": "현장 ID", "map_id": "맵 ID(현장 안 라벨)", "name": "이름", "robot_id": "로봇 ID", "x": "X 좌표(m)", "y": "Y 좌표(m)",
 "version": "맵 버전(내용 해시 12자)", "type": "종류", "base_version": "편집 기준 맵 버전(낙관적 잠금)", "job_id": "작업 ID",
 "elevator_id": "승강기 ID", "theta": "방향(rad)", "priority": "우선순위(클수록 먼저)", "created_at": "생성 시각", "groups": "그룹 목록",
 "robot_group": "로봇 그룹 필터", "width": "가로(m)", "zone_id": "구역 ID", "preset_id": "프리셋 ID", "commands": "명령(단계) 목록",
 "not_before": "이 시각 전 배정 안 함(ISO)", "deadline": "마감 시각(ISO)", "map_uid": "로봇 보고용 맵 uid", "height": "세로(m)",
 "in_service": "서비스 중(false=점검)", "note": "메모·점검 사유", "status": "상태", "notified_robots": "명령을 보낸 로봇", "stops": "서는 층 목록",
 "auto_assign": "자동 배정", "external_id": "외부 주문 멱등 키", "zone": "구역", "node": "픽업 지점", "return_node": "반납 지점",
 "reason": "사유", "mode": "방식", "robots": "로봇 목록", "warnings": "경고", "order_id": "오더 ID", "order_update_id": "오더 갱신 번호",
 "updated_at": "수정 시각", "rotation": "회전(도)", "state": "상태", "enabled": "사용", "station_id": "스테이션 ID", "site": "현장 필터",
 "limit": "최대 건수", "hook_id": "webhook ID", "schedule_id": "예약 ID", "action_id": "액션 ID", "notify": "로봇에 알림",
 "charging": "충전 중", "despeckle_iterations": "노이즈 정리 반복 횟수", "activate": "업로드 후 활성화", "files": "업로드 파일",
 "target": "목적지 이름", "duration": "시간(초)", "params": "액션 인자", "entry": "진입 방향", "level": "수준", "description": "설명",
 "active": "활성", "model": "모델", "length": "길이(m)", "protocol_version": "프로토콜 버전", "fault": "장애 종류", "count": "수",
 "available_count": "가용 수", "unregistered_count": "미등록 수", "detail": "상세", "created": "생성됨", "activated": "활성화됨",
 "stats": "통계", "preset_name": "프리셋 이름", "done_commands": "완료 명령 수", "total_commands": "전체 명령 수",
 "traffic_waiting": "교통 대기 이유", "stage": "현재 단계", "total_stages": "전체 단계", "stage_label": "단계 이름", "error": "실패 사유",
 "dispatched_at": "배정 시각", "deadline_missed": "마감 초과", "system": "시스템 작업 종류", "retry_of": "재시도 원본 작업",
 "role": "역할(viewer/operator/admin)", "payload_id": "적재물 ID", "active_version": "활성 버전", "versions": "버전 목록",
 "node_id": "노드 ID", "sequence_id": "노드 순서", "released": "통행 허가", "action": "액션", "speed_limit": "속도 상한(m/s)",
 "gates": "진입 방향별 대기·출구", "door_id": "자동문 ID", "door_nodes": "자동문 진입점", "assignment": "배정 정보",
 "set_map_sent": "SET_MAP 전송 여부", "registered_at": "등록 시각", "liveness": "연결 상태", "available_for_job": "배정 가능",
 "registered": "등록 여부", "assigned_map_id": "배정 맵 ID", "assigned_map_uid": "배정 맵 uid", "map_synced": "맵 동기화 일치",
 "display_status": "표시 상태", "connection": "연결 보고", "first_seen": "처음 수신", "last_state_at": "마지막 State 수신",
 "last_connection_at": "마지막 연결 보고", "factsheet": "로봇 사양", "days": "요일(0=월)", "time": "시각 HH:MM", "interval_s": "간격(초)",
 "map_count": "맵 수", "robot_count": "로봇 수", "maps": "맵 목록", "ops": "운영 상태", "pose": "자세", "battery": "배터리",
 "errors": "오류 목록", "action_states": "액션 진행", "last_node_sequence_id": "마지막 노드 순서", "floor": "층 이름",
 "entry_theta": "진입 방향(rad)", "gate_id": "진입 방향 ID", "wait": "대기 node", "exit": "출구 node",
 "max_moving_robots": "층 동시 이동 허가 대수(null=무제한)", "conflict_pause": "경로 교차 시 일시정지", "url": "수신 URL",
 "kinds": "이벤트 종류", "secret": "서명 비밀키", "force": "강제", "filename": "파일 이름", "robot": "로봇 필터", "job": "작업 필터",
 "kind": "이벤트 종류 필터", "severity": "심각도", "since": "시작 시각", "until": "끝 시각", "after_id": "이 id 이후",
 "bucket": "집계 단위(hour/day)", "from": "구간 시작", "to": "구간 끝", "open": "열린 알림만", "alert_id": "알림 ID",
 "is_active": "활성", "key": "API 키(발급 시 한 번만)", "loc": "오류 위치", "msg": "오류 메시지", "input": "입력값", "ctx": "문맥",
}

ADMIN = {"DELETE /api/v1/sites/{site_id}", "GET /api/v1/auth/keys", "POST /api/v1/auth/keys",
         "DELETE /api/v1/auth/keys/{name}", "GET /api/v1/webhooks", "POST /api/v1/webhooks",
         "PUT /api/v1/webhooks/{hook_id}", "DELETE /api/v1/webhooks/{hook_id}"}

# FMS 가 HTTP 상태로 돌려주는 공통 오류 (fms_server/api 예외 변환 규약)
ERRORS = {"GET": "404 대상 없음", "POST": "404 대상 없음 · 409 상태·버전 충돌 · 422 검증 실패",
          "PUT": "404 · 409 base_version 불일치 · 422", "PATCH": "404 · 409 pending 아님 · 422",
          "DELETE": "404 · 409 사용 중(예약·작업 참조)"}


def role(key):
    if key == "GET /health" or "/bundle" in key or "/files/" in key:
        return "공개(로봇)" if key != "GET /health" else "공개"
    if key in ADMIN:
        return "admin"
    return "viewer" if key.startswith("GET") else "operator"


def schema_of(spec, ref_or_schema):
    s = ref_or_schema or {}
    if "$ref" in s:
        return spec["components"]["schemas"][s["$ref"].split("/")[-1]], s["$ref"].split("/")[-1]
    if "allOf" in s and len(s["allOf"]) == 1:
        return schema_of(spec, s["allOf"][0])
    return s, None


def type_of(spec, s):
    if not s:
        return "any"
    if "$ref" in s:
        return s["$ref"].split("/")[-1]
    if "anyOf" in s:
        ts = [type_of(spec, x) for x in s["anyOf"]]
        return " | ".join(t for t in ts if t != "null") + (" ?" if "null" in ts else "")
    if s.get("type") == "array":
        return f"{type_of(spec, s.get('items', {}))}[]"
    if "enum" in s:
        return "enum(" + ", ".join(map(str, s["enum"]))[:60] + ")"
    if s.get("type") == "object" and "additionalProperties" in s:
        return "object(map)"
    return s.get("type", "object")


def fields_table(spec, schema, title):
    s, name = schema_of(spec, schema)
    props = s.get("properties") or {}
    if not props:
        t = type_of(spec, schema) if schema else "JSON"
        return f"<tr><td colspan='5'>{escape(title)}: <code>{escape(t)}</code></td></tr>"
    req = set(s.get("required", []))
    rows = [f"<tr><th colspan='5' style='text-align:left'>{escape(title)} <code>{escape(name or '')}</code></th></tr>"]
    for k, v in props.items():
        desc = v.get("description") or FIELD_KO.get(k, "")
        dflt = v.get("default")
        dtxt = "" if dflt is None else json.dumps(dflt, ensure_ascii=False)
        rows.append(f"<tr><td class='nw'><code>{escape(k)}</code></td><td>{escape(type_of(spec, v))}</td>"
                    f"<td class='c'>{'Y' if k in req else ''}</td><td>{escape(dtxt[:24])}</td><td>{escape(desc)}</td></tr>")
    return "".join(rows)


def ops(spec):
    out = []
    for path, methods in spec["paths"].items():
        for m, o in methods.items():
            out.append((m.upper(), path, o))
    return out


def main():
    spec = json.loads((HERE / "gen" / "openapi.json").read_text(encoding="utf-8"))
    all_ops = ops(spec)
    counters = {}
    listing, detail = [], []
    n_total = 0
    for prefix, gname, tag, screen in GROUPS:
        mine = [(m, p, o) for m, p, o in all_ops if (o.get("tags") or [None])[0] == tag]
        if not mine:
            continue
        detail.append(f"<h3>{escape(gname)} <span class='small'>(태그 <code>{escape(tag or 'health')}</code> · 화면 {escape(screen)})</span></h3>")
        for m, p, o in mine:
            counters[prefix] = counters.get(prefix, 0) + 1
            api_id = f"{prefix}{counters[prefix]:02d}"
            key = f"{m} {p}"
            ko = KO.get(key, o.get("summary", ""))
            n_total += 1
            listing.append(f"<tr><td class='c nw'>{api_id}</td><td>{escape(gname)}</td><td>{escape(ko)}</td>"
                           f"<td class='c'><span class='method {m}'>{m}</span></td><td><code>{escape(p)}</code></td>"
                           f"<td class='c'>{role(key)}</td><td class='c'><span class='badge done'>구현</span></td></tr>")
            rows = []
            params = o.get("parameters") or []
            if params:
                rows.append("<tr><th colspan='5' style='text-align:left'>파라미터 (path·query)</th></tr>")
                for prm in params:
                    sch = prm.get("schema", {})
                    dflt = sch.get("default")
                    rows.append(f"<tr><td class='nw'><code>{escape(prm['name'])}</code></td><td>{escape(prm['in'])} · {escape(type_of(spec, sch))}</td>"
                                f"<td class='c'>{'Y' if prm.get('required') else ''}</td><td>{'' if dflt is None else escape(json.dumps(dflt, ensure_ascii=False))}</td>"
                                f"<td>{escape(prm.get('description') or sch.get('description') or FIELD_KO.get(prm['name'], ''))}</td></tr>")
            body = (o.get("requestBody") or {}).get("content", {})
            if body:
                ctype, cval = next(iter(body.items()))
                rows.append(fields_table(spec, cval.get("schema"), f"요청 본문 ({ctype})"))
            resp = (o.get("responses") or {}).get("200") or (o.get("responses") or {}).get("201") or {}
            rschema = (resp.get("content") or {}).get("application/json", {}).get("schema")
            if rschema and (rschema.get("$ref") or rschema.get("properties")):
                rows.append(fields_table(spec, rschema, "응답 200"))
            else:
                rows.append(f"<tr><td colspan='5'>응답 200: <code>{escape(type_of(spec, rschema) if rschema else 'JSON')}</code></td></tr>")
            desc = (o.get("description") or "").strip()
            detail.append(
                f"<div class='api'><h4>{api_id} {escape(ko)}</h4>"
                f"<table><tr><td colspan='5'><span class='method {m}'>{m}</span><code>{escape(p)}</code>"
                f" &nbsp; 권한 <b>{role(key)}</b> &nbsp; 오류 {escape(ERRORS.get(m, ''))}"
                + (f"<br><span class='small'>{escape(desc)}</span>" if desc else "") + "</td></tr>"
                "<tr><th style='width:22%'>이름</th><th style='width:20%'>위치·타입</th><th style='width:6%'>필수</th><th style='width:12%'>기본값</th><th>설명</th></tr>"
                + "".join(rows) + "</table></div>")
    (HERE / "gen" / "api_list.html").write_text(
        "<table><thead><tr><th>ID</th><th>그룹</th><th>기능</th><th>메서드</th><th>URI</th><th>권한</th><th>상태</th></tr></thead><tbody>"
        + "".join(listing) + "</tbody></table>", encoding="utf-8")
    (HERE / "gen" / "api_rest.html").write_text("\n".join(detail), encoding="utf-8")
    (HERE / "gen" / "api_count.txt").write_text(str(n_total), encoding="utf-8")


if __name__ == "__main__":
    main()
