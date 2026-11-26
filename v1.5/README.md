# 설계서 v1.5 소스

제안서 v1.5 기준 설계서. v1.1(전면 개정)을 검수·보강한 판이다.

결과물 (이 폴더):
- `(3팀)설계서_v1.5(김대환,김민준,최민석,박시현,안태현).pdf` — 설계서
- `(3팀)설계서_v1.5_발표주석.pdf` — 설계서 쪽마다 왼쪽에 그 쪽, 오른쪽에 발표 요점·부연 설명·예상 질문
- `발표주석_v1.5.md` — 같은 주석의 텍스트판

## 빌드 (이 폴더에서)

```bash
../../AMR-fms/.venv/bin/python build.py              # 다이어그램·API 표 → 2회 인쇄(목차 쪽번호) → 발표 주석
../../AMR-fms/.venv/bin/python build.py --no-notes   # 주석 생략
../../AMR-fms/.venv/bin/python build.py --fast       # 1회 인쇄 (목차 쪽번호 000)
../../AMR-fms/.venv/bin/python build.py --html       # HTML 만 (브라우저 미리 보기)
python3 tools/check.py                               # 표·그림 번호, ID 참조, 캡션 누락 검사
```

버전 번호·날짜는 `build.py` 맨 위 `VERSION`, `DATE` 한 곳에서 바꾼다(`__VER__`, `__DATE__` 치환).

## 구성

| 경로 | 내용 |
|---|---|
| `src/NN_*.html` | 장별 본문(번호 순서로 합침). `<!--#include gen/…-->` 로 생성 표를 넣고, `<!--#toc-->`·`<!--#lof-->`·`<!--#lot-->` 자리에 목차가 들어간다 |
| `src/style.css` | A4 인쇄 스타일, 머리글·쪽번호 |
| `notes/NN_*.md` | 발표 주석. `## 앵커 \| 제목` 아래에 본문. 앵커 = 제목 번호(`6.2`), 캡션(`표 6.2`·`그림 6.6`), ID(`SC-01`·`SD-02`·`API-401`), 제목 글자, 또는 본문 속 `<!--@이름-->`. `+앵커` 는 그 다음 쪽 |
| `tools/notes.css` | 발표 주석 PDF 스타일 (A4 가로) |
| `tools/check.py` | 문서 일관성 검사 |
| `tools/make_diagrams.py` · `diagrams.py` | 시퀀스·유스케이스·상태도·구성도·ERD·간트 SVG (`assets/diagrams/`) |
| `tools/gen_api.py` | `gen/openapi.json` → 7.2 API 정의표·7.3 상세 |
| `tools/gen_mqtt.py` | AMR-fms `common/schemas.py` → 7.1 MQTT 메시지 표. **AMR-fms 루트에서** 실행 |
| `tools/shoot.py` | FMS 웹 화면 캡처 (Chrome DevTools) |
| `build/` | 중간 산출물(1차 PDF, 앵커 쪽번호 `entries.tsv`, 주석용 축소 이미지) — 지워도 된다 |

## 쪽번호를 찾는 방법

1차 인쇄 때 제목·캡션 끝에 보이지 않는 표식(`QQM{n}QQ`, 2px 흰 글씨, 폭 0)을 넣고 `pdftotext` 로 어느 쪽에 찍혔는지 찾는다. 2차 인쇄는 표식을 빼고 쪽번호를 채운다. 두 인쇄의 쪽수가 다르면 경고를 찍는다. 표식은 flex 컨테이너 바로 아래(예: 표지 `section.cover` 직속)에 두면 레이아웃이 바뀌므로 문단 안에 둔다.

## 코드가 바뀌면 다시 뽑을 것

```bash
# AMR-fms 루트에서
FMS_DATA_ROOT=$(mktemp -d) FMS_MQTT_PORT=18859 .venv/bin/python -c \
  "import json;from fms_server.main import app;json.dump(app.openapi(),open('../설계서/v1.5/gen/openapi.json','w'),ensure_ascii=False,indent=1)"
.venv/bin/python ../설계서/v1.5/tools/gen_mqtt.py
```

화면 캡처는 **격리된 브로커 포트**(예: 18870)와 별도 데이터 폴더로 FMS·로봇을 띄운 뒤 찍는다.
기본 포트 1883 에 이미 떠 있는 브로커·로봇이 있으면 캡처용 FMS 가 거기에 SET_MAP 을 보낸다.
