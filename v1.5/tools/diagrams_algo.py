"""v1.3 추가 다이어그램 — 핵심 알고리즘(활동도·판정 흐름·ZonePlanner 그래프·클래스도).

명세는 AMR-fms 작업 트리(2026-11-26) 코드 기준이다. 주황 = 이번 개발.
"""
from diagrams import BLUE, GREEN, INK, ORANGE, PURPLE, RED, SUB, boxes


def algos():
    d = {}
    # 1. 배정 루프 활동도 (allocate_pending → rank_candidates → dispatch)
    d["act_allocate"] = boxes("배정 루프 활동도 — JobCoordinator.allocate_pending() (1초마다)", {
        "s": (60, 40, 0, 0, "", INK, "start"),
        "mq": (110, 15, 190, 50, "MQTT 연결됨?", BLUE, "diamond"),
        "tt": (340, 15, 210, 50, "tick_traffic()\ntick_multifloor()", BLUE),
        "sort": (590, 15, 380, 50, "대기 작업 정렬: auto_assign ∧ pending\n키 (−priority, created_at, job_id)", BLUE),
        "dl": (590, 95, 380, 46, "마감 지남 → deadline_missed 이벤트만 (작업 계속)", SUB),
        "nb": (590, 160, 380, 50, "not_before 전? / 현장 배정 차단?", BLUE, "diamond"),
        "cand": (590, 240, 380, 56, "후보 = available_robots() ∩ 현장 등록\n(직접 지정이면 그 로봇만, 정지된 맵 제외)", BLUE),
        "rank": (590, 320, 380, 66, "rank_candidates(): eligible() 로 거르고\n비용 = 경로거리 + 60m × 환승 + 0.2 × (100 − 잔량)\n+ (계획) 예상 대기 × 평균 속도", BLUE),
        "loop": (590, 410, 380, 50, "순위대로 dispatch(job, robot) 시도", BLUE),
        "ok": (590, 485, 180, 46, "성공 → 다음 작업", GREEN),
        "fail": (790, 485, 180, 46, "전부 실패 → 대기 이유 기록", ORANGE),
        "pre": (790, 555, 180, 46, "_preempt_staging()\n(대기 복귀 로봇 선점)", SUB),
        "g": (20, 160, 520, 455, "dispatch(job, robot) — 최종 가용성 재검사", RED, "group"),
        "d1": (40, 195, 480, 40, "MQTT 연결 · job 이 pending · 로봇에 활성 작업 없음", INK),
        "d2": (40, 245, 480, 40, "State 수신 · 잔량 > 0 · (정책) 잔량 ≥ min_job_charge", INK),
        "d3": (40, 295, 480, 40, "available_for_job: ONLINE ∧ IDLE ∧ AUTO ∧ ¬paused ∧ LOCALIZED", INK),
        "d4": (40, 345, 480, 40, "현장 등록 · in_service · 맵 uid 일치 · 맵 version = 활성", INK),
        "d5": (40, 395, 480, 40, "다층이면 _dispatch_multi (승강기 stage 계획)", INK),
        "d6": (40, 445, 480, 50, "compile_to_order → traffic.prepare(대기·출구 node 삽입)\n→ traffic.update(초기 허가)", INK),
        "d7": (40, 505, 480, 40, "status=assigned · jobs.json 저장 (발행 전 저장)", INK),
        "d8": (40, 555, 480, 40, "publish_order → job.assigned 이벤트", INK),
    }, [("s", "mq", ""), ("mq", "tt", "예"), ("tt", "sort", ""), ("sort", "dl", ""), ("dl", "nb", ""),
        ("nb", "cand", "아니오"), ("cand", "rank", ""), ("rank", "loop", ""), ("loop", "ok", "성공"), ("loop", "fail", "JobError"),
        ("fail", "pre", ""), ("loop", "d1", "", RED, "dash", [(560, 435), (560, 215)]),
        ("d1", "d2", ""), ("d2", "d3", ""), ("d3", "d4", ""), ("d4", "d5", ""), ("d5", "d6", ""), ("d6", "d7", ""), ("d7", "d8", "")],
        width=1000, height=640, legend=[(BLUE, "배정 루프"), (RED, "dispatch 재검사(실패 시 JobError)"), (ORANGE, "실패 처리")])

    # 2. 통행 허가 판정 흐름 (TrafficController.update, crossing 하나)
    d["act_traffic"] = boxes("통행 허가 판정 — TrafficController.update(job) 의 crossing 하나", {
        "s": (60, 35, 0, 0, "", INK, "start"),
        "pre": (100, 10, 400, 50, "로봇 fresh(ONLINE·LOCALIZED) ∧ ¬paused ∧ ¬ERROR\n∧ 맵 uid·version 일치?", BLUE, "diamond"),
        "w0": (560, 10, 400, 50, "대기 이유: 맵·위치 확인 대기 (허가 그대로)", SUB),
        "fl": (100, 85, 400, 46, "acquire_floor: 층 정원 안?", BLUE, "diamond"),
        "w1": (560, 85, 400, 46, "대기 이유: 층별 동시 이동 대수 제한", SUB),
        "ps": (100, 155, 400, 50, "출구 통과(last_node = exit) ∧ 차체 외접원이 존 밖?", BLUE, "diamond"),
        "dn": (560, 155, 400, 50, "crossing done → 다음 crossing 검사", GREEN),
        "own": (100, 230, 400, 46, "이미 내 존 예약? (같은 order)", BLUE, "diamond"),
        "t1": (560, 230, 400, 46, "through = 출구 node (허가 유지)", GREEN),
        "wn": (100, 300, 400, 46, "대기 node 예약이 남의 것?", BLUE, "diamond"),
        "w2": (560, 300, 400, 46, "through = 대기 node 직전 · '대기 node 사용 중'", ORANGE),
        "cs": (100, 370, 400, 50, "(내 대기 예약이 없으면) 대기 node 주변 차체 여유\n+ 남의 예약 pose 와 거리 OK?", BLUE, "diamond"),
        "w3": (560, 370, 400, 50, "through = 대기 node 직전 · '대기 node 주변 확인 대기'\n유휴 로봇이 막으면 aside_requests 에 추가", ORANGE),
        "rw": (100, 445, 400, 40, "wait 예약 저장 → traffic.reserve", BLUE),
        "at": (80, 505, 440, 66, "대기 node 도착·정지(0.08 m, v<0.01) ∧ 존 예약 없음\n∧ 존 안 다른 로봇 없음·모두 fresh ∧ 출구 공간 OK\n(자동문이면 열림 확인)", BLUE, "diamond"),
        "rz": (560, 505, 400, 60, "zone 예약 저장(bounds·exit·update+1)\n→ through = 출구 node · 대기 해제", GREEN),
        "w4": (100, 600, 400, 40, "through = 대기 node · '점유 존 진입 허가 대기'", ORANGE),
        "rel": (560, 600, 400, 40, "through 까지 released=true · 바뀌면 order_update_id+1", BLUE),
    }, [("s", "pre", ""), ("pre", "w0", "아니오"), ("pre", "fl", "예"), ("fl", "w1", "아니오"), ("fl", "ps", "예"),
        ("ps", "dn", "예"), ("ps", "own", "아니오"), ("own", "t1", "예"), ("own", "wn", "아니오"), ("wn", "w2", "예"), ("wn", "cs", "아니오"),
        ("cs", "w3", "아니오"), ("cs", "rw", "예"), ("rw", "at", ""), ("at", "rz", "예"), ("at", "w4", "아니오"),
        ("rz", "rel", ""), ("w4", "rel", "", None, None, [(530, 615)]), ("t1", "rel", "", GREEN, "dash", [(985, 253), (985, 615)])],
        width=1000, height=680, legend=[(GREEN, "허가 확장"), (ORANGE, "대기(허가 멈춤)"), (SUB, "판단 보류")])

    # 3. ZonePlanner 그래프 예시
    d["zone_graph"] = boxes("ZonePlanner — 대기·출구 node 그래프 위 최단 경로 (예: 주 통로 Z1 vs 우회 Z2)", {
        "g1": (330, 30, 300, 120, "점유 존 Z1 (주 통로, 1대 폭)", RED, "group"),
        "g2": (330, 260, 300, 120, "점유 존 Z2 (우회 통로)", RED, "group"),
        "st": (30, 170, 120, 50, "출발 (로봇 위치)", PURPLE, "round"),
        "w1": (200, 70, 110, 44, "Z1 대기 node\n(서쪽 gate)", BLUE),
        "e1": (650, 70, 110, 44, "Z1 출구 node\n(동쪽)", BLUE),
        "w2": (200, 300, 110, 44, "Z2 대기 node", BLUE),
        "e2": (650, 300, 110, 44, "Z2 출구 node", BLUE),
        "gl": (840, 170, 130, 50, "목적지", GREEN, "round"),
        "nt": (30, 400, 940, 52, "간선 비용 = 격자 A* 거리(m). 출발·출구 → 대기·목적지 간선은 모든 존을 벽으로 막고, 대기 → 출구 간선만 그 존을 연다.\n현재(distance): Z1 경로 5+14+6 = 25 m < Z2 경로 9+18+9 = 36 m → Z1.  계획(rule/ai): 대기→출구 간선에 '예상 대기(초) × 평균 속도'를 더해 Z1 이 붐비면 Z2 선택", SUB, "dash"),
    }, [("st", "w1", "5 m"), ("w1", "e1", "14 m (+ 예상 대기)", ORANGE), ("e1", "gl", "6 m"),
        ("st", "w2", "9 m"), ("w2", "e2", "18 m (+ 예상 대기)", ORANGE), ("e2", "gl", "9 m")], width=1000, height=470)

    # 4. 핵심 클래스 다이어그램
    d["cls_core"] = boxes("핵심 클래스와 의존 관계 (fms_server/)", {
        "jc": (360, 20, 280, 120, "JobCoordinator (task.py)\n— lock: RLock\n+ dispatch() · cancel() · allocate_pending()\n+ tick_safety() · tick_traffic() · tick_reroute()\n− _advance() · _finish() · _run_stage()", RED),
        "js": (30, 20, 260, 90, "JobStore (task.py)\n+ create() · create_system()\n+ save() · list() · by_external_id()\n(jobs.json 원자 저장)", BLUE),
        "al": (30, 140, 260, 70, "JobAllocator (allocator.py)\n1초 스레드: allocate_pending →\ntick_safety → ticks[]", BLUE),
        "tc": (360, 175, 280, 120, "TrafficController (traffic.py)\n+ prepare() · update() · reconcile()\n+ acquire_floor() · snapshot()\n+ analyze() · revoke_safe() · path_conflicts()\n(traffic.json, TTL 없음)", BLUE),
        "zp": (700, 175, 270, 90, "ZonePlanner\n+ route(start, goal) → [(zone, gate)]\n+ distance(a, b, allowed) (격자 A*)\n+ set_obstacles()", BLUE),
        "rp": (700, 290, 270, 70, "RouteCostPolicy (계획)\n+ cost(route, snap)\n+ expected_wait(zone, gate, snap, eta)", ORANGE, "dash"),
        "ai": (700, 385, 270, 70, "ai_adapter (계획)\n+ predict_wait · predict_soc_after\n+ anomaly_score · status · reload", ORANGE, "dash"),
        "fl": (30, 245, 260, 90, "Fleet (fleet.py)\n+ apply_state/connection/factsheet\n+ available_robots() · add_listener()\nRobotRecord.liveness()", BLUE),
        "ob": (360, 330, 280, 60, "ObstacleRegistry (obstacles.py)\n맵 전역 장애물 30초 확인·5분 유지", BLUE),
        "bm": (30, 370, 260, 70, "BatteryManager (battery.py)\n+ tick() · move_aside()\n충전·대기 복귀·대피 시스템 작업", BLUE),
        "ec": (360, 420, 280, 60, "ElevatorController (elevator_ctl.py)\n+ acquire()/release() — 요청 시각 FIFO", BLUE),
        "ev": (30, 455, 260, 60, "EventLog (events.py)\n+ record() 큐 · query()", GREEN, "db"),
        "rg": (700, 20, 270, 80, "SiteRegistry (sites.py)\n+ assignment_for() · map_store()\nMapStore: 버전·활성·uid", BLUE),
        "as": (700, 110, 270, 50, "assign.py: rank_candidates · eligible", BLUE),
    }, [("al", "jc", "호출"), ("jc", "js", "저장"), ("jc", "tc", "prepare/update"), ("tc", "zp", "route"), ("zp", "rp", "간선 비용", ORANGE, "dash"),
        ("rp", "ai", "predict_wait", ORANGE, "dash"), ("jc", "fl", "리스너", None, None, [(305, 130), (305, 290)]), ("tc", "ob", "rects"),
        ("jc", "bm", "move_aside", None, None, [(318, 130), (318, 405)]), ("jc", "ec", "임대", None, None, [(344, 130), (344, 450)]), ("jc", "ev", "record", GREEN, "dash", [(331, 130), (331, 485)]),
        ("jc", "rg", "맵·배정"), ("jc", "as", "순위"), ("as", "rp", "", ORANGE, "dash", [(985, 135), (985, 325)])],
        width=1000, height=560, legend=[(RED, "락 소유"), (BLUE, "구현"), (ORANGE, "이번 개발")])

    # 5. 계획: 장애 자동 재배정 활동도 (fail_lost)
    d["act_failover"] = boxes("계획 — 장애 작업 자동 재배정 JobCoordinator.fail_lost() (1초 tick)", {
        "s": (60, 40, 0, 0, "", INK, "start"),
        "lv": (100, 15, 380, 50, "작업 중 로봇 liveness ∈ {LOST, STALE}?", ORANGE, "diamond"),
        "no": (540, 15, 420, 50, "아무것도 안 함 (FATAL 은 _advance 가 이미 failed 처리)", SUB),
        "gr": (100, 90, 380, 50, "LOST: 즉시 / STALE: 3초 + 유예 2초 경과?", ORANGE, "diamond"),
        "wt": (540, 90, 420, 50, "다음 tick 에 다시 (통신 순간 끊김 오판 방지)", SUB),
        "ck": (100, 165, 380, 50, "승강기 칸 안 작업? (in_car)", ORANGE, "diamond"),
        "kp": (540, 165, 420, 50, "자동 재배정 안 함 → elevator_attention 알림, 운영자 복구(SC-11)", RED),
        "f": (100, 240, 380, 50, "job → failed(robot_lost) · 실패 사유·시각 기록", ORANGE),
        "rt": (100, 310, 380, 50, "재시도 작업 생성: 같은 명령 · resume_from = done_commands\nretry_of = 원본 · priority 유지", ORANGE),
        "lz": (100, 380, 380, 50, "교통 예약은 그대로 (퇴장 증거 없음) · 존 상태 '확인 필요'", RED),
        "ev": (100, 450, 380, 50, "job.retry_auto · job.failed 이벤트 → 다음 tick 배정", ORANGE),
        "nt": (540, 240, 420, 260, "· 재시도 작업의 경로 선택은 '확인 필요' 존을 막힌 존으로 본다\n  (ZonePlanner 에 그 존을 장애물로 넘김) → 우회하거나 대기 node 앞에서 기다린다.\n· 네트워크만 끊긴 로봇은 허가 구간까지 계속 달릴 수 있다.\n  허가 밖으로는 못 가므로 충돌은 없지만 같은 운반을 두 번 할 수 있다.\n· 그래서 재접속한 로봇이 종료된 작업의 order_id 를 보고하면\n  FMS 가 즉시 CANCEL_ORDER 를 보낸다(중복 실행 차단).\n\n목표 시간: kill → LWT 로 즉시 LOST → 다음 tick(≤1초) 재시도 생성\n→ 그다음 tick(≤1초) 배정 = 재배정 5초 이내 (NFR-04)", SUB, "dash"),
    }, [("s", "lv", ""), ("lv", "no", "아니오"), ("lv", "gr", "예"), ("gr", "wt", "아니오"), ("gr", "ck", "예"),
        ("ck", "kp", "예"), ("ck", "f", "아니오"), ("f", "rt", ""), ("rt", "lz", ""), ("lz", "ev", "")],
        width=1000, height=520)
    return d
