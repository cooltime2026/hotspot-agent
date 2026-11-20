"""새 SimScale 캡처를 데이터로 넣는 도구 (사진 → CSV).

사용법 (manifold_agent 폴더에서):

1) 사진 등록 (번호 자동, 같은 파일 중복 검사)
   python ml/intake.py image 받은사진1.png 받은사진2.png
   → images/208.png, images/209.png ... 로 복사, 같은 파일을 또 보내면 알려줌

2) Run 추가 (바닥 최고온도·압력, 색상바에서 읽은 숫자)
   python ml/intake.py run --design M0 --hotspot 1_1,1_2 --tmax 150.2 --pmax 900 --pmin -50 [--v 0.497] --img 208,209
   - --v 를 빼면 같은 형상의 기존 Run 압력 최대와 비교해 유속을 자동 판별 (압력은 핫스팟과 무관)
   - 같은 형상·유속인데 압력이 기존과 2% 이상 다르면 경고 (유속을 잘못 본 경우 잡기)
   - 같은 형상·핫스팟·유속이 이미 있으면 거부 (--replace 로 덮어쓰기)

3) 채널 단면(Velocity Magnitude) 사진 추가 → 바로 22채널 유속 읽기
   python ml/intake.py section --img 210 --design M0 --v 0.497 --vmax 0.7234 [--cut-y 6.0] [--hotspot 1_1+1_2]
   - 질량 점검(Σ채널유량/Q) 출력, flowdigit/debug/210.png 에 읽은 위치 표시

4) 점검
   python ml/intake.py check      # 전체 데이터 일관성(압력-유속, 중복, 사진 중복)
"""
from __future__ import annotations
import argparse, csv, shutil, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, DATA, IMAGES, INLET_V, flow_from_v, parse_cells, md5   # noqa: E402

RUNS = DATA / "direct_runs.csv"
SECTIONS = DATA / "section_catalog.csv"
RUN_FIELDS = ["design", "inlet_velocity_m_s", "total_flow_mL_min", "model", "heat", "Tmax_bottom_C",
              "p_max_Pa", "p_min_Pa", "inlet", "note"]


def read_csv(p):
    return list(csv.DictReader(open(p, encoding="utf-8"))) if Path(p).exists() else []


def write_csv(p, rows, fields):
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore"); w.writeheader(); w.writerows(rows)


# ---------- 1) 사진 등록 ----------
def cmd_image(a):
    known = {md5(p): p.stem for p in IMAGES.glob("*.png")}
    nums = [int(p.stem) for p in IMAGES.glob("*.png") if p.stem.isdigit()]
    nxt = max(nums, default=0) + 1
    for src in a.files:
        h = md5(src)
        if h in known:
            print(f"  {src}: 이미 있는 사진과 똑같음 → images/{known[h]}.png (등록 안 함)")
            continue
        dst = IMAGES / f"{nxt}.png"
        if Path(src).suffix.lower() == ".png":
            shutil.copy(src, dst)
        else:
            from PIL import Image
            Image.open(src).convert("RGB").save(dst)
        known[h] = str(nxt)
        print(f"  {src} → images/{nxt}.png"); nxt += 1


# ---------- 2) Run 추가 ----------
def pressure_table(rows, design):
    """형상별 유속 → 압력 최대 평균 (기존 Run에서)"""
    t = {}
    for r in rows:
        if r["design"] == design:
            t.setdefault(float(r["inlet_velocity_m_s"]), []).append(float(r["p_max_Pa"]))
    return {v: float(np.mean(p)) for v, p in t.items()}


def guess_v(rows, design, pmax):
    t = pressure_table(rows, design)
    if not t:
        return None, "이 형상의 기존 Run이 없어 압력으로 유속 판별 불가"
    v, p = min(t.items(), key=lambda kv: abs(kv[1] - pmax))
    err = abs(p - pmax) / p
    if err > 0.02:
        return None, f"압력 {pmax} Pa 가 기존 어느 유속({ {k: round(x) for k, x in t.items()} })과도 2% 이상 다름"
    return v, f"압력 {pmax} Pa ≈ 기존 {p:.0f} Pa → 유속 {v} m/s"


def cmd_run(a):
    rows = read_csv(RUNS)
    cells = parse_cells(a.hotspot)
    if a.v is None:
        v, msg = guess_v(rows, a.design, a.pmax); print(" ", msg)
        if v is None:
            sys.exit("  → --v 로 유속을 직접 적어 주세요.")
    else:
        v = a.v
        if v not in INLET_V:
            print(f"  경고: 유속 {v} 는 5단계 {INLET_V} 에 없음")
        t = pressure_table(rows, a.design)
        if v in t and abs(t[v] - a.pmax) / t[v] > 0.02:
            print(f"  경고: 같은 형상·유속의 기존 압력 최대 {t[v]:.0f} Pa 와 {a.pmax} Pa 가 2% 이상 다름 → 유속 다시 확인!")
    heat = "50 W/cm2 + 300 W/cm2 at " + ",".join(cells)
    dup = [i for i, r in enumerate(rows) if r["design"] == a.design and float(r["inlet_velocity_m_s"]) == v
           and parse_cells(r["heat"]) == cells]
    new = dict(design=a.design, inlet_velocity_m_s=v, total_flow_mL_min=round(flow_from_v(v)),
               model="laminar", heat=heat, Tmax_bottom_C=a.tmax, p_max_Pa=a.pmax,
               p_min_Pa=a.pmin if a.pmin is not None else "", inlet=a.inlet or "",
               note=(a.note or "read from Post-processor colorbar") + (f"; img {a.img}" if a.img else ""))
    if dup and not a.replace:
        sys.exit(f"  같은 Run이 이미 있음: {rows[dup[0]]}  (덮어쓰려면 --replace)")
    if dup:
        rows[dup[0]] = new; print("  덮어씀")
    else:
        rows.append(new)
    write_csv(RUNS, rows, RUN_FIELDS)
    print(f"  추가: {a.design} {'+'.join(cells)} v={v} Tmax={a.tmax} pmax={a.pmax}  (총 {len(rows)} Run)")


# ---------- 3) 단면 사진 ----------
def cmd_section(a):
    sys.path.insert(0, str(ROOT / "flowdigit"))
    rows = read_csv(SECTIONS)
    if any(int(r["img"]) == a.img for r in rows) and not a.replace:
        sys.exit(f"  사진 {a.img} 은 이미 목록에 있음 (--replace)")
    rows = [r for r in rows if int(r["img"]) != a.img]
    new = dict(img=a.img, design=a.design, inlet_v_mps=a.v, vmax_colorbar=a.vmax, cut_y_mm=a.cut_y,
               hotspot=a.hotspot or "", note=a.note or "")
    import run_all
    rr, s = run_all.run_one(new)
    print(" ", s)
    sh = np.array([r["q_frac"] for r in rr])
    print("  채널 유량 / 균일값:", " ".join(f"{x:.2f}" for x in sh))
    print(f"  Σ채널유량/Q = {s['mass']}  (단면이 모든 유량을 지나는 위치면 1에 가까워야 함)")
    if s["detected"] < 18:
        print(f"  경고: 채널 {s['detected']}개만 자동 검출 → flowdigit/debug/{a.img}.png 확인 필요")
    rows.append(new)
    write_csv(SECTIONS, rows, list(new))
    print("  목록에 추가. 전체 표 갱신은: python flowdigit/run_all.py")


# ---------- 4) 점검 ----------
def cmd_check(a):
    rows = read_csv(RUNS); ok = True
    for d in sorted({r["design"] for r in rows}):
        sub = [r for r in rows if r["design"] == d]
        for v in sorted({float(r["inlet_velocity_m_s"]) for r in sub}):
            p = np.array([float(r["p_max_Pa"]) for r in sub if float(r["inlet_velocity_m_s"]) == v])
            spread = (p.max() - p.min()) / p.mean()
            flag = "" if spread < 0.02 else "  ← 2% 넘게 다름!"
            ok &= not flag
            print(f"  {d} v={v}: Run {len(p)}개, 압력 최대 {p.mean():.0f} Pa (차이 {spread*100:.1f}%){flag}")
    keys = [(r["design"], r["inlet_velocity_m_s"], tuple(parse_cells(r["heat"]))) for r in rows]
    for k in {k for k in keys if keys.count(k) > 1}:
        ok = False; print("  중복 Run:", k)
    hs = {}
    for p in IMAGES.glob("*.png"):
        hs.setdefault(md5(p), []).append(p.name)
    for v in hs.values():
        if len(v) > 1:
            ok = False; print("  같은 사진 중복:", v)
    print("  이상 없음" if ok else "  ↑ 확인 필요")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("image"); p.add_argument("files", nargs="+"); p.set_defaults(f=cmd_image)
    p = sp.add_parser("run")
    p.add_argument("--design", required=True); p.add_argument("--hotspot", required=True)
    p.add_argument("--tmax", type=float, required=True); p.add_argument("--pmax", type=float, required=True)
    p.add_argument("--pmin", type=float); p.add_argument("--v", type=float)
    p.add_argument("--inlet"); p.add_argument("--note"); p.add_argument("--img")
    p.add_argument("--replace", action="store_true"); p.set_defaults(f=cmd_run)
    p = sp.add_parser("section")
    p.add_argument("--img", type=int, required=True); p.add_argument("--design", required=True)
    p.add_argument("--v", type=float, required=True); p.add_argument("--vmax", type=float, required=True)
    p.add_argument("--cut-y", type=float, default=6.0); p.add_argument("--hotspot"); p.add_argument("--note")
    p.add_argument("--replace", action="store_true"); p.set_defaults(f=cmd_section)
    p = sp.add_parser("check"); p.set_defaults(f=cmd_check)
    a = ap.parse_args(); a.f(a)


if __name__ == "__main__":
    main()
