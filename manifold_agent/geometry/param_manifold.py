"""숫자 6개로 그리는 빗살(띠)형 매니폴드 가족 — M1(직선 빗살)·M3(V자 빗살)이 이 가족의 한 점.

  python geometry/param_manifold.py preview            # M1·M3 재현 확인 + 예시 그림
  python geometry/param_manifold.py step <이름> n=13 yf=6 s=0.5 xf=6 b=0 wf=0.75     # STEP 만들기

구조 (M1과 같음, 단위 mm, 0.1 mm 격자)
  채널층 z 0.1~0.5 (채널 22개, y 1.5~10.5, 양 끝 헤더) — 고정
  관통층 P (두께 0.15): 가로 띠 n개가 채널 위를 덮음. 띠는 번갈아 A망·B망.
  덮개 홈층 U (두께 0.4): 같은 띠 + 왼쪽 등뼈(A망, x 0.6~1.4) / 오른쪽 등뼈(B망, x 10.6~11.4)
  포트: A망 (3,1),(3,11) / B망 (9,1),(9,11).  ★ SimScale 입구 = B망 (9,1),(9,11) (M1·M3 실험과 같은 방향)
숫자(모양 변수)
  n  : 띠 개수 (홀수, 7~17). 많을수록 물이 채널을 짧게 지나감(잘 식고 압력 ↑)
  yf : 띠를 촘촘하게 모으는 y 위치 [mm] (핫스팟 쪽)
  s  : 모으는 정도 0~1 (0 = 고르게, 1 = 제작 제약 안에서 최대로 모음; 실제 값 s_eff)
  xf : 띠를 휘게 하는 중심 x [mm]
  b  : 휘는 정도 [mm] (+ = xf에서 멀수록 띠가 가운데로 모임 = V자, M3 ≈ +0.6)
  wf : 띠 폭 / 띠 간격 (0.5~0.85). 나머지는 띠 사이 벽
제약: 띠 폭 ≥ 0.3 mm, 띠 사이 벽 ≥ 0.1 mm (제작·격자)
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np

N, RES = 120, 0.1
YA, YB = 1.7, 10.3                 # 띠가 놓이는 범위 (M1: 1.7~10.2)
XP0, XP1 = 1.6, 10.4               # 관통층 띠 x 범위
PORTS = [[3, 1], [3, 11], [9, 1], [9, 11]]
DEFAULT = dict(n=13, yf=6.0, s=0.0, xf=6.0, b=0.0, wf=0.75)
BOUNDS = dict(n=(7, 17), yf=(2.0, 10.0), s=(0.0, 1.0), xf=(1.5, 10.5), b=(-0.8, 0.8), wf=(0.5, 0.85))


def band_layout(p):
    """띠 중심 y와 폭 (휘기 전) — 밀도 ρ(y) = 1 + 4s·exp(−(y−yf)²/(2·1.3²)) 로 띠를 배치"""
    n = int(p["n"]) | 1
    y = np.linspace(YA, YB, 2001)
    rho = 1 + 4 * p["s"] * np.exp(-(y - p["yf"]) ** 2 / (2 * 1.3 ** 2))
    cdf = np.concatenate([[0], np.cumsum((rho[1:] + rho[:-1]) / 2 * np.diff(y))]); cdf /= cdf[-1]
    edges = np.interp(np.linspace(0, 1, n + 1), cdf, y)
    centers = (edges[1:] + edges[:-1]) / 2; pitch = np.diff(edges)
    width = np.maximum(p["wf"] * pitch, WMIN)
    width = np.minimum(width, pitch - GMIN)         # 벽 ≥ GMIN
    return centers, width, pitch


def squeeze(p, x):
    """휘기(V자): xf에서 멀어질수록 띠 묶음이 y=6 쪽으로 f배 모임 (b>0). 띠 폭도 같이 줄어 벽이 유지됨. M3 ≈ b 0.8"""
    w = min(1.0, abs(x - p["xf"]) / 4.4)
    f = 1 - p["b"] * w / 4.3
    if f > 1:                                   # b<0 (벌어짐): 바깥 띠가 판 띠 범위(1.6~10.4)를 넘지 않게 제한
        c, wd, _ = band_layout(p)
        k = np.argmax(np.abs(c - 6))
        f = min(f, (4.3 - wd[k] / 2) / max(abs(c[k] - 6), 1e-6))   # 바깥 띠 끝 ≤ 1.7/10.3 (포트 받침과 벽 0.2)
    return f


WMIN, GMIN = 0.35, 0.2      # 매끈한 STEP(v2) 제약: 띠 폭 ≥ 0.35 mm, 벽 ≥ 0.2 mm (메시·수렴 안정)


def feasible(p):
    c, w, pitch = band_layout(p)
    fmin = min(squeeze(p, (ix + 0.5) * RES) for ix in range(N))
    return bool(np.all(fmin * (pitch - w) >= GMIN - 1e-9) and np.all(fmin * w >= WMIN - 1e-9))


def resolve(p):
    """s는 '가능한 최대 모으기' 대비 비율(0~1)로 해석 → 실제 모으기 정도 s_eff (제약을 항상 지킴).
    n이 너무 커서 고르게 놓아도 제약 위반이면 n을 2씩 줄임."""
    p = {**DEFAULT, **p}; p["n"] = int(p["n"]) | 1
    while p["n"] > 5 and not feasible({**p, "s": 0.0}):
        p["n"] -= 2
    lo, hi = 0.0, 3.0
    if feasible({**p, "s": hi}):
        smax = hi
    else:
        for _ in range(30):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if feasible({**p, "s": mid}) else (lo, mid)
        smax = lo
    q = dict(p); q["s_eff"] = round(p["s"] * smax, 4); q["s_max"] = round(smax, 4)
    return q


def masks(p):
    p = resolve(p); p = {**p, "s": p["s_eff"]}
    P = np.zeros((N, N), int); U = np.zeros((N, N), int)
    centers, width, pitch = band_layout(p)
    fmin = min(squeeze(p, (ix + 0.5) * RES) for ix in range(N))
    ok = bool(np.all(fmin * (pitch - width) >= GMIN - 1e-9) and np.all(fmin * width >= WMIN - 1e-9))
    for ix in range(N):
        x = (ix + 0.5) * RES; f = squeeze(p, x)
        for k, (c, w0) in enumerate(zip(centers, width)):
            w = w0 * f
            yc = np.clip(6 + (c - 6) * f, 1.7 + w / 2, 10.3 - w / 2)
            iy0, iy1 = int(round((yc - w / 2) / RES)), int(round((yc + w / 2) / RES))
            v = 1 if k % 2 == 0 else 2
            if XP0 <= x <= XP1:
                P[iy0:iy1, ix] = v
            if (v == 1 and 0.6 <= x <= XP1) or (v == 2 and XP0 <= x <= 11.4):
                U[iy0:iy1, ix] = v
    gx = lambda a, b: slice(int(round(a / RES)), int(round(b / RES)))
    U[gx(0.4, 11.5), gx(0.6, 1.4)] = 1;  U[gx(0.4, 11.5), gx(10.6, 11.4)] = 2          # 등뼈
    for y0, y1 in [(0.4, 1.5), (10.5, 11.5)]:
        U[gx(y0, y1), gx(0.6, 3.6)] = 1; U[gx(y0, y1), gx(8.3, 11.4)] = 2              # 포트 받침
    # 띠 사이 벽이 이어지는지(다른 망끼리 붙지 않았는지) 확인
    for A in (P, U):
        d = (A[1:] != A[:-1]) & (A[1:] > 0) & (A[:-1] > 0)
        if d.any():
            ok = False
    return P, U, ok, dict(centers=centers, width=width, pitch=pitch)


def design_entry(p):
    P, U, ok, _ = masks(p)
    return dict(head=1, ports=PORTS, P=P.reshape(-1).tolist(), U=U.reshape(-1).tolist(),
                layers=[dict(h=0.15), dict(h=0.4)], params=resolve(p), valid=ok)


def openings(p):
    """shape_features 용: 채널별 공급(S)/회수(C) 구멍. 공급 = B망(2) (SimScale 입구 (9,1),(9,11))"""
    import sys as _s; _s.path.insert(0, str(Path(__file__).resolve().parents[1] / "ml"))
    import shape_features as SF
    P, _, _, _ = masks(p)
    return SF.openings_from_mask(P, 2, 1.5, 10.5)


def iou(a, b):
    a, b = np.asarray(a).reshape(N, N) > 0, np.asarray(b).reshape(N, N) > 0
    return (a & b).sum() / max((a | b).sum(), 1)


def fit_existing(key):
    """기존 M1/M3 마스크와 가장 비슷한 변수 찾기 (가족 안에 들어가는지 확인)"""
    D = json.loads((Path(__file__).parent / "src/designs.json").read_text())
    Pt = np.array(D[key]["P"]).reshape(N, N)
    best = (-1, None)
    for n in [11, 13, 15]:
        for s in [0, 0.25, 0.5, 0.75, 1.0]:
            for b in [-0.6, -0.3, 0, 0.3, 0.6, 0.8]:
                for wf in [0.6, 0.7, 0.8]:
                    p = dict(n=n, yf=6, s=s, xf=6, b=b, wf=wf)
                    P, _, _, _ = masks(p)
                    sc = iou(P, Pt)
                    if sc > best[0]:
                        best = (sc, p)
    return best


def build_step(name, p, outdir="out/step_param"):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from geometry import build_html as BH
    import cadquery as cq
    D = {name: design_entry(p)}
    BH.NAMES[name] = f"자동설계 {name}"
    fluid, solid, ztop, g = BH.build(name, D)
    out = Path(outdir); out.mkdir(parents=True, exist_ok=True)
    asm = cq.Assembly(name=f"manifold_{name}")
    asm.add(cq.Workplane().add(fluid), name="fluid", color=cq.Color(0.2, 0.5, 1.0, 1))
    asm.add(cq.Workplane().add(solid), name="solid", color=cq.Color(0.75, 0.75, 0.78, 1))
    asm.save(str(out / f"{name}.step"), exportType="STEP")
    BH.preview(name, fluid, g, out / f"{name}_3d.png")
    info = dict(name=name, params=D[name]["params"], valid=D[name]["valid"], fluid_solids=len(fluid.Solids()),
                fluid_mm3=round(fluid.Volume(), 3), solid_mm3=round(solid.Volume(), 3),
                dead_fluid_filled_mm3=g["dropped_mm3"], bottom_faces=len(BH.bottom_cells(solid)), height_mm=round(ztop, 3))
    (out / f"{name}.json").write_text(json.dumps(info, ensure_ascii=False, indent=1))
    return info


def smooth_polys(p):
    """STEP용 띠 다각형 (v3). 띠 높이는 채널 사이 고체 벽 한가운데(x = 1.0 + 0.5j)에서만 바뀌는 계단형이고,
    모든 면이 축과 나란하며 y는 0.05 mm 격자에 맞춤 → 아주 작은 조각면이 생기지 않음(SimScale 접촉 계산 실패 방지).
    채널 하나에서 보면 띠가 곧은 직사각형이라 유동에는 같은 효과. 반환: P층 [(망, 다각형)], U층 [(망, 다각형)], 최소 벽"""
    from shapely.geometry import box
    from shapely.ops import unary_union
    q = resolve(p); q = {**q, "s": q["s_eff"]}
    centers, width, _ = band_layout(q)
    xb = [XP0] + [1.0 + 0.5 * j for j in range(30) if XP0 < 1.0 + 0.5 * j < XP1] + [XP1]
    up = lambda v: np.ceil(v / 0.05 - 1e-9) * 0.05; dn = lambda v: np.floor(v / 0.05 + 1e-9) * 0.05
    def y_of(c, w0, x):
        f = squeeze(q, x); w = w0 * f
        yc = np.clip(6 + (c - 6) * f, 1.7 + w / 2, 10.3 - w / 2)
        return up(yc - w / 2), dn(yc + w / 2)
    Pp, Up = {1: [], 2: []}, {1: [], 2: []}
    for k, (c, w0) in enumerate(zip(centers, width)):
        v = 1 if k % 2 == 0 else 2
        segs = [(x0, x1, *y_of(c, w0, (x0 + x1) / 2)) for x0, x1 in zip(xb[:-1], xb[1:])]
        boxes = [box(x0, y0, x1, y1) for x0, x1, y0, y1 in segs]
        Pp[v].append(unary_union(boxes))
        ext = box(0.6, segs[0][2], XP0, segs[0][3]) if v == 1 else box(XP1, segs[-1][2], 11.4, segs[-1][3])
        Up[v].append(unary_union(boxes + [ext]))
    Up[1] += [box(0.6, 0.4, 1.4, 11.5), box(0.6, 0.4, 3.6, 1.5), box(0.6, 10.5, 3.6, 11.5)]
    Up[2] += [box(10.6, 0.4, 11.4, 11.5), box(8.3, 0.4, 11.4, 1.5), box(8.3, 10.5, 11.4, 11.5)]
    out = []
    for L in (Pp, Up):
        lay = []
        for v in (1, 2):
            u = unary_union(L[v])
            lay += [(v, g) for g in (u.geoms if hasattr(u, "geoms") else [u])]
        out.append(lay)
    gap = min(a.distance(b) for lay in out for va, a in lay for vb, b in lay if va != vb)
    return out[0], out[1], gap


def build_step_smooth(name, p, outdir="out/step_param_v3"):
    """매끈한 다각형으로 STEP (build_html.build 과 같은 층·포트 규칙)"""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from geometry import build_html as BH
    import cadquery as cq
    from shapely.geometry import box as sbox
    Pl, Ul, gap = smooth_polys(p)
    parts = [BH.bx(0.625, 11.375, 0.5, 1.5, BH.TB, BH.Z_CH), BH.bx(0.625, 11.375, 10.5, 11.5, BH.TB, BH.Z_CH)]
    for j in range(BH.NCH):
        cx = BH.X0 + BH.PITCH * j
        parts.append(BH.bx(cx - BH.WC / 2, cx + BH.WC / 2, BH.Y0, BH.Y1, BH.TB, BH.Z_CH))
    z = BH.Z_CH; layers = []
    for lay, t in [(Pl, 0.15), (Ul, 0.4)]:
        polys = [g for _, g in lay]; layers.append((z, z + t, polys))
        parts += [BH.poly_solid(g, z, z + t) for g in polys]; z += t
    ztop = z + BH.LID
    for (px, py) in PORTS:
        circ = sbox(px - .4, py - .4, px + .4, py + .4).centroid.buffer(0.4, 32); zstart = BH.TB
        for (z0, z1, polys) in reversed(layers):
            if any(g.intersects(circ) for g in polys):
                zstart = z0; break
        parts.append(cq.Solid.makeCylinder(0.4, ztop - zstart, cq.Vector(px, py, zstart)))
    fluid = BH.fuse(parts)
    pcs = parts[-4:]; keep, dropped = [], []
    for so in fluid.Solids():
        (keep if any(so.intersect(pc).Volume() > 1e-9 for pc in pcs) else dropped).append(so)
    fluid = keep[0] if len(keep) == 1 else cq.Compound.makeCompound(keep)
    dc = 3.0
    cols = [BH.bx(c * dc, (c + 1) * dc, r * dc, (r + 1) * dc, 0, ztop) for r in range(4) for c in range(4)]
    solid = cols[0].fuse(*cols[1:]).cut(fluid)
    out = Path(outdir); out.mkdir(parents=True, exist_ok=True)
    asm = cq.Assembly(name=f"manifold_{name}")
    asm.add(cq.Workplane().add(fluid), name="fluid", color=cq.Color(0.2, 0.5, 1.0, 1))
    asm.add(cq.Workplane().add(solid), name="solid", color=cq.Color(0.75, 0.75, 0.78, 1))
    asm.save(str(out / f"{name}.step"), exportType="STEP")
    BH.preview(name, fluid, dict(ports=PORTS), out / f"{name}_3d.png")
    info = dict(name=name, params=resolve(p), valid=feasible({**resolve(p), "s": resolve(p)["s_eff"]}),
                min_gap_mm=round(gap, 3), fluid_solids=len(fluid.Solids()), dead_fluid_filled_mm3=round(sum(d.Volume() for d in dropped), 4),
                fluid_mm3=round(fluid.Volume(), 3), bottom_faces=len(BH.bottom_cells(solid)), height_mm=round(ztop, 3))
    (out / f"{name}.json").write_text(json.dumps(info, ensure_ascii=False, indent=1))
    return info


def draw(ax, p, title=""):
    P, U, ok, _ = masks(p)
    img = np.zeros((N, N, 3)) + 0.92
    img[U == 1] = (0.75, 0.85, 1.0); img[U == 2] = (1.0, 0.82, 0.78)
    img[P == 1] = (0.25, 0.45, 0.85); img[P == 2] = (0.85, 0.3, 0.25)
    ax.imshow(img, origin="lower", extent=[0, 12, 0, 12])
    for k in range(5):
        ax.axhline(3 * k, color="k", lw=0.4); ax.axvline(3 * k, color="k", lw=0.4)
    for i, (x, y) in enumerate(PORTS):
        ax.plot(x, y, "o", mfc="white" if i < 2 else "gold", mec="k", ms=7)
    ax.set_xticks([]); ax.set_yticks([]); ax.set_title(title + ("" if ok else "  ✗제약 위반"), fontsize=9)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "preview"
    if cmd == "preview":
        for k in ["M1", "M3"]:
            sc, p = fit_existing(k); print(k, "가장 비슷한 변수", p, f"겹침(IoU) {sc:.2f}")
    elif cmd == "step":
        p = {kv.split("=")[0]: float(kv.split("=")[1]) for kv in sys.argv[3:]}
        print(build_step(sys.argv[2], p))
