"""머신러닝 새 설계(진화) → 마스크 json · STEP · 설정 그림 (2026-11-28).

  node html_v17/evolve_deep.js out/new_designs/deep_0.json 1_3+1_4 2_2+3_2 ...  # 페이지 규칙·모델로 핫스팟마다 새 설계 찾기
  python ml/build_new.py N1:1_3+1_4 N2:2_2+3_2 ...                            # 이름:핫스팟 → STEP

만드는 것 (out/new_designs/):
  <이름>_mask.json  페이지 g 그대로 (cav·gro 240×240, 1 = 입구망, pin·pout, head: 1 = 헤더형(채널 1.5~10.5 + 헤더, 층 0.15/0.4),
                    0 = v17 형(채널 0.6~11.4, 층 0.5/0.35))
  <이름>.step        압축 안 한 STEP (fluid·solid, 바닥 16칸 분할)  — 저장소에는 <이름>_step.zip
  <이름>_3d.png, <이름>.json (부피·검사)
  <이름>_front_back.png  설정 그림: 왼쪽 앞면(입구·출구 좌표) / 오른쪽 뒷면(핫스팟 칸)
"""
import json, sys, zipfile
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "out" / "new_designs"


def unrle(a, n=240 * 240):
    o = np.zeros(n, np.uint8); k = 0
    for v, c in zip(a[0::2], a[1::2]):
        o[k:k + c] = v; k += c
    return o


def load_deep():
    """html_v17/evolve_deep.js 결과(out/new_designs/deep_*.json) 합치기"""
    D = {}
    for f in sorted(OUT.glob("deep_*.json")):
        D.update(json.loads(f.read_text()))
    return D


def mask_of(name, hs, D=None):
    r = (D or load_deep())[hs]
    e = r["best"]
    if not e:
        raise SystemExit(f"{hs}: 새 설계 없음")
    g = e["g"]
    lib = [x for x in r["lib"] if not x.get("out")]
    extra = {}
    if r.get("hs"):      # 아무 배치: hs = [{x,y,lx,ly,q}], hotspot = 발열 큰 두 칸(이름표), Q = 설계 유량
        extra = dict(hs=r["hs"], label=hs, Q=r.get("Q", 55)); hs = "+".join(r["cells"])
    extra["n_dead"] = e.get("nDead")      # 물이 안 흐르는 채널 수 (22개 중)
    return dict(**extra, name=name, hotspot=hs, base=f"머신러닝 새 설계 ({e['fam']}에서 진화 · 슬롯 +{e['cnt']['add']} · 홈 +{e['cnt']['gro']})",
                fam=e["fam"], seed=e["from"], head=int(e["head"]), cnt=e["cnt"], iou=e["iou"], mlT=e["T"], seedT=e["T0"],
                lib_best=lib[0] if lib else None, pin=[[round(x, 3) for x in q] for q in g["pin"]], pout=[[round(x, 3) for x in q] for q in g["pout"]], cav=unrle(g["cav"]).tolist(), gro=unrle(g["gro"]).tolist())


def build_step(m):
    from geometry import build_html as BH
    import cadquery as cq
    BH.NGRID, BH.RES = 240, 0.05
    name = m["name"]
    if m["head"]:
        D = {name: dict(head=1, ports=m["pin"] + m["pout"], P=m["cav"], U=m["gro"], layers=[dict(h=0.15), dict(h=0.4)])}
    else:
        D = {name: dict(head=0, ext=[0.6, 11.4], ports=m["pin"] + m["pout"], P=m["cav"], U=m["gro"], layers=[dict(h=0.5), dict(h=0.35)])}
    fluid, solid, ztop, g = BH.build(name, D)
    hot_faces = None
    if m.get("hs"):      # 아무 배치: 바닥면을 '핫스팟마다 한 면 + 나머지'로 나눔 (16칸 대신) → SimScale 에서 핫스팟 면을 바로 고름
        solid, hot_faces = free_bottom(BH, cq, fluid, ztop, m["hs"])
    asm = cq.Assembly(name=f"manifold_{name}")
    asm.add(cq.Workplane().add(fluid), name="fluid", color=cq.Color(0.2, 0.5, 1.0, 1))
    asm.add(cq.Workplane().add(solid), name="solid", color=cq.Color(0.75, 0.75, 0.78, 1))
    stp = OUT / f"{name}.step"
    asm.save(str(stp), exportType="STEP")
    with zipfile.ZipFile(OUT / f"{name}_step.zip", "w", zipfile.ZIP_DEFLATED) as z:
        z.write(stp, stp.name)
    BH.preview(name, fluid, dict(ports=m["pin"] + m["pout"]), OUT / f"{name}_3d.png")
    info = dict(name=name, hotspot=m["hotspot"], design=m["base"], head=m["head"], inlets=m["pin"], outlets=m["pout"], height_mm=round(ztop, 3),
                fluid_solids=len(fluid.Solids()), fluid_mm3=round(fluid.Volume(), 3), solid_mm3=round(solid.Volume(), 3),
                overlap_mm3=round(fluid.intersect(solid).Volume(), 6), bottom_faces=len(BH.bottom_cells(solid)),
                dead_fluid_filled_mm3=g["dropped_mm3"], ml_pred_C=round(m["mlT"], 1))
    if hot_faces is not None:
        info["hotspot_faces"] = hot_faces; info["hs"] = m["hs"]
    (OUT / f"{name}.json").write_text(json.dumps(info, ensure_ascii=False, indent=1))
    return info


def hs_rects(hs):
    """핫스팟 → 판 안으로 자른 사각형 (x0, y0, x1, y1, q)"""
    return [(max(0, h["x"] - h["lx"] / 2), max(0, h["y"] - h["ly"] / 2), min(12, h["x"] + h["lx"] / 2), min(12, h["y"] + h["ly"] / 2), h["q"]) for h in hs]


def free_bottom(BH, cq, fluid, ztop, hs):
    """고체 = (판 − 핫스팟 기둥) + 핫스팟 기둥 (합치되 경계선 유지) − 유체. 바닥(z=0) 면: 핫스팟마다 1개 + 나머지.
    겹치는 핫스팟은 지원 안 함(겹치면 멈춤). 반환: 고체, 바닥면 목록 [{hotspot, x0,y0,x1,y1, area_mm2, found}]"""
    R = hs_rects(hs)
    for i in range(len(R)):
        for j in range(i + 1, len(R)):
            if min(R[i][2], R[j][2]) - max(R[i][0], R[j][0]) > 1e-9 and min(R[i][3], R[j][3]) - max(R[i][1], R[j][1]) > 1e-9:
                raise SystemExit(f"핫스팟 H{i+1}·H{j+1} 이 겹침 — 하나로 합치거나 떼어서 다시")
    prisms = [BH.bx(x0, x1, y0, y1, 0, ztop) for x0, y0, x1, y1, _ in R]
    rest = BH.bx(0, 12, 0, 12, 0, ztop)
    for p in prisms:
        rest = rest.cut(p)
    housing = rest.fuse(*prisms)                 # clean() 안 함 → 핫스팟 경계선 유지
    solid = housing.cut(fluid)
    faces = BH.bottom_cells(solid); out = []
    for i, (x0, y0, x1, y1, q) in enumerate(R):
        f = [a for a in faces if abs(a.Center().x - (x0 + x1) / 2) < 1e-3 and abs(a.Center().y - (y0 + y1) / 2) < 1e-3 and abs(a.Area() - (x1 - x0) * (y1 - y0)) < 1e-3]
        out.append(dict(hotspot=f"H{i+1}", x0=round(x0, 3), y0=round(y0, 3), x1=round(x1, 3), y1=round(y1, 3), q_W_cm2=q, area_mm2=round((x1 - x0) * (y1 - y0), 3), found=len(f) == 1))
    return solid, out


def front_back(items, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Circle
    matplotlib.rcParams["font.family"] = ["WenQuanYi Zen Hei", "DejaVu Sans"]
    fig, axs = plt.subplots(len(items), 2, figsize=(13, 7 * len(items)))
    axs = np.atleast_2d(axs)
    for row, m in enumerate(items):
        a, b = axs[row]; HOT = [] if m.get("hs") else [tuple(map(int, c.split("_"))) for c in m["hotspot"].split("+")]
        a.add_patch(Rectangle((0, 0), 12, 12, fc="#eef0f3", ec="k", lw=1.5))

        def lab(pts, txt, col, fc):
            for i, (x, y) in enumerate(pts):
                a.add_patch(Circle((x, y), .5, fc=fc, ec=col, lw=3))
                near = any(abs(x - q[0]) < 4 and abs(y - q[1]) < 1.5 for j, q in enumerate(pts) if j != i)
                if near:
                    a.text(x, y + (.75 if i == 0 else -.75), f"{txt} ({x:.2f}, {y:.2f})", ha="center", va="bottom" if i == 0 else "top", fontsize=11, color=col, weight="bold")
                else:
                    a.text(x + (.75 if x < 6 else -.75), y, f"{txt} ({x:.2f}, {y:.2f})", va="center", ha="left" if x < 6 else "right", fontsize=12, color=col, weight="bold")
        lab(m["pin"], "입구", "#1f4fd8", "white"); lab(m["pout"], "출구", "#c0301a", "gold")
        a.set_xlim(0, 12); a.set_ylim(0, 12); a.set_xlabel("x [mm] →"); a.set_ylabel("y [mm] ↑")
        a.set_title(f"{m['name']} — 앞면(윗면): 입구·출구\n위에서 내려다봄 · STEP {m['name']}.step", fontsize=14, weight="bold")
        if m.get("hs"):      # 아무 배치: 바닥 = 핫스팟 면(H1, H2 …) + 나머지 한 면(기본 50 W/cm²)
            b.add_patch(Rectangle((0, 0), 12, 12, fc="#fde9b0", ec="k", lw=1.5))
            b.text(.3, 11.6, "나머지 면: 50 W/cm²", fontsize=11, color="#777", va="bottom")
            for i, (x0, y0, x1, y1, q) in enumerate(hs_rects(m["hs"])):
                b.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="#e8452c", ec="k", lw=1.8))
                small = min(x1 - x0, y1 - y0) < 2.4
                b.text((x0 + x1) / 2, (y0 + y1) / 2, f"H{i+1}\n{q:g} W/cm²", ha="center", va="center", fontsize=9 if small else 13, weight="bold", color="white")
                b.text((x0 + x1) / 2, y1 + .15, f"x {x0:g}~{x1:g}, y {y0:g}~{y1:g}", ha="center", va="top", fontsize=9.5, color="#7a1c0c", weight="bold")
        else:
            for r in range(1, 5):
                for c in range(1, 5):
                    hot = (r, c) in HOT
                    b.add_patch(Rectangle(((c - 1) * 3, (r - 1) * 3), 3, 3, fc="#e8452c" if hot else "#fde9b0", ec="k", lw=1.3))
                    b.text((c - .5) * 3, (r - .5) * 3, f"{r}_{c}\n{'300' if hot else '50'} W/cm²", ha="center", va="center",
                           fontsize=14 if hot else 10, weight="bold" if hot else "normal", color="white" if hot else "#777")
        b.set_xlim(0, 12); b.set_ylim(12, 0); b.set_xlabel("x [mm] →"); b.set_ylabel("y [mm] ↓")
        hl = f"{len(m['hs'])}곳 (바닥면이 핫스팟대로 나뉨)" if m.get("hs") else m["hotspot"].replace("+", " + ")
        b.set_title(f"{m['name']} — 뒷면(바닥): 핫스팟 {hl}\n아래에서 올려다봄 (위아래 뒤집힘)", fontsize=14, weight="bold")
        for ax in (a, b):
            ax.set_aspect("equal"); ax.set_xticks(range(0, 13, 3)); ax.set_yticks(range(0, 13, 3))
    Q = items[0].get("Q", 55)
    fig.suptitle(f"{items[0]['name']}: 왼쪽 = 앞면 입구·출구, 오른쪽 = 뒷면 핫스팟 (유량 {Q:g} mL/min = 입구 {Q / 60 / (2 * np.pi * .16):.3f} m/s)", fontsize=15, weight="bold")
    fig.tight_layout(rect=(0, 0, 1, .94)); fig.savefig(path, dpi=80); plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    items = []
    for a in sys.argv[1:]:
        name, hs = a.split(":")
        m = mask_of(name, hs)
        (OUT / f"{name}_mask.json").write_text(json.dumps(m, ensure_ascii=False))
        print(build_step(m), flush=True)
        items.append(m)
        front_back([m], OUT / f"{name}_front_back.png")      # 설계마다 한 장 (왼쪽 앞면 입구·출구 / 오른쪽 뒷면 핫스팟)
