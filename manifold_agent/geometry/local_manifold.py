"""새 모양 가족 L: '국소 개방' 띠형 매니폴드 (띠 가족 + 핫스팟 열에만 여는 띠).

  python geometry/local_manifold.py          # L1~L4 만들기 → out/step_local/

아이디어
  띠 가족은 22개 채널(세로 열)이 모두 같은 띠 배치를 봄 → 핫스팟 열만 더 시원하게 할 수 없음.
  L 가족: 핫스팟 줄(yf) 근처 띠 2k개는 덮개 홈층(U)에는 그대로 있지만(등뼈에 연결),
          관통층(P) 구멍은 핫스팟 열(x0~x1)에서만 연다.
  → 핫스팟 열의 채널: 띠 n개 (구간 짧음 = 물 많이, 찬물 가까이)
    나머지 열의 채널: 띠 n−2k개 (그 자리에 긴 구간 하나 = 저항 큼) → 물이 핫스팟 열로 더 몰림.
  2k개(짝수, 연속)를 빼므로 남은 띠의 A/B 번갈아 순서가 유지됨(같은 망끼리 붙지 않음).
변수: 띠 가족 6개(n, yf, s, xf, b, wf) + k(국소 띠 쌍 수 1~3) + x0, x1(여는 x 범위, mm)
STEP 규칙: v3 build_step_smooth 와 같음(축 정렬, 0.05 mm 격자, 띠 ≥0.35, 다른 망 벽 ≥0.2).
※ 이 가족은 SimScale 데이터가 아직 없음 → 모델 예측은 참고용(외삽).
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from geometry import param_manifold as PM  # noqa: E402

BASE = ["n", "yf", "s", "xf", "b", "wf"]


def local_bands(p):
    """국소 띠 번호 (yf 에 가장 가까운 연속 2k개)"""
    q = PM.resolve({k: p[k] for k in BASE}); q = {**q, "s": q["s_eff"]}
    c, _, _ = PM.band_layout(q)
    k2 = 2 * int(p["k"]); n = len(c)
    if k2 <= 0 or k2 > n - 3:
        return set()
    best = min(range(0, n - k2 + 1), key=lambda i: np.mean(np.abs(c[i:i + k2] - p["yf"])))
    # 첫 띠(0)와 마지막 띠는 포트 받침과 이어지므로 건드리지 않음
    best = min(max(best, 1), n - 1 - k2)
    return set(range(best, best + k2))


def _in_x(p, x):
    return p["x0"] <= x <= p["x1"]


def masks(p):
    """param_manifold.masks 와 같은 규칙 + 국소 띠는 P층에서 x0~x1 만 연다"""
    q = PM.resolve({k: p[k] for k in BASE}); q = {**q, "s": q["s_eff"]}
    P = np.zeros((PM.N, PM.N), int); U = np.zeros((PM.N, PM.N), int)
    centers, width, pitch = PM.band_layout(q)
    loc = local_bands(p)
    fmin = min(PM.squeeze(q, (ix + 0.5) * PM.RES) for ix in range(PM.N))
    ok = bool(np.all(fmin * (pitch - width) >= PM.GMIN - 1e-9) and np.all(fmin * width >= PM.WMIN - 1e-9))
    for ix in range(PM.N):
        x = (ix + 0.5) * PM.RES; f = PM.squeeze(q, x)
        for k, (c, w0) in enumerate(zip(centers, width)):
            w = w0 * f
            yc = np.clip(6 + (c - 6) * f, 1.7 + w / 2, 10.3 - w / 2)
            iy0, iy1 = int(round((yc - w / 2) / PM.RES)), int(round((yc + w / 2) / PM.RES))
            v = 1 if k % 2 == 0 else 2
            if PM.XP0 <= x <= PM.XP1 and (k not in loc or _in_x(p, x)):
                P[iy0:iy1, ix] = v
            if (v == 1 and 0.6 <= x <= PM.XP1) or (v == 2 and PM.XP0 <= x <= 11.4):
                U[iy0:iy1, ix] = v
    gx = lambda a, b: slice(int(round(a / PM.RES)), int(round(b / PM.RES)))
    U[gx(0.4, 11.5), gx(0.6, 1.4)] = 1; U[gx(0.4, 11.5), gx(10.6, 11.4)] = 2
    for y0, y1 in [(0.4, 1.5), (10.5, 11.5)]:
        U[gx(y0, y1), gx(0.6, 3.6)] = 1; U[gx(y0, y1), gx(8.3, 11.4)] = 2
    for A in (P, U):
        d = (A[1:] != A[:-1]) & (A[1:] > 0) & (A[:-1] > 0)
        if d.any():
            ok = False
    return P, U, ok, dict(centers=centers, width=width, pitch=pitch, local=sorted(loc))


def smooth_polys(p):
    """param_manifold.smooth_polys 와 같은 다각형 + 국소 띠의 P층 조각은 x0~x1 구간만"""
    from shapely.geometry import box
    from shapely.ops import unary_union
    q = PM.resolve({k: p[k] for k in BASE}); q = {**q, "s": q["s_eff"]}
    centers, width, _ = PM.band_layout(q)
    loc = local_bands(p)
    xb = [PM.XP0] + [1.0 + 0.5 * j for j in range(30) if PM.XP0 < 1.0 + 0.5 * j < PM.XP1] + [PM.XP1]
    up = lambda v: np.ceil(v / 0.05 - 1e-9) * 0.05; dn = lambda v: np.floor(v / 0.05 + 1e-9) * 0.05

    def y_of(c, w0, x):
        f = PM.squeeze(q, x); w = w0 * f
        yc = np.clip(6 + (c - 6) * f, 1.7 + w / 2, 10.3 - w / 2)
        return up(yc - w / 2), dn(yc + w / 2)
    Pp, Up = {1: [], 2: []}, {1: [], 2: []}
    for k, (c, w0) in enumerate(zip(centers, width)):
        v = 1 if k % 2 == 0 else 2
        segs = [(x0, x1, *y_of(c, w0, (x0 + x1) / 2)) for x0, x1 in zip(xb[:-1], xb[1:])]
        boxes = [box(x0, y0, x1, y1) for x0, x1, y0, y1 in segs]
        pboxes = [bx for (x0, x1, _, _), bx in zip(segs, boxes) if k not in loc or _in_x(p, (x0 + x1) / 2)]
        if pboxes:
            Pp[v].append(unary_union(pboxes))
        ext = box(0.6, segs[0][2], PM.XP0, segs[0][3]) if v == 1 else box(PM.XP1, segs[-1][2], 11.4, segs[-1][3])
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


def openings(p):
    """shape_features 용 채널별 공급/회수 구멍 (공급 = B망 2)"""
    sys.path.insert(0, str(ROOT / "ml"))
    import shape_features as SF
    return SF.openings_from_mask(masks(p)[0], 2, 1.5, 10.5)


def build_step(name, p, outdir="out/step_local"):
    """v3 build_step_smooth 를 그대로 쓰되 다각형만 국소 개방 버전으로 바꿈"""
    orig = PM.smooth_polys
    PM.smooth_polys = lambda _q: smooth_polys(p)
    try:
        info = PM.build_step_smooth(name, {k: p[k] for k in BASE}, outdir=outdir)
    finally:
        PM.smooth_polys = orig
    info["local"] = dict(k=p["k"], x0=p["x0"], x1=p["x1"], bands=sorted(local_bands(p)))
    (Path(outdir) / f"{name}.json").write_text(json.dumps(info, ensure_ascii=False, indent=1, default=float))
    return info


def hotspot_x(hs):
    cols = sorted({int(c.split("_")[1]) for c in hs.split("+")})
    return max(PM.XP0, (cols[0] - 1) * 3.0), min(PM.XP1, cols[-1] * 3.0)


# 첫 4개: 기본 핫스팟 4종을 하나씩 겨냥. 띠 15개(지금까지 가장 시원했던 개수), 고른 간격 + 국소 띠.
L = {
    "L1": ("2_2+3_2", dict(n=15, yf=6.0, s=0.0, xf=6.0, b=0.0, wf=0.7, k=3)),
    "L2": ("3_3+3_4", dict(n=15, yf=7.5, s=0.0, xf=6.0, b=0.0, wf=0.7, k=2)),
    "L3": ("2_1+2_2", dict(n=15, yf=4.5, s=0.0, xf=6.0, b=0.0, wf=0.7, k=2)),
    "L4": ("1_3+1_4", dict(n=15, yf=2.0, s=0.0, xf=6.0, b=0.0, wf=0.7, k=2)),
}

if __name__ == "__main__":
    out = {}
    for name, (hs, p) in L.items():
        x0, x1 = hotspot_x(hs); p = {**p, "x0": x0, "x1": x1}
        P, U, ok, info = masks(p)
        _, _, gap = smooth_polys(p)
        print(name, hs, "x", (x0, x1), "국소 띠", info["local"], "마스크 OK", ok, "최소 벽", round(gap, 3))
        b = build_step(name, p)
        print("   STEP:", {k: b[k] for k in ["fluid_solids", "min_gap_mm", "dead_fluid_filled_mm3", "bottom_faces"]})
        out[name] = {**p, "aimed_hotspot": hs, "local_bands": info["local"]}
    Path("out/step_local/round_L.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float))
