"""아무 핫스팟 배치(여러 곳 · 크기 · 열유속) → 머신러닝 새 설계 → STEP · 설정 그림 · 유량 · 페이지 1위  (2026-11-28)

  python ml/design_any.py --hs "3,6,2,2,500; 9,6,2,2,150"            # 핫스팟마다 '중심x,중심y,가로,세로,열유속' (mm, W/cm²), ';' 로 구분
  python ml/design_any.py --hs "6,6,5,5,200" --name N30 --q 70       # 이름·설계 유량(mL/min) 지정

하는 일 (전부 자동):
  1. html_v17/evolve_deep.js — 페이지의 모양 규칙(핫스팟 위치·크기·발열량으로 배치)·제작 검사·머신러닝 점수(칸마다 발열 몫)·정식 유량 계산으로 새 모양을 진화
  2. ml/build_new.py — <이름>.step (바닥면 = 핫스팟마다 한 면 + 나머지), <이름>_front_back.png (앞면 입구·출구 / 뒷면 핫스팟 좌표·열유속), <이름>_3d.png
  3. ml/new_summary.py · new_overview.py — 표(예상 온도 · 유량), 한눈 그림
  4. html_v17/patch_ml.py — 페이지에서 같은 핫스팟을 놓으면 1위 = 이 설계 (그 뒤 아티팩트 publish 는 Claude 가)
바탕 조건: 기본 열유속 50 W/cm², 입구 20 ℃ (SimScale 설정과 같음). 핫스팟끼리 겹치면 안 됨.
주의: 학습 데이터는 '칸에 맞는 붙은 두 칸 300 W/cm²' 뿐 → 다른 배치의 예상 온도는 확인 안 됨.
"""
import argparse, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out" / "new_designs"


def sh(*a, env=None):
    import os
    r = subprocess.run(list(a), cwd=ROOT, capture_output=True, text=True, env={**os.environ, **(env or {})})
    if r.returncode:
        print(r.stdout[-3000:], r.stderr[-3000:]); raise SystemExit(f"실패: {' '.join(a)}")
    return r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hs", required=True, help="'x,y,lx,ly,q; x,y,lx,ly,q' (중심·크기 mm, 열유속 W/cm²)")
    ap.add_argument("--name"); ap.add_argument("--q", type=float, default=55.0); ap.add_argument("--iters", type=int, default=700)
    ap.add_argument("--target", type=float, default=85.0)
    ap.add_argument("--max-dead", type=int, help="물이 안 흐르는 채널을 이 수 이하로 (22개 중). 예: 0 = 모든 채널에 물이 흐르는 모양만")
    a = ap.parse_args()
    hs = []
    for t in a.hs.split(";"):
        if t.strip():
            v = [float(x) for x in t.split(",")]
            if len(v) != 5: raise SystemExit(f"핫스팟은 'x,y,가로,세로,열유속' 5개 숫자: {t!r}")
            x, y, lx, ly, q = v
            if not (0 <= x - lx / 2 and x + lx / 2 <= 12 and 0 <= y - ly / 2 and y + ly / 2 <= 12): raise SystemExit(f"핫스팟이 판(0~12 mm) 밖으로 나감: {t!r}")
            hs.append(v)
    if not hs: raise SystemExit("핫스팟이 없음")
    nums = [int(re.match(r"N(\d+)_mask", f.name).group(1)) for f in OUT.glob("N*_mask.json")]
    name = a.name or f"N{max(nums, default=0) + 1}"
    spec = name + "=" + ";".join(",".join(f"{x:g}" for x in v) for v in hs)
    print(f"[1/4] {name}: 핫스팟 {len(hs)}곳, 유량 {a.q:g} mL/min — 모양 찾는 중 (1~2분)")
    print("   ", sh("node", "html_v17/evolve_deep.js", "out/new_designs/deep_free.json", spec, env=dict(ITERS=str(a.iters), QML=str(a.q), **({"DEADMAX": str(a.max_dead)} if a.max_dead is not None else {}))).strip().splitlines()[-1])
    r = json.loads((OUT / "deep_free.json").read_text())[name]
    if not r.get("best"): raise SystemExit("새 설계를 찾지 못함 (제작 검사·유량 계산을 통과한 모양이 없음)")
    print("[2/4] STEP · 그림")
    out = sh(sys.executable, "ml/build_new.py", f"{name}:{name}")
    info = json.loads((OUT / f"{name}.json").read_text())
    ok = info["fluid_solids"] == 1 and info["overlap_mm3"] == 0 and all(f["found"] for f in info.get("hotspot_faces", []))
    print(f"    유체 {info['fluid_solids']}덩어리, 겹침 {info['overlap_mm3']}, 바닥면 {info['bottom_faces']}개, 핫스팟 면 {sum(f['found'] for f in info.get('hotspot_faces', []))}/{len(hs)} 찾음 → {'통과' if ok else '확인 필요'}")
    print("[3/4] 표 · 한눈 그림"); sh(sys.executable, "ml/new_summary.py", str(a.target)); sh(sys.executable, "ml/new_overview.py")
    print("[4/4] 페이지"); sh(sys.executable, "html_v17/patch_ml.py")
    row = [l for l in (OUT / "summary.md").read_text(encoding="utf-8").splitlines() if l.startswith(f"| {name} ")]
    print("\n".join(row))
    nd = r["best"].get("nDead")
    print(f"    물이 안 흐르는 채널 {nd}/22" + ("  ← 많음: 모델이 이런 칸의 온도를 낮게 보는 약점이 있음(--max-dead 0 으로 비교 설계 가능)" if nd and nd > 4 else ""))
    print(f"끝: out/new_designs/{name}.step, {name}_front_back.png, {name}_3d.png  (입구 {info['inlets']}, 출구 {info['outlets']})")


if __name__ == "__main__":
    main()
