"""설계서 다이어그램 명세 → assets/diagrams/*.svg

명세는 AMR-fms 코드 기준(2026-11-25)이다. 주황(ORANGE)은 이번 개발(12/09 기능 동결)에서 추가하는 부분.
"""
import shutil
from pathlib import Path

from diagrams import (BLUE, GREEN, INK, ORANGE, PURPLE, RED, SUB, boxes, erd, gantt, sequence, usecase)

HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "assets" / "diagrams"
PROPOSAL = HERE.parent.parent / "제안서" / "v1.2" / "proposal-v1.2" / "assets"

P_OP = ("op", "운영자", "actor")
P_AD = ("ad", "관리자", "actor")
P_WEB = ("web", "웹 관제 화면\n(static/*.js)", "boundary")
P_API = ("api", "REST API\n(FastAPI)", "control")
P_JC = ("jc", "JobCoordinator\n(task.py)", "control")
P_AL = ("al", "배정 루프\n(allocator.py 1초)", "control")
P_TR = ("tr", "TrafficController\n(traffic.py)", "control")
P_ST = ("st", "상태 파일\n(jobs/traffic.json)", "entity")
P_EV = ("ev", "EventLog\n(events.db)", "entity")
P_MQ = ("mq", "Mosquitto\n브로커", "ext")
P_RB = ("rb", "로봇 프로세스\n(C++ robot_client)", "robot")
P_FL = ("fl", "Fleet\n(fleet.py)", "control")
P_AI = ("ai", "ai_adapter\n(계획)", "ai")


def seqs():
    d = {}
    d["sd01_publish"] = sequence("SD-01 작업 게시 → 자동 배정 → 오더 발행", [P_OP, P_WEB, P_API, P_JC, P_AL, P_TR, P_MQ, P_RB], [
        ("m", "op", "web", "프리셋 선택 · [작업 생성]"),
        ("m", "web", "api", "POST /sites/{site}/presets/{id}/publish {}"),
        ("m", "api", "jc", "publish(preset) — 명령·좌표·맵 스냅샷 복사"),
        ("s", "jc", "Job 생성 (pending, auto_assign)"),
        ("m", "jc", "api", "JobOut", "ret"),
        ("m", "api", "web", "200 JobOut → 게시판 갱신", "ret"),
        ("f", "loop", "1초마다", [
            ("m", "al", "jc", "allocate_pending() — (-priority, created_at) 순"),
            ("m", "jc", "jc", "rank_candidates(): 경로 거리 + 환승 벌점 + 잔량 가산", "sync"),
            ("n", "jc", "이번 개발: 비용에 '예상 대기' 항 추가 (거리 → 예약 수 규칙 → AI)", "al"),
            ("m", "jc", "tr", "prepare(job, order): 대기·출구 node 삽입"),
            ("m", "tr", "tr", "acquire_floor → 대기 node 예약 → released 컷", "sync"),
            ("m", "tr", "jc", "허가 구간까지 released=true", "ret"),
            ("s", "jc", "traffic.json·jobs.json 저장 (발행 전 저장)"),
            ("m", "jc", "mq", "publish fms/v1/{id}/order"),
            ("m", "mq", "rb", "Order(order_id, update_id=0, nodes)", "async"),
        ]),
        ("m", "rb", "mq", "State(order_id, node_states, sub_state) 200ms", "async", PURPLE),
        ("m", "mq", "jc", "fleet.apply_state → _advance", "async"),
        ("s", "jc", "첫 수신 확인 → working, job.working 기록"),
    ])
    d["sd02_zone"] = sequence("SD-02 점유 존 통과 (대기 node → 진입 허가 → 출구 통과·차체 이탈 → 해제)", [P_RB, P_MQ, P_FL, P_JC, P_TR, P_ST], [
        ("n", "rb", "오더 노드: … n2(대기 node, released=true) n3(출구 node, released=false) …", "tr"),
        ("m", "rb", "mq", "State: n2 도착, velocity≈0, sub_state=WAITING", "async", PURPLE),
        ("m", "mq", "fl", "apply_state", "async"),
        ("m", "fl", "jc", "리스너 → update(job)"),
        ("m", "jc", "tr", "update(job)"),
        ("f", "alt", "존 비어 있음 ∧ 출구 공간 비어 있음 ∧ 다른 로봇 상태 확실", [
            ("s", "tr", "존 예약(zone → job) · 출구까지 허가"),
            ("m", "tr", "st", "traffic.json 원자 저장"),
            ("m", "tr", "jc", "released 확장", "ret"),
            ("m", "jc", "mq", "Order 재발행 (order_update_id+1, n3 released=true)"),
            ("m", "mq", "rb", "Order", "async"),
        ], [("아니면", [
            ("s", "tr", "set_waiting(reason) → traffic.wait 기록"),
            ("n", "tr", "이번 개발: traffic.wait 에 zone_id·gate_id·대기열 길이 추가 (혼잡 예측 라벨)", "st"),
        ])]),
        ("m", "rb", "mq", "State: 존 통과 중 (BUSY/MOVING)", "async", PURPLE),
        ("m", "rb", "mq", "State: last_node = n3, 차체 외접원이 존 밖", "async", PURPLE),
        ("m", "mq", "fl", "apply_state", "async"),
        ("m", "fl", "tr", "update(job)"),
        ("f", "opt", "출구 통과 ∧ 차체 이탈이 State 로 확인됨", [
            ("s", "tr", "존 예약 해제 (TTL 없음, 증거로만)"),
            ("m", "tr", "st", "저장 · traffic.wait_end(seconds) 기록"),
        ]),
        ("n", "tr", "취소·오류·통신 두절은 퇴장 증거가 아니다 → 예약 유지, 존 상태 '확인 필요'", "st"),
    ])
    d["sd03_cancel"] = sequence("SD-03 작업 취소", [P_OP, P_WEB, P_API, P_JC, P_TR, P_MQ, P_RB], [
        ("m", "op", "web", "게시판 [취소]"),
        ("m", "web", "api", "POST /sites/{site}/jobs/{id}/cancel"),
        ("m", "api", "jc", "cancel(job_id)"),
        ("f", "alt", "pending", [("s", "jc", "canceled 로 바로 종료")],
         [("assigned / working", [
             ("s", "jc", "canceling 전이"),
             ("m", "jc", "mq", "instant CANCEL_ORDER"),
             ("m", "mq", "rb", "CANCEL_ORDER", "async"),
             ("m", "rb", "mq", "State: order 비움, IDLE", "async", PURPLE),
             ("m", "mq", "jc", "apply_state", "async"),
             ("s", "jc", "canceled, job.canceled 기록"),
             ("m", "jc", "tr", "update: 정지·존 밖이면 예약 반납, 존 안이면 유지"),
         ])]),
        ("m", "api", "web", "JobOut(status)", "ret"),
    ])
    d["sd04_pause"] = sequence("SD-04 로봇 일시정지·재개·오류 해제", [P_OP, P_WEB, P_API, P_MQ, P_RB], [
        ("m", "op", "web", "로봇 팝업 [일시정지]"),
        ("m", "web", "api", "POST /robots/{id}/pause"),
        ("m", "api", "mq", "instant PAUSE (send_instant)"),
        ("m", "mq", "rb", "PAUSE", "async"),
        ("m", "rb", "mq", "State: paused=true, pause_source=FMS", "async", PURPLE),
        ("m", "op", "web", "[재개]"),
        ("m", "web", "api", "POST /robots/{id}/resume"),
        ("f", "alt", "pause_source = FMS", [
            ("m", "api", "mq", "instant RESUME"),
            ("m", "mq", "rb", "RESUME → 현재 위치에서 A* 재계산 후 다음 노드부터", "async"),
        ], [("pause_source = LOCAL", [("m", "api", "web", "409 로봇에서 건 정지는 로봇에서 해제", "ret", RED)])]),
        ("m", "op", "web", "[오류 해제]"),
        ("m", "web", "api", "POST /robots/{id}/reset-error"),
        ("m", "api", "mq", "instant RESET_ERROR"),
    ])
    d["sd05_failure"] = sequence("SD-05 로봇 장애 감지 → 작업 종료 → 재배정", [P_RB, P_MQ, P_FL, P_AL, P_JC, P_TR, P_EV], [
        ("f", "alt", "프로세스 kill (장애 주입)", [
            ("m", "mq", "fl", "LWT: connection CONNECTION_BROKEN (브로커가 대신 발행)", "async", RED),
        ], [("FATAL 오류", [
            ("m", "rb", "mq", "State.errors=[FATAL …], state=ERROR", "async", PURPLE),
            ("m", "mq", "jc", "apply_state → job failed(오류 내용)", "async"),
        ]), ("State 3초 미수신", [("s", "fl", "liveness = STALE")])]),
        ("m", "al", "fl", "tick: liveness 확인"),
        ("s", "fl", "LOST/STALE 로봇은 배정 후보에서 제외"),
        ("m", "al", "jc", "이번 개발: LOST/STALE 로봇의 활성 작업 failed(robot_lost) (fail_lost, 6.6.10)", "sync", ORANGE),
        ("m", "jc", "jc", "재시도 작업 생성 (retry_of, 같은 명령) — FATAL 은 운영자 판단", "sync", ORANGE),
        ("m", "jc", "tr", "update: 예약은 증거 없이 풀지 않음"),
        ("n", "tr", "존 안에서 멈춘 로봇의 존은 '확인 필요'로 남아 다른 로봇은 우회 통로 또는 대기", "ev"),
        ("m", "al", "jc", "다음 tick: 재시도 작업 배정 (목표 5초 이내)", "sync", ORANGE),
        ("m", "jc", "ev", "job.failed · job.assigned · alert(robot_offline 30초)"),
    ])
    d["sd06_ws"] = sequence("SD-06 실시간 맵 갱신 (WebSocket)", [P_OP, P_WEB, P_API, P_FL, P_MQ, P_RB], [
        ("m", "op", "web", "실시간 맵 열기"),
        ("m", "web", "api", "GET /sites/{site}/maps/{map} · /files/navi_gridmap.baked.png"),
        ("m", "web", "api", "WS /api/v1/robots/stream"),
        ("f", "loop", "로봇마다 200ms", [
            ("m", "rb", "mq", "State", "async", PURPLE),
            ("m", "mq", "fl", "apply_state (paho 스레드)", "async"),
            ("m", "fl", "api", "broadcaster: call_soon_threadsafe", "async"),
            ("m", "api", "web", "robot 변경분 JSON", "async"),
            ("s", "web", "Canvas 다시 그리기 (로봇·대기 이유·존 상태)"),
        ]),
        ("n", "web", "목표: State 발행 → 화면 표시 p95 500ms 이하 (10대, LAN)", "rb"),
    ])
    d["sd07_alert"] = sequence("SD-07 알림 발생 → 확인", [P_AL, ("alr", "AlertManager\n(alerts.py)", "control"), P_EV, P_API, P_WEB, P_OP], [
        ("f", "loop", "1초 tick", [("m", "al", "alr", "상태 규칙 평가 (오프라인 30초, 배터리 critical, 교착, pending 장기화…)")]),
        ("m", "ev", "alr", "구독: job.failed · job.deadline_missed", "async"),
        ("s", "alr", "같은 key 는 열린 알림 하나만"),
        ("m", "alr", "ev", "alerts INSERT, alert.opened 기록"),
        ("m", "ev", "api", "EventStream", "async"),
        ("m", "api", "web", "WS /events/stream → 배지 + 토스트", "async"),
        ("m", "op", "web", "알림 [확인]"),
        ("m", "web", "api", "POST /alerts/{id}/ack"),
        ("m", "api", "alr", "ack(actor)"),
        ("s", "alr", "상태 규칙 알림은 조건이 사라지면 스스로 닫힘"),
    ])
    d["sd08_kpi"] = sequence("SD-08 통계(KPI) 조회", [P_OP, P_WEB, P_API, ("kpi", "kpi.py", "control"), P_EV], [
        ("m", "op", "web", "통계 · 기간 선택"),
        ("m", "web", "api", "GET /sites/{site}/kpi?bucket=hour"),
        ("m", "api", "kpi", "compute(site, from, to, bucket)"),
        ("m", "kpi", "ev", "SELECT events WHERE site_id, ts 구간"),
        ("s", "kpi", "완료·실패, 배정 대기, 수행 시간, 가동률, 주행 거리, 교통 대기, 교착"),
        ("n", "kpi", "이번 개발: 존별 대기 집계(traffic.wait_end + zone_id), 운행(run_id)별 필터", "ev"),
        ("m", "api", "web", "버킷 배열", "ret"),
        ("s", "web", "Canvas 막대·누적 그래프"),
    ])
    d["sd09_route_ai"] = sequence("SD-09 예상 대기를 반영한 통로 선택 (이번 개발)", [P_JC, P_TR, ("pol", "RouteCostPolicy\n(정책 객체)", "plan"), P_AI, P_EV], [
        ("m", "jc", "tr", "prepare(job, order)"),
        ("m", "tr", "tr", "ZonePlanner: 후보 gate 순서 (통로 A, 우회 통로 B …)", "sync"),
        ("f", "loop", "후보 경로마다", [
            ("m", "tr", "pol", "cost(route, snapshot)", "sync", ORANGE),
            ("f", "alt", "policy = distance", [("s", "pol", "이동 시간만", ORANGE)],
             [("policy = rule", [("s", "pol", "이동 + 예약 수 × 평균 통과 시간", ORANGE)]),
              ("policy = ai", [
                  ("m", "pol", "ai", "predict_wait(zone, 배정 시점 스냅샷)", "sync", ORANGE),
                  ("m", "ai", "pol", "예상 대기(초) · 100ms 초과·실패 시 None", "ret", ORANGE),
                  ("s", "pol", "None 이면 rule 값으로 대체", ORANGE),
              ])]),
        ]),
        ("m", "pol", "tr", "비용 최소 gate 순서", "ret", ORANGE),
        ("m", "tr", "ev", "route.choice(후보·비용·정책) 기록", "sync", ORANGE),
        ("n", "tr", "진입 허가는 그대로 SD-02 규칙 (AI 는 허가를 바꾸지 않는다)", "ev"),
    ])
    d["sd10_anomaly"] = sequence("SD-10 이상 징후 → 점검 후보 표시 (이번 개발)", [P_RB, P_FL, P_AL, P_AI, P_EV, P_WEB, P_OP], [
        ("m", "rb", "fl", "State 200ms (속도·잔량·위치·허가 상태)", "async", PURPLE),
        ("f", "loop", "1초 tick", [
            ("m", "al", "ai", "anomaly_score(robot, 최근 60초 창)", "sync", ORANGE),
            ("m", "ai", "al", "점수 · 근거 특징 상위 3개", "ret", ORANGE),
        ]),
        ("f", "opt", "점수 > 임계 연속 3창", [
            ("m", "al", "ev", "robot.anomaly 기록 · 알림 rule=anomaly", "sync", ORANGE),
            ("m", "ev", "web", "WS 이벤트 → 점검 후보 패널", "async", ORANGE),
        ]),
        ("m", "op", "web", "근거 확인 → [점검 전환] (in_service=false)"),
        ("n", "al", "기준선: traffic.stall (60초 0.3 m 미만 이동 / 대기 180초 초과)", "ev"),
    ])
    d["sd11_map"] = sequence("SD-11 맵 업로드 · 활성화 · SET_MAP 동기화", [P_AD, P_WEB, P_API, ("ms", "MapStore\n(mapkit)", "entity"), ("co", "MapCoordinator\n(coordinator.py)", "control"), P_MQ, P_RB], [
        ("m", "ad", "web", "맵 관리 · 파일 선택(fms_map.json + PNG) · [맵 업로드]"),
        ("m", "web", "api", "POST /sites/{site}/maps (multipart)"),
        ("m", "api", "ms", "ingest.validate → bake(금지구역 굽기) → version=내용 해시 12자"),
        ("f", "alt", "검증 실패", [("m", "api", "web", "422 + 사유", "ret", RED)], [("성공", [
            ("m", "ms", "api", "version · warnings", "ret"),
            ("f", "opt", "활성화 체크", [("m", "api", "ms", "activate(version)")]),
        ])]),
        ("m", "co", "ms", "활성 버전 변경 감지"),
        ("m", "co", "mq", "instant SET_MAP {map_id(uid), map_version, url}"),
        ("m", "mq", "rb", "SET_MAP", "async"),
        ("m", "rb", "api", "GET …/bundle?version= (zip)"),
        ("s", "rb", "번들 캐시 · 맵 교체"),
        ("m", "rb", "mq", "State.map_id·map_version 보고", "async", PURPLE),
        ("n", "co", "배정 맵 uid·활성 버전을 보고해야 작업 배정 (불일치면 10초 쿨다운 후 재발행)", "rb"),
    ])
    d["sd12_zone_edit"] = sequence("SD-12 점유 존 등록 (구역 편집기)", [P_AD, P_WEB, P_API, ("ms", "MapStore", "entity"), P_TR, ("co", "MapCoordinator", "control")], [
        ("m", "ad", "web", "목적지로 대기·출구 node 먼저 등록"),
        ("m", "ad", "web", "＋ → 구역 → 종류 '점유 존' · 사각형 그리기 · 진입 방향 추가"),
        ("s", "web", "zone-geometry.js: 회전 경계·겹침 검사"),
        ("m", "web", "api", "POST …/maps/{map}/zones {type: occupancy, gates[], rotation, base_version}"),
        ("m", "api", "tr", "교통 예약·대기 작업 있는지 확인"),
        ("f", "alt", "예약 있음", [("m", "api", "web", "409 맵 편집 차단", "ret", RED)],
         [("base_version 불일치", [("m", "api", "web", "409 다시 불러오기", "ret", RED)]),
          ("겹침·차체 여유 부족", [("m", "api", "web", "422 사유", "ret", RED)]),
          ("정상", [("m", "api", "ms", "edit_zone → 새 버전(annotations.json) 활성화"),
                    ("m", "co", "co", "SET_MAP 전체 로봇", "sync")])]),
    ])
    d["sd13_robot_reg"] = sequence("SD-13 로봇 등록 · 점검 전환", [P_AD, P_WEB, P_API, ("sr", "SiteRegistry\n(sites.py)", "entity"), ("co", "MapCoordinator", "control"), P_MQ], [
        ("m", "ad", "web", "로봇 ID·배정 맵 입력 [로봇 등록]"),
        ("m", "web", "api", "POST /sites/{site}/robots {robot_id, map_id}"),
        ("m", "api", "sr", "assign(robot, site, map) → site.json"),
        ("m", "api", "co", "sync(robot)"),
        ("m", "co", "mq", "SET_MAP"),
        ("m", "api", "web", "{assignment, set_map_sent}", "ret"),
        ("m", "ad", "web", "[점검 전환] 사유 입력"),
        ("m", "web", "api", "PUT /sites/{site}/robots/{id} {in_service:false, note}"),
        ("s", "sr", "배정 후보에서 제외 (진행 작업은 끝까지)"),
    ])
    d["sd14_ops"] = sequence("SD-14 현장 전체 정지 · 대피", [P_AD, P_WEB, P_API, ("sr", "SiteRegistry", "entity"), P_JC, P_MQ, P_RB], [
        ("m", "ad", "web", "운영 제어 · 사유 · [현장 정지]"),
        ("m", "web", "api", "POST /sites/{site}/pause {map_id?, reason}"),
        ("m", "api", "sr", "ops.paused 저장"),
        ("m", "api", "mq", "등록 로봇 전부 PAUSE"),
        ("s", "jc", "배정 건너뜀, 대기 이유 '현장 정지 중'"),
        ("n", "jc", "나중에 접속한 로봇에도 PAUSE. 교통 예약·승강기 임대는 유지", "rb"),
        ("m", "ad", "web", "[대피 시작] mode=pullover"),
        ("m", "web", "api", "POST /sites/{site}/evacuation {active:true, mode}"),
        ("m", "jc", "mq", "진행 작업 취소 → IDLE 후 가까운 주차 지점으로 시스템 작업"),
        ("m", "ad", "web", "[대피 해제]"),
        ("n", "jc", "취소된 작업은 자동 재게시하지 않는다", "rb"),
    ])
    d["sd15_charge"] = sequence("SD-15 자동 충전 · 대기 복귀", [P_AL, ("bt", "BatteryManager\n(battery.py)", "control"), ("cp", "charger_pool.py", "control"), P_JC, P_MQ, P_RB], [
        ("f", "loop", "1초 tick, 정책 enabled", [
            ("m", "al", "bt", "tick()"),
            ("f", "alt", "charge < low(25%) ∧ 유휴", [
                ("m", "bt", "cp", "빈 충전소 (경로 거리 순, 그룹 일치)"),
                ("m", "bt", "jc", "create_system('charge', DOCK, min_charge=release 60%)"),
                ("m", "jc", "mq", "Order (DOCK)"),
                ("m", "mq", "rb", "도킹 후 CHARGING", "async"),
            ], [("유휴 idle_after(60초) 초과 ∧ 충전·주차 위치 아님", [
                ("m", "bt", "jc", "create_system('staging', PARK)"),
            ])]),
        ]),
        ("n", "bt", "이번 개발(목표): 작업 후 예상 잔량 < min_job_charge 이면 배정 대신 충전 후보", "rb"),
        ("n", "jc", "일반 작업 후보가 staging 중 로봇뿐이면 staging 을 취소하고 배정 (선점)", "rb"),
    ])
    d["sd16_elevator"] = sequence("SD-16 다층 작업 (승강기 임대)", [P_JC, ("rt", "route.py", "control"), ("el", "ElevatorController\n(elevator_ctl.py)", "control"), ("mqe", "elev/v1/{id}", "ext"), P_TR, P_RB], [
        ("m", "jc", "rt", "build_plan(start map, goal map)"),
        ("m", "rt", "jc", "stage 목록: 승강장 이동 → 탑승 → 층 이동 → 하차 → 목적지", "ret"),
        ("m", "jc", "tr", "도착 층 정원 먼저 예약(acquire_floor future)"),
        ("m", "jc", "el", "acquire(lease) — 요청 시각 FIFO"),
        ("m", "el", "mqe", "cmd: call(층)"),
        ("m", "mqe", "el", "state: 도착·문 열림", "async"),
        ("m", "jc", "rb", "STRAIGHT 진입 오더"),
        ("m", "el", "mqe", "cmd: go(목표 층)"),
        ("m", "mqe", "el", "state: 도착·문 열림", "async"),
        ("m", "jc", "rb", "SET_MAP(도착 층) → 후진 하차 STRAIGHT"),
        ("m", "jc", "el", "release(lease) · elevator_leases.json"),
        ("f", "break", "호출 대기 시간 초과 ∧ 탑승 전", [("m", "jc", "rt", "build_plan(avoid={승강기}) 재계획")]),
    ])
    d["sd17_deadlock"] = sequence("SD-17 교착·정체 감지와 안전한 회수", [P_AL, P_TR, ("el", "elevator_ctl", "control"), P_EV, P_WEB], [
        ("f", "loop", "1초 tick", [
            ("m", "al", "tr", "analyze()"),
            ("m", "tr", "el", "임대·대기 정보"),
            ("s", "tr", "wait_graph: A → B (B 가 가진 대기 node·존·층 정원·임대)"),
            ("s", "tr", "find_cycles (DFS)"),
            ("f", "alt", "순환 있음", [
                ("m", "tr", "ev", "traffic.deadlock (같은 순환 1회)"),
                ("m", "tr", "tr", "revoke_safe(): 아직 허가를 내보내지 않은 예약만 (탑승 전 도착 층 예약)", "sync"),
                ("m", "tr", "ev", "traffic.revoke"),
            ], [("60초 0.3 m 미만 이동 / 대기 180초 초과", [("m", "tr", "ev", "traffic.stall")])]),
        ]),
        ("m", "ev", "web", "알림 deadlock · 교통 상태 표에 순환 로봇·자원", "async"),
        ("n", "tr", "발행된 허가(대기 node·존)는 자동으로 풀지 않는다 → 운영자 조치. 이번 개발 목표: 낮은 우선순위 로봇 자동 양보 검증", "web"),
    ])
    d["sd18_runner"] = sequence("SD-18 FMS 연동 실험 러너 운행 (이번 개발)", [("rn", "실험 러너\n(run_experiment.py)", "plan"), ("bk", "브로커", "ext"), P_RB, P_API, P_JC, P_EV, ("fs", "runs/{run_id}/", "entity")], [
        ("m", "rn", "fs", "scenario.yaml · seed · 조건(①~④) · 커밋 해시 → meta.json", "sync", ORANGE),
        ("m", "rn", "api", "PUT …/traffic {route_policy, max_moving_robots}", "sync", ORANGE),
        ("m", "rn", "rb", "robot_client × N 기동 (시작 위치·잔량)", "sync", ORANGE),
        ("m", "rn", "api", "POST /runs {run_id, …} → 이벤트에 run_id 부여", "sync", ORANGE),
        ("f", "loop", "15분, 주문 시각표대로", [
            ("m", "rn", "api", "POST /sites/{site}/jobs (external_id=run_id-n)", "sync", ORANGE),
            ("m", "jc", "rb", "배정 · 오더 (SD-01, SD-02)"),
            ("m", "jc", "ev", "job.* · traffic.* · robot.* (run_id)"),
            ("f", "opt", "이상 주입 시각", [("m", "rn", "rb", "INJECT_FAULT(유형) · 주입 시각 기록", "sync", ORANGE)]),
        ]),
        ("m", "rn", "api", "GET /events?run_id= → events.jsonl", "sync", ORANGE),
        ("m", "rn", "fs", "지표 요약 · CPU 사용률 · 무효 판정", "sync", ORANGE),
        ("m", "rn", "rb", "종료 (SIGTERM → OFFLINE)", "sync", ORANGE),
    ])
    d["sd19_train"] = sequence("SD-19 데이터셋 생성 · 학습 · 평가 · 배포 (이번 개발)", [("ds", "dataset.py", "plan"), ("fs", "runs/·datasets/", "entity"), ("tr2", "train_*.py\n(학과 GPU / 로컬)", "plan"), ("mc", "models/\nmodel_card.json", "entity"), P_AI], [
        ("m", "ds", "fs", "운행 단위 읽기 (events.jsonl · state.jsonl · meta)", "sync", ORANGE),
        ("s", "ds", "배정 순간 스냅샷으로 특징 생성 (미래 정보 차단)", ORANGE),
        ("s", "ds", "seed 단위로 학습/평가 분리", ORANGE),
        ("m", "ds", "fs", "congestion.parquet · battery.parquet · anomaly.parquet", "sync", ORANGE),
        ("m", "tr2", "fs", "학습 세트 읽기", "sync", ORANGE),
        ("s", "tr2", "규칙 → GBM → (데이터 충분 시) LSTM 순서로 학습", ORANGE),
        ("s", "tr2", "평가 seed 로 MAE · 탐지율 · 오경보 계산, 기준선과 비교", ORANGE),
        ("m", "tr2", "mc", "model.joblib + model_card(특징·지표·데이터셋 해시)", "sync", ORANGE),
        ("m", "mc", "ai", "FMS 재시작 또는 POST /ai/reload (API-1006) 로 로드", "sync", ORANGE),
    ])
    d["sd20_adapter"] = sequence("SD-20 ai_adapter 추론과 안전한 대체", [("cl", "호출자\n(traffic/assign/battery)", "control"), P_AI, ("md", "로드된 모델", "plan"), ("rule", "규칙 기준값", "control"), P_EV], [
        ("m", "cl", "ai", "predict_wait / predict_soc_after / anomaly_score", "sync", ORANGE),
        ("f", "alt", "모델 없음 ∨ 비활성", [("m", "ai", "rule", "규칙 값", "sync")],
         [("모델 있음", [
             ("m", "ai", "md", "predict(특징 벡터)", "sync", ORANGE),
             ("f", "break", "예외 ∨ 100ms 초과 ∨ NaN", [
                 ("m", "ai", "rule", "규칙 값으로 대체", "sync"),
                 ("m", "ai", "ev", "ai.fallback(이유) 기록 (분당 1회로 제한)", "sync", ORANGE),
             ]),
         ])]),
        ("m", "ai", "cl", "값 + source(ai|rule)", "ret"),
        ("n", "ai", "AI 장애가 관제 장애가 되지 않는다: 허가·안전 규칙은 ai_adapter 를 호출하지 않는다", "ev"),
    ])
    d["sd21_preset"] = sequence("SD-21 프리셋 편집 · 예약 실행", [P_OP, P_WEB, P_API, ("ps", "presets.py\n(presets.json)", "entity"), ("sc", "Scheduler\n(scheduler.py)", "control"), P_JC], [
        ("m", "op", "web", "프리셋 이름 · 단계(이동/대기/적재/하차/도킹/주차) 추가 · [저장]"),
        ("m", "web", "api", "POST /sites/{site}/presets {name, commands[]}"),
        ("m", "api", "ps", "검증(목적지 존재·params) → 저장"),
        ("m", "op", "web", "예약 실행: 프리셋 · 요일/시각 또는 간격"),
        ("m", "web", "api", "POST /sites/{site}/schedules"),
        ("f", "loop", "1초 tick", [
            ("m", "sc", "sc", "때가 된 예약?", "sync"),
            ("m", "sc", "ps", "last_run 먼저 저장 (재시작 중복 방지)"),
            ("m", "sc", "jc", "publish(preset, priority, robot_group)"),
        ]),
    ])
    d["sd22_traffic_cfg"] = sequence("SD-22 교통 제어 설정 (층 정원 · 경로 정책)", [P_AD, P_WEB, P_API, P_TR, P_ST], [
        ("m", "ad", "web", "현장 설정 · 선택 맵 교통 제어"),
        ("m", "web", "api", "GET …/maps/{map}/traffic"),
        ("m", "api", "tr", "snapshot(): 정원, 예약, 존 상태, 대기 작업, 교착·정체, 장애물"),
        ("m", "api", "web", "표시", "ret"),
        ("m", "ad", "web", "동시 이동 대수 · 경로 교차 정지 · 통로 선택 정책 [적용]"),
        ("m", "web", "api", "PUT …/traffic {max_moving_robots, conflict_pause, route_policy}"),
        ("m", "api", "tr", "set_limit / set_options"),
        ("m", "tr", "st", "traffic.json"),
        ("n", "tr", "route_policy(distance|rule|ai)는 이번 개발에서 추가. 기본 distance", "st"),
    ])
    return d


def ucs():
    d = {}
    d["uc_operator"] = usecase("운영자 유스케이스", [("op", "운영자")], [("rb", "AMR 로봇"), ("bk", "MQTT 브로커")], [
        ("실시간 관제", [("u1", "실시간 맵 보기", "done"), ("u2", "로봇 상세·대기 이유 보기", "done"), ("u3", "존별 대기 보기", "plan")]),
        ("작업 운영", [("u4", "작업 게시(프리셋)", "done"), ("u5", "작업 직접 생성", "done"), ("u6", "작업 취소·재시도", "done"), ("u7", "우선순위 변경", "done"), ("u8", "예약 실행 등록", "done")]),
        ("로봇 조작", [("u9", "일시정지·재개", "done"), ("u10", "오류 해제", "done"), ("u11", "위치 힌트", "done")]),
        ("알림·분석", [("u12", "알림 확인", "done"), ("u13", "KPI 조회", "done"), ("u14", "이력 조회", "done"), ("u15", "점검 후보 확인", "plan"), ("u16", "관제 방식 비교 보기", "plan")]),
    ], [("op", "u1"), ("op", "u2"), ("op", "u3"), ("op", "u4"), ("op", "u5"), ("op", "u6"), ("op", "u7"), ("op", "u8"),
        ("op", "u9"), ("op", "u10"), ("op", "u11"), ("op", "u12"), ("op", "u13"), ("op", "u14"), ("op", "u15"), ("op", "u16"),
        ("bk", "u9"), ("bk", "u10"), ("rb", "u11"), ("rb", "u1")], width=1000, system="FMS — 운영자 기능")
    d["uc_admin"] = usecase("관리자 유스케이스", [("ad", "관리자")], [("rb", "AMR 로봇"), ("ev", "승강기·자동문"), ("ex", "외부 시스템")], [
        ("현장·맵", [("a1", "현장 등록·삭제", "done"), ("a2", "맵 업로드·버전 활성화", "done"), ("a3", "목적지·도킹 등록", "done"), ("a4", "픽업스테이션", "done")]),
        ("교통 규칙", [("a5", "점유 존·자동문 편집", "done"), ("a6", "금지·감속·일방통행", "done"), ("a7", "층 정원 설정", "done"), ("a8", "통로 선택 정책", "plan")]),
        ("로봇·설비", [("a9", "로봇 등록·재배정", "done"), ("a10", "점검 전환·그룹", "done"), ("a11", "승강기 연결·복구", "done")]),
        ("운영 정책", [("a12", "현장 정지·대피", "done"), ("a13", "충전·대기 정책", "done")]),
        ("보안·연동", [("a14", "API 키 관리", "done"), ("a15", "webhook 관리", "done"), ("a16", "MQTT 계정 인증", "plan")]),
    ], [("ad", k) for k in ("a1", "a2", "a3", "a4", "a5", "a6", "a7", "a8", "a9", "a10", "a11", "a12", "a13", "a14", "a15", "a16")]
       + [("rb", "a2"), ("rb", "a9"), ("ev", "a11"), ("ev", "a5"), ("ex", "a15")], width=1000, system="FMS — 관리자 기능")
    d["uc_system"] = usecase("FMS 자동 처리 · AI 유스케이스", [("tm", "타이머(1초)"), ("rn", "실험 러너")], [("rb", "AMR 로봇"), ("gpu", "AI 학습 환경\n(학과 GPU/로컬)")], [
        ("자동 관제", [("s1", "작업 자동 배정", "done"), ("s2", "점유 존 통행 허가", "done"), ("s3", "층 정원 관리", "done"), ("s4", "교착·정체 감지", "done"), ("s5", "막힌 통로 재경로", "done"), ("s6", "자동 충전·대기 복귀", "done")]),
        ("장애 대응", [("s7", "LWT·STALE 감지", "done"), ("s8", "장애 작업 재배정", "plan")]),
        ("AI", [("s9", "혼잡(대기) 예측", "plan"), ("s10", "배터리(작업 후 잔량) 예측", "plan"), ("s11", "이상 탐지", "plan"), ("s12", "규칙 값 대체", "plan")]),
        ("실험·학습", [("s13", "무인 반복 운행", "plan"), ("s14", "운행 단위 데이터셋", "plan"), ("s15", "모델 학습·평가", "plan")]),
    ], [("tm", k) for k in ("s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8")] + [("rn", "s13"), ("rn", "s14"), ("gpu", "s15"),
        ("rb", "s2"), ("rb", "s7"), ("s1", "s9", "<<include>>"), ("s9", "s12", "<<extend>>")], width=1000, system="FMS — 자동 처리·AI")
    return d


def states():
    d = {}
    W = 1000
    d["st_robot"] = boxes("로봇 상태 머신 (State.state · sub_state)", {
        "s": (60, 170, 0, 0, "", INK, "start"),
        "idle": (110, 145, 120, 50, "IDLE", BLUE, "state"),
        "mv": (330, 60, 160, 50, "BUSY / MOVING", BLUE, "state"),
        "wt": (330, 145, 160, 50, "BUSY / WAITING", ORANGE, "state"),
        "ac": (330, 230, 160, 50, "BUSY / ACTING", BLUE, "state"),
        "ch": (600, 60, 140, 50, "CHARGING", GREEN, "state"),
        "er": (600, 160, 140, 50, "ERROR", RED, "state"),
        "em": (600, 260, 140, 50, "EMERGENCY", RED, "state"),
        "note": (780, 60, 200, 250, "paused(+pause_source)\nmode(AUTO/MANUAL)\nlocalization\n은 별도 축\n(4축 상태)\n\nEMERGENCY 는\n다른 상태를 덮어쓴다", SUB, "dash"),
    }, [("s", "idle", ""), ("idle", "mv", "order 수신"), ("mv", "wt", "released=false\n노드 앞"),
        ("wt", "mv", "통행권 확장", BLUE, None, [(470, 128)]), ("mv", "ac", "PICK/DROP 노드", None, None, [(300, 170), (300, 250)]),
        ("ac", "idle", "오더 완료", None, None, [(170, 255)]), ("mv", "ch", "DOCK 액션"), ("ch", "idle", "min_charge 도달", GREEN, None, [(670, 30), (170, 30)]),
        ("wt", "er", "FATAL\n(오더 폐기)", RED), ("er", "idle", "RESET_ERROR", SUB, "dash", [(540, 330), (170, 330)]),
        ("ac", "em", "비상정지", RED)], width=W, height=360)
    d["st_job"] = boxes("작업(Job) 상태 머신", {
        "s": (50, 140, 0, 0, "", INK, "start"),
        "p": (90, 115, 120, 50, "pending", SUB, "state"),
        "a": (280, 115, 120, 50, "assigned", BLUE, "state"),
        "w": (470, 115, 120, 50, "working", BLUE, "state"),
        "ok": (690, 30, 120, 46, "success", GREEN, "state"),
        "f": (690, 115, 120, 46, "failed", RED, "state"),
        "cg": (470, 240, 120, 46, "canceling", ORANGE, "state"),
        "c": (690, 240, 120, 46, "canceled", SUB, "state"),
        "e": (900, 140, 0, 0, "", INK, "end"),
    }, [("s", "p", ""), ("p", "a", "dispatch\n(자동·수동)"), ("a", "w", "로봇 수신 확인"), ("w", "ok", "모든 명령 완료", GREEN),
        ("w", "f", "FATAL / 거절\n/ robot_lost(계획)", RED), ("a", "cg", "취소", ORANGE, None, [(340, 263)]), ("w", "cg", "취소", ORANGE),
        ("cg", "c", "IDLE 확인"), ("p", "c", "취소", SUB, None, [(150, 330), (750, 330)]), ("ok", "e", ""), ("f", "e", ""), ("c", "e", ""),
        ("f", "p", "재시도(새 job, retry_of)", SUB, "dash", [(750, 95), (150, 95)])], width=W, height=360)
    d["st_zone"] = boxes("점유 존 상태 (traffic.snapshot)", {
        "e": (80, 120, 150, 54, "비어 있음", GREEN, "state"),
        "r": (330, 40, 150, 54, "진입 예약", BLUE, "state"),
        "o": (580, 120, 150, 54, "점유 중", BLUE, "state"),
        "u": (330, 220, 150, 54, "확인 필요", RED, "state"),
    }, [("e", "r", "대기 node 정지 확인\n∧ 존·출구 빔"), ("r", "o", "차체가 존에 걸침"), ("o", "e", "출구 통과 ∧ 차체 이탈", GREEN, None, [(655, 300), (155, 300)]),
        ("o", "u", "통신 두절·위치 상실\n·취소", RED), ("u", "e", "존 밖 정지 보고", SUB, "dash"), ("e", "u", "미허가 점유 감지", RED, None, [(240, 230)])],
        width=820, height=330)
    return d


def flows():
    d = {}
    d["flow_service"] = boxes("서비스 절차 — 운영 루프와 학습 루프", {
        "g1": (20, 20, 960, 230, "운영 루프 (실시간)", BLUE, "group"),
        "g2": (20, 270, 960, 200, "학습 루프 (운행 기록 → 모델)", ORANGE, "group"),
        "op": (40, 90, 130, 60, "① 운영자\n운반 요청", INK),
        "web": (210, 90, 140, 60, "웹 관제 화면\n작업 게시판", BLUE),
        "fms": (390, 60, 200, 120, "② FMS\n배정 · 통행 허가\n충전 · 승강기", BLUE),
        "bk": (630, 90, 120, 60, "MQTT\n브로커", SUB),
        "rb": (790, 80, 170, 80, "③ 로봇 ×N\nC++·MuJoCo\nA* 경로계획", PURPLE),
        "log": (40, 330, 170, 70, "④ 운행 기록\nevents.db · State\n이상 주입 기록", GREEN, "db"),
        "ds": (250, 330, 160, 70, "⑤ 데이터셋\n운행 단위 분리", ORANGE),
        "tr": (450, 330, 160, 70, "⑥ 학습·평가\n규칙 대비 비교", ORANGE),
        "ad": (650, 330, 160, 70, "⑦ ai_adapter\n예상 대기·잔량\n이상 점수", ORANGE),
        "use": (840, 330, 130, 70, "⑧ 배차·통로\n선택·점검 후보", ORANGE),
    }, [("op", "web", ""), ("web", "fms", "REST"), ("fms", "bk", "order\ninstant"), ("bk", "rb", ""), ("rb", "bk", "state", PURPLE, None, [(710, 175)]),
        ("fms", "log", "기록", GREEN, None, [(490, 215), (125, 215)]), ("log", "ds", ""), ("ds", "tr", ""), ("tr", "ad", "model_card"), ("ad", "use", ""),
        ("use", "fms", "참고값만\n(허가는 FMS)", ORANGE, "dash", [(905, 260), (560, 260)])], width=1000, height=490,
        legend=[(BLUE, "구현 완료"), (ORANGE, "이번 개발"), (PURPLE, "로봇(시뮬레이터)")])
    d["flow_data"] = boxes("데이터 수집 · 전처리 파이프라인", {
        "r": (20, 40, 150, 70, "실험 러너\nscenario.yaml\nseed·조건", ORANGE),
        "f": (20, 160, 150, 70, "FMS\nevents.db\n(job·traffic·robot)", BLUE, "db"),
        "s": (20, 280, 150, 70, "로봇 State\n200ms\n(MQTT 구독 기록)", PURPLE),
        "raw": (240, 140, 170, 110, "runs/{run_id}/\nmeta.json\nevents.jsonl\nstate.jsonl\nfaults.jsonl", GREEN, "db"),
        "cl": (470, 60, 170, 60, "정제\n워밍업 60초·CPU>90% 제외", ORANGE),
        "fe": (470, 160, 170, 60, "특징 생성\n배정 순간 스냅샷", ORANGE),
        "lb": (470, 260, 170, 60, "라벨 결합\n실제 대기·잔량·주입 시각", ORANGE),
        "sp": (700, 160, 130, 60, "seed 단위\n학습/평가 분리", ORANGE),
        "out": (870, 130, 120, 120, "datasets/\ncongestion\nbattery\nanomaly\n.parquet", GREEN, "db"),
    }, [("r", "raw", "meta·faults"), ("f", "raw", "GET /events?run_id"), ("s", "raw", "구독 기록"), ("raw", "cl", ""), ("cl", "fe", ""), ("fe", "lb", ""),
        ("lb", "sp", "", None, None, [(765, 290)]), ("sp", "out", "")], width=1000, height=380)
    d["flow_model"] = boxes("AI 모델 파이프라인 (학습 → 서비스)", {
        "d": (20, 120, 140, 80, "datasets/\n*.parquet", GREEN, "db"),
        "b": (200, 30, 170, 60, "기준선\n예약 수 규칙 · 임계값\n· traffic.stall", SUB),
        "m1": (200, 120, 170, 60, "모델 v1\nGBM(회귀) / AE", ORANGE),
        "m2": (200, 210, 170, 60, "모델 v2 (선택)\nLSTM 시계열", ORANGE, "dash"),
        "ev": (420, 120, 170, 60, "평가 seed\nMAE · 탐지율 · 오경보", ORANGE),
        "gate": (630, 110, 130, 80, "채택 기준\n통과?", ORANGE, "diamond"),
        "card": (800, 40, 180, 60, "model.joblib\nmodel_card.json", GREEN, "db"),
        "ad": (800, 150, 180, 60, "ai_adapter\n(FMS 프로세스 안)", ORANGE),
        "rule": (800, 250, 180, 50, "규칙 기준값 유지", SUB),
    }, [("d", "b", ""), ("d", "m1", ""), ("d", "m2", ""), ("b", "ev", ""), ("m1", "ev", ""), ("m2", "ev", ""), ("ev", "gate", ""),
        ("gate", "card", "예"), ("card", "ad", "로드"), ("gate", "rule", "아니오", SUB)], width=1000, height=320)
    d["flow_threads"] = boxes("FMS 프로세스 안의 스레드와 락", {
        "paho": (20, 40, 200, 70, "paho 네트워크 스레드\nState·Connection 수신", PURPLE),
        "fleet": (270, 40, 170, 70, "Fleet 리스너\n(블로킹 금지)", BLUE),
        "loop": (20, 160, 200, 70, "asyncio 루프\nREST · WebSocket", BLUE),
        "alloc": (20, 280, 200, 90, "job-allocator 1초\n배정·교통 안전·재경로\n배터리·예약·알림", BLUE),
        "lock": (500, 150, 200, 90, "JobCoordinator.lock\n(RLock)\n→ _EDIT_LOCK\n→ LocationStore._lock", RED),
        "evl": (770, 40, 200, 70, "event-log 스레드\n묶음 commit · 구독자", GREEN),
        "wh": (770, 160, 200, 60, "webhooks 스레드\n재시도 · HMAC 서명", GREEN),
        "el": (770, 270, 200, 60, "elevator-sim / door-sim", SUB),
        "files": (500, 300, 200, 70, "JSON 상태 파일\n(원자적 교체)", GREEN, "db"),
    }, [("paho", "fleet", ""), ("fleet", "lock", "update"), ("loop", "lock", "API 쓰기"), ("alloc", "lock", "tick"),
        ("fleet", "loop", "call_soon_threadsafe", SUB, "dash"), ("lock", "files", "저장"), ("lock", "evl", "record() 큐", GREEN, "dash"),
        ("evl", "wh", "구독"), ("evl", "loop", "EventStream", GREEN, "dash", [(600, 90), (300, 160)])], width=1000, height=390)
    d["flow_deploy"] = boxes("배포 구성 (예정안 · 학과 확인 후 확정)", {
        "g1": (20, 20, 300, 300, "서비스·시연 — 학교 AWS 계정", BLUE, "group"),
        "g2": (350, 20, 300, 300, "AI 학습 — 학과 GPU 서버", ORANGE, "group"),
        "g3": (680, 20, 300, 300, "성능 실험 — 팀원 PC 4대", PURPLE, "group"),
        "a1": (50, 60, 240, 50, "웹 관제 화면 (static)", BLUE), "a2": (50, 125, 240, 50, "FMS 서버 (uvicorn 1 worker)", BLUE),
        "a3": (50, 190, 240, 50, "Mosquitto (계정·ACL·TLS)", BLUE), "a4": (50, 255, 240, 50, "시연용 로봇 몇 대 상시", PURPLE),
        "b1": (380, 60, 240, 60, "datasets/ 반입", GREEN, "db"), "b2": (380, 140, 240, 50, "train_*.py · 평가", ORANGE),
        "b3": (380, 210, 240, 50, "model.joblib · model_card", GREEN), "b4": (380, 270, 240, 40, "대체: 로컬 · Colab", SUB, "dash"),
        "c1": (710, 60, 240, 50, "브로커 + FMS + 로봇 10대", PURPLE), "c2": (710, 125, 240, 50, "실험 러너 (야간 병렬)", ORANGE),
        "c3": (710, 190, 240, 50, "runs/ → 원본 로그 S3", GREEN), "c4": (710, 255, 240, 50, "같은 조건 seed 는 같은 PC", SUB),
    }, [("c3", "b1", "운행 기록"), ("b3", "a2", "모델 파일", ORANGE, None, [(500, 340), (170, 340)])], width=1000, height=360)
    d["flow_comm"] = boxes("서버/클라이언트 통신 구조", {
        "br": (20, 120, 170, 90, "웹 브라우저\nfms_server/static", BLUE),
        "api": (280, 40, 200, 70, "REST /api/v1\n(FastAPI)", BLUE),
        "ws": (280, 140, 200, 60, "WebSocket\n/robots/stream · /events/stream", BLUE),
        "core": (540, 80, 180, 120, "FMS 코어\n배정·교통·충전\n승강기·이벤트", BLUE),
        "mq": (780, 100, 120, 80, "Mosquitto", SUB),
        "rb": (780, 230, 200, 70, "robot_client ×N\nfms/v1/{id}/…", PURPLE),
        "el": (780, 20, 200, 60, "승강기·자동문\nelev/v1 · door/v1", SUB),
        "ext": (280, 250, 200, 60, "외부 시스템\nREST 주문 · webhook", SUB, "dash"),
        "view": (540, 250, 180, 60, "Qt 플릿 뷰어\n(구독 전용)", PURPLE),
    }, [("br", "api", "HTTP JSON"), ("br", "ws", "WS"), ("api", "core", ""), ("ws", "core", "", SUB, "dash"), ("core", "mq", "MQTT"),
        ("mq", "rb", "order · instant ↓ / state · connection ↑"), ("mq", "el", "cmd ↓ state ↑"), ("ext", "api", "REST"),
        ("view", "mq", "sub", PURPLE, "dash"), ("rb", "api", "HTTP 맵 번들", PURPLE, "dash", [(600, 330), (380, 330), (380, 110)])], width=1000, height=350)
    return d


def erds():
    store = {"J": "JSON", "S": "SQLite"}
    ent = {
        "Site (site.json)": (10, 10, 235, [("site_id", "str", "PK"), ("name", "str", ""), ("ops.paused/evacuation", "obj", ""), ("created_at", "iso", "")], BLUE, "JSON"),
        "RobotAssignment": (10, 175, 235, [("robot_id", "str", "PK"), ("site_id", "str", "FK"), ("map_id", "str", "FK"), ("in_service", "bool", ""), ("groups", "str[]", "")], BLUE, "site.json"),
        "MapVersion": (262, 10, 235, [("map_id", "str", "PK"), ("version", "hash12", "PK"), ("map_uid", "sha256[:24]", ""), ("active", "bool", ""), ("annotations", "zones[]", "")], BLUE, "maps/"),
        "Zone": (262, 200, 235, [("zone_id", "str", "PK"), ("type", "occupancy|prohibit|slow|…", ""), ("polygon·rotation", "float", ""), ("gates[]", "wait/exit", ""), ("door", "str?", "")], BLUE, "annotations"),
        "Location": (514, 10, 235, [("name", "str", "PK"), ("map_id", "str", "FK"), ("x, y, theta", "float", ""), ("type", "station|charger|parking|…", "")], BLUE, "locations.json"),
        "Preset": (514, 175, 235, [("preset_id", "str", "PK"), ("name", "str", ""), ("commands[]", "obj", "")], BLUE, "presets.json"),
        "Schedule": (514, 320, 235, [("id", "str", "PK"), ("preset_id", "str", "FK"), ("days/time/interval_s", "", "")], BLUE, "schedules.json"),
        "Job": (766, 10, 225, [("job_id", "str", "PK"), ("site_id", "str", "FK"), ("robot_id", "str", "FK"), ("status", "enum", ""), ("traffic", "obj", ""), ("retry_of", "str", "FK")], BLUE, "jobs.json"),
        "TrafficReservation": (766, 220, 225, [("key(site/map)", "str", "PK"), ("limit", "int?", ""), ("leases[]", "obj", ""), ("zone→job", "map", "")], BLUE, "traffic.json"),
        "events": (10, 370, 235, [("id", "INTEGER", "PK"), ("ts", "REAL", ""), ("site_id", "TEXT", "FK"), ("kind", "TEXT", ""), ("robot_id", "TEXT", "FK"), ("job_id", "TEXT", "FK"), ("run_id (계획)", "TEXT", ""), ("data", "JSON", "")], GREEN, "events.db"),
        "alerts": (262, 400, 235, [("id", "INTEGER", "PK"), ("site_id", "TEXT", "FK"), ("rule · key", "TEXT", ""), ("opened/acked/resolved", "REAL", "")], GREEN, "events.db"),
        "webhook_queue": (514, 470, 235, [("id", "INTEGER", "PK"), ("webhook_id", "TEXT", "FK"), ("event_id", "INTEGER", "FK"), ("attempts · next_at", "", "")], GREEN, "events.db"),
        "Elevator": (766, 420, 225, [("elevator_id", "str", "PK"), ("stops[]", "map/zone", "FK"), ("lease", "obj", "")], BLUE, "elevators"),
    }
    rels = [("Site (site.json)", "RobotAssignment", "1", "N", "등록"), ("Site (site.json)", "MapVersion", "1", "N", ""),
            ("MapVersion", "Zone", "1", "N", ""), ("MapVersion", "Location", "1", "N", ""), ("Preset", "Schedule", "1", "N", ""),
            ("Location", "Preset", "1", "N", "target"), ("Job", "TrafficReservation", "1", "0..N", "예약"),
            ("events", "alerts", "1", "0..1", ""), ("alerts", "webhook_queue", "", "", ""), ("TrafficReservation", "Elevator", "", "", "")]
    rels = [r for r in rels if r[2]]
    return {"erd": erd("논리 ERD — JSON 상태 저장소와 SQLite 이력", ent, rels, width=1000, height=620)}


def schedule():
    days = ["11/24", "25", "26", "27", "30", "12/1", "2", "3", "4", "7", "8", "9", "10", "11", "14", "15", "16", "17", "18"]
    B, O, G, P = BLUE, ORANGE, GREEN, PURPLE
    rows = [
        ("문서·발표", None, 0, 0, None), ("", "제안서 발표 1·2 → 설계서 발표 1·2", 1, 4, SUB), ("", "제안서·설계서 확정", 5, 5, SUB), ("", "완료보고서·발표자료 → 보완", 15, 17, SUB),
        ("FMS 코어 · 배정", None, 0, 0, None), ("", "운행 ID · 대기 기록 존 ID", 0, 5, O), ("", "통로 선택 비용 (거리 → 예약 수 규칙)", 6, 8, O),
        ("", "배정 비용에 예상 대기 항", 8, 10, O), ("", "AI 정책 연결 · 안전한 대체", 9, 11, O), ("", "장애 작업 재배정", 7, 9, O),
        ("실험 · 시뮬레이터", None, 0, 0, None), ("", "FMS 연동 실험 러너", 0, 6, O), ("", "baseline(1·2단계) 로그 야간 수집", 2, 8, O),
        ("", "이상 주입 4종", 6, 10, O), ("", "검증·성능·연동시험 + 장기 구동", 11, 13, P), ("", "본 실험(야간) + 분석", 12, 15, P),
        ("웹 관제 화면", None, 0, 0, None), ("", "존별 대기 · 대기 이유 표시", 5, 8, O), ("", "점검 후보 · 비교 · 시연 화면", 9, 13, O), ("", "API 키 입력 화면 · AI 정책 카드", 9, 11, O),
        ("AI 모듈", None, 0, 0, None), ("", "운행 단위 데이터셋 파이프라인", 2, 7, O), ("", "혼잡 예측 v1 (규칙 → 회귀 트리)", 6, 8, O),
        ("", "재학습 · 시계열 모델 비교", 9, 12, O), ("", "배터리 예측", 8, 11, O), ("", "이상 탐지 (Autoencoder)", 9, 11, O),
        ("배포", None, 0, 0, None), ("", "MQTT 인증 → 배포 환경 확인 → 배포", 9, 14, G),
        ("평가", None, 0, 0, None), ("", "진도표 · 리허설 · 평가발표회", 14, 16, RED),
    ]
    marks = [(6, "v0.3 러너", O), (8, "v0.5 중간점검", O), (11, "v1.0 기능동결", RED), (13, "검증 완료", P), (16, "평가발표회", RED)]
    return {"gantt": gantt("모듈별 개발 일정", days, rows, marks, width=1000)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    allsvg = {}
    from diagrams_algo import algos
    from diagrams_v14 import v14
    from diagrams_v15 import v15
    for f in (seqs, ucs, states, flows, erds, schedule, algos, v14, v15):
        allsvg.update(f())
    for name, svg in allsvg.items():
        (OUT / f"{name}.svg").write_text(svg, encoding="utf-8")
    for name in ("overview", "fms", "simulator", "ai"):
        src = PROPOSAL / f"{name}.svg"
        if src.exists():
            shutil.copy(src, OUT / f"proposal_{name}.svg")
    print("다이어그램", len(allsvg), "개")


if __name__ == "__main__":
    main()
