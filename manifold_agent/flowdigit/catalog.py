"""채널 단면(Velocity Magnitude) 사진 목록 — 이제 data/section_catalog.csv 에서 읽는다.
새 사진은 `python ml/intake.py section ...` 으로 추가하면 CSV에 들어간다.
(사진 번호 = images/<번호>.png, 유속 = 입구 유속 m/s, vmax = 속도 색상바 최댓값 m/s, 사진에서 직접 읽음)
유량분배는 열과 무관 → 같은 형상·유속이면 핫스팟이 달라도 같은 유동장(반복 측정)."""
import csv, os
HERE = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(HERE, "..", "images")
CATALOG = os.path.join(HERE, "..", "data", "section_catalog.csv")

ROWS = list(csv.DictReader(open(CATALOG, encoding="utf-8")))
# 예전 형식 호환: (사진번호, 형상, 입구유속, 핫스팟), VMAX[형상][유속]
SECTIONS = [(int(r["img"]), r["design"], float(r["inlet_v_mps"]), r["hotspot"]) for r in ROWS]
VMAX = {}
for r in ROWS:
    VMAX.setdefault(r["design"], {})[float(r["inlet_v_mps"])] = float(r["vmax_colorbar"])
CUT_Y = {int(r["img"]): float(r["cut_y_mm"]) for r in ROWS}
