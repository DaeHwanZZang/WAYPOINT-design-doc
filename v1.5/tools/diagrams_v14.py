"""v1.4 추가 다이어그램 — 실험 맵 synth3, AI 모델 구조, 시험 흐름, 보안 경계.

synth3 는 설계 제안이다(아직 AMR-simulator 에 없다). 좌표 1 m = S px.
"""
from diagrams import BLUE, GREEN, INK, ORANGE, PURPLE, RED, SUB, boxes

S = 22          # px / m
OX, OY = 40, 40  # 그림 여백


def _m(x, y, w, h):
    return OX + x * S, OY + y * S, w * S, h * S


def v14():
    d = {}
    # 1. synth3 맵 (40 × 21 m)
    n = {
        "west": (*_m(0, 0, 8, 21), "서쪽 구역", BLUE, "group"),
        "east": (*_m(32, 0, 8, 21), "동쪽 구역", BLUE, "group"),
        "wall1": (*_m(8, 2, 24, 7.5), "벽", SUB),
        "wall2": (*_m(8, 11.5, 24, 7.5), "벽", SUB),
        "zn": (*_m(8, 0, 24, 2), "      Z2 북쪽 우회 통로 (점유 존, 24 m)", RED, "group"),
        "zm": (*_m(8, 9.5, 24, 2), "      Z1 주 통로 (점유 존, 24 m)", RED, "group"),
        "zs": (*_m(8, 19, 24, 2), "      Z3 남쪽 우회 통로 (점유 존, 24 m)", RED, "group"),
    }
    # 대기 node(통로 축) 와 출구 node(축에서 2 m 비켜남)를 분리한다 — 같은 점을 쓰면 양방향 교착
    pts = {}
    for z, y in (("Z2", 1), ("Z1", 10.5), ("Z3", 20)):
        off = 2 if z != "Z3" else -2
        pts[f"{z}w"] = ((6.6, y), "대기", ORANGE)      # 서쪽 대기 (서→동 진입)
        pts[f"{z}e"] = ((33.4, y), "대기", ORANGE)     # 동쪽 대기 (동→서 진입)
        pts[f"{z}wx"] = ((5.0, y + off), "출구", PURPLE)  # 동→서 출구
        pts[f"{z}ex"] = ((35.0, y + off), "출구", PURPLE)  # 서→동 출구
    for name, ((x, y), lab, col) in pts.items():
        X, Y = OX + x * S, OY + y * S
        n[name] = (X - 18, Y - 10, 36, 20, lab, col, "round")
    for i in range(5):
        n[f"w{i}"] = (OX + 1 * S, OY + (3 + i * 3.6) * S, 62, 22, f"W-0{i + 1}", GREEN)
        n[f"e{i}"] = (OX + 37 * S - 20, OY + (3 + i * 3.6) * S, 62, 22, f"E-0{i + 1}", GREEN)
    e = [("w2", "Z1w", "", INK, "dash"), ("Z1w", "Z1ex", "서→동 주 경로 ≈ 34 m", RED, None, [(OX + 20 * S, OY + 10.5 * S), (OX + 33 * S, OY + 10.5 * S)]), ("Z1ex", "e2", "", INK, "dash"),
         ("w0", "Z2w", "", INK, "dash"), ("Z2w", "Z2ex", "북쪽 우회 ≈ 53 m (1.6배)", ORANGE, "dash", [(OX + 20 * S, OY + 1 * S), (OX + 33 * S, OY + 1 * S)]),
         ("w4", "Z3w", "", INK, "dash"), ("Z3w", "Z3ex", "남쪽 우회 ≈ 53 m", ORANGE, "dash", [(OX + 20 * S, OY + 20 * S), (OX + 33 * S, OY + 20 * S)])]
    d["map_synth3"] = boxes("실험 맵 synth3 (제안) — 40 × 21 m, 1글자 = 1 m, 통로 3개 = 점유 존 3개", n, e,
                            width=OX * 2 + 40 * S, height=OY * 2 + 21 * S + 30,
                            legend=[(RED, "점유 존(한 대씩)"), (ORANGE, "대기 node"), (PURPLE, "출구 node(축에서 2 m 비켜남)"), (GREEN, "작업 지점")])

    # 2. 혼잡 예측 모델 구조 (GBM) + LSTM 선택안
    d["model_congestion"] = boxes("AI-1 혼잡 예측 — 입력 특징 → 회귀 트리(앙상블) → 예상 대기, 선택: LSTM", {
        "f": (20, 40, 230, 250, "입력 (표 3.3, 배정 시점)\nentries_1m · entries_3m\nqueue_len · queue_len_dir\nreserved_ahead · avg_pass_s\noccupied · occ_elapsed_s\neta_to_wait_s · order_density\nmoving_robots · floor_cap\nzone_id · dir (범주)", BLUE),
        "t1": (300, 40, 140, 60, "트리 1", ORANGE), "t2": (300, 115, 140, 60, "트리 2", ORANGE), "t3": (300, 230, 140, 60, "트리 M (≤ 300)", ORANGE),
        "dots": (300, 185, 140, 34, "…", SUB, "dash"),
        "sum": (490, 130, 150, 70, "Σ 학습률 × 트리 출력\n+ 초기값(중앙값)", ORANGE),
        "out": (690, 130, 140, 70, "예상 대기 ŷ (초)\nmax(0, ŷ)", GREEN),
        "ad": (860, 130, 120, 70, "ai_adapter\nsource=ai", ORANGE),
        "l": (300, 330, 340, 90, "선택안 LSTM: 존별 1분 진입 수 15스텝 시퀀스\n→ LSTM(32) → [h ; 현재 특징] → Dense(16) → ŷ\n(W3 에 GBM 과 비교, 이기면 채택)", PURPLE, "dash"),
        "lo": (690, 330, 290, 90, "손실: 절대오차(L1) — 대기 0 이 많은 라벨\n조기 종료: 검증 10%, 20회 개선 없음\n평가: 평가 seed MAE vs 예약 수 규칙", SUB, "dash"),
    }, [("f", "t1", ""), ("f", "t2", ""), ("f", "t3", ""), ("t1", "sum", ""), ("t2", "sum", ""), ("t3", "sum", ""), ("sum", "out", ""), ("out", "ad", ""),
        ("f", "l", "", PURPLE, "dash", [(135, 375)])], width=1000, height=450)

    # 3. 이상 탐지 Autoencoder
    d["model_anomaly"] = boxes("AI-3 이상 탐지 — 정상 창만으로 학습한 Autoencoder, 재구성 오차가 점수·근거", {
        "x": (20, 60, 170, 220, "입력 x (54)\n최근 6창 × 9특징\n(1초 간격, 창 10초)\n표준화(학습 세트 통계)", BLUE),
        "e1": (230, 80, 90, 180, "Dense 32\nReLU", ORANGE),
        "z": (360, 120, 80, 100, "z (8)\n병목", RED),
        "d1": (480, 80, 90, 180, "Dense 32\nReLU", ORANGE),
        "xr": (610, 60, 150, 220, "재구성 x̂ (54)", BLUE),
        "err": (800, 60, 180, 100, "특징별 오차\n(x − x̂)²\n→ 9특징으로 합산", GREEN),
        "sc": (800, 180, 180, 100, "점수 = 평균 오차 / 임계\n임계 = 정상 검증 99.5 분위\n3창 연속 초과 → 경보", GREEN),
        "why": (610, 310, 370, 70, "근거 = 오차 상위 3개 특징 → 표 5.2 문구\n예: released_ahead·disp_m → \"허가 노드 3개 남음 · 위치 변화 0.02 m\"", ORANGE, "dash"),
        "tr": (20, 310, 560, 70, "학습: 정상 창만(seed 101~, 이상 주입 없는 운행), MSE, Adam 1e-3, 배치 256, 30 epoch\n평가: 주입 운행 seed 206~210 의 모든 창 → ROC·PR·사건 단위 탐지율·지연", SUB, "dash"),
    }, [("x", "e1", ""), ("e1", "z", ""), ("z", "d1", ""), ("d1", "xr", ""), ("xr", "err", ""), ("x", "err", "", SUB, "dash", [(105, 30), (890, 30)]),
        ("err", "sc", ""), ("err", "why", "", ORANGE, "dash", [(890, 295)])], width=1000, height=400)

    # 4. 시험 단계 흐름 (V 모델)
    d["test_v"] = boxes("시험 단계 — 설계 산출물과 시험의 짝 (V 모델)", {
        "r": (20, 30, 230, 56, "요구사항 (2장)\nFR · NFR · AR · S1~S12", BLUE),
        "a": (90, 120, 230, 56, "기능·프로세스 설계 (6장)\nSD · 6.6 알고리즘", BLUE),
        "i": (160, 210, 230, 56, "인터페이스 설계 (7장)\nMQTT · REST · FN", BLUE),
        "u": (230, 300, 230, 56, "코드 (모듈)", SUB),
        "ut": (540, 300, 230, 56, "단위 시험 TC-U\npytest · C++ unit · node", GREEN),
        "it": (610, 210, 230, 56, "통합·계약 시험 TC-I\ncommon 동기화 · physics_test", GREEN),
        "st": (680, 120, 230, 56, "시스템 시험 TC-S · TC-N · TC-R\n시나리오 · 성능 · 장애", GREEN),
        "at": (750, 30, 230, 56, "인수 시험 (완료 기준 표 1.5)\n72회 실험 · 12/16 시연", GREEN),
    }, [("r", "a", ""), ("a", "i", ""), ("i", "u", ""), ("u", "ut", "구현"), ("ut", "it", ""), ("it", "st", ""), ("st", "at", ""),
        ("r", "at", "검증", ORANGE, "dash"), ("a", "st", "", ORANGE, "dash"), ("i", "it", "", ORANGE, "dash")], width=1000, height=380)

    # 5. 보안 경계
    d["sec_zones"] = boxes("보안 경계와 통제 (배포 전 필수 항목)", {
        "ext": (20, 40, 210, 300, "외부 (인터넷·학교망)", RED, "group"),
        "u": (40, 80, 170, 50, "운영자 브라우저", INK), "x": (40, 160, 170, 50, "외부 시스템 (WMS)", INK), "atk": (40, 250, 170, 60, "공격자\n(익명 접속 시도)", RED, "dash"),
        "dmz": (280, 40, 300, 300, "서버 (학교 AWS 예정)", BLUE, "group"),
        "fms": (300, 80, 260, 60, "FMS :8000\nAPI 키 (Bearer) · 역할 3종", BLUE),
        "mq": (300, 170, 260, 60, "Mosquitto :8883(TLS)\n계정 · 토픽 ACL", BLUE),
        "fs": (300, 260, 260, 60, "FMS_DATA_ROOT\nauth.json 해시 · 백업", GREEN, "db"),
        "lan": (630, 40, 350, 300, "로봇 망 (시연 PC / 현장 LAN)", PURPLE, "group"),
        "rb": (660, 90, 290, 60, "robot_client ×N\nMQTT 계정 (로봇별) · 맵 번들 토큰", PURPLE),
        "vw": (660, 180, 290, 50, "Qt 뷰어 (구독 전용 계정)", PURPLE),
        "ssh": (660, 260, 290, 50, "관리자 SSH (키 인증만)", SUB),
    }, [("u", "fms", "HTTPS + API 키"), ("x", "fms", "REST + 멱등 키 /\nwebhook HMAC"), ("atk", "mq", "익명 거절", RED, "dash"),
        ("fms", "mq", "fms 계정"), ("rb", "mq", "fms/v1/{자기 id}/# 만", PURPLE), ("vw", "mq", "읽기 전용", PURPLE, "dash"), ("rb", "fms", "번들 ?token=", PURPLE, "dash", [(620, 120)]),
        ("fms", "fs", ""), ("ssh", "fs", "", SUB, "dash", [(600, 285)])], width=1000, height=360)
    return d
