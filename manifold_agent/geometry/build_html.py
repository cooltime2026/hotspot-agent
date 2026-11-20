"""HTML 에이전트(hotspot_agent v15)의 매니폴드 형상을 STEP으로 변환.

python -m geometry.build_html [키...]     (키 생략 시 기준형 M0 + 10종 전부)

형상 규칙은 HTML의 presetGeo/v3Build와 동일하게 맞춤 (단위 mm, 판 12x12, 원점 = 판 왼쪽 아래):
  바닥판     z 0 ~ 0.1          (바닥면을 4x4 = 16칸으로 분할 → SimScale 열유속 면)
  채널층     z 0.1 ~ 0.5        채널 22개, 중심 x = 0.75 + 0.5 j, 폭 0.25, 흐름 방향 y
             head 형(M 계열, M0): 채널 y 1.5~10.5 + 헤더 y 0.5~1.5, 10.5~11.5 (x 0.625~11.375)
             D 계열: 채널 y 0.6~11.4
  관통층     P 마스크(0.1 mm 격자, 값 1/2/3 = 유체), 두께 ts0
  덮개 홈층  U 마스크(값 1/2 = 유체), 두께 ts1
             ts = [layers[0].h, layers[1].h] (단층이면 [h0, 0.35]) → M 0.15/0.4, D 0.5/0.35, D6 0.3/0.35
  덮개       두께 LID, 포트 4개(지름 0.8) 관통 → 윗면 원 = 입구 2개(ports[0..1]), 출구 2개(ports[2..3])
STEP 바디: fluid (유체 하나), solid (고체 하나, 바닥 16칸 분할 면 포함)
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
import cadquery as cq
from shapely.geometry import box as sbox, Polygon, MultiPolygon
from shapely.ops import unary_union

Z = 12.0; NGRID = 120; RES = Z / NGRID
TB, HC = 0.1, 0.4; Z_CH = TB + HC
WC, PITCH, X0, NCH = 0.25, 0.5, 0.75, 22
Y0, Y1 = 1.5, 10.5
LID = 0.15; PORT_D = 0.8; NCELL = 4
NAMES = {"M0": "매니폴드 없음", "M1": "중앙 집중 빗살형", "M3": "V자 빗살형", "M4": "핫스팟 직상부 공급형",
         "M5": "파도형 빗살", "D0": "이중 바람개비형", "D1": "말굽형", "D2": "엇갈린 막대형",
         "D4": "흡입 바람개비형", "D5": "말굽 완충형", "D6": "가로 빗살형"}
SRC = Path(__file__).parent / "src" / "designs.json"


def mask_polys(mask, vals):
    m = np.isin(np.asarray(mask).reshape(NGRID, NGRID), vals)
    rects = []
    for iy in range(NGRID):
        ix = 0
        while ix < NGRID:
            if m[iy, ix]:
                s = ix
                while ix < NGRID and m[iy, ix]: ix += 1
                rects.append(sbox(s * RES, iy * RES, ix * RES, (iy + 1) * RES))
            else:
                ix += 1
    u = unary_union(rects).simplify(1e-6)
    return [] if u.is_empty else (list(u.geoms) if isinstance(u, MultiPolygon) else [u])


def poly_solid(poly: Polygon, z0, z1):
    wire = lambda coords: cq.Wire.makePolygon([cq.Vector(x, y, z0) for x, y in list(coords)[:-1]], close=True)
    face = cq.Face.makeFromWires(wire(poly.exterior.coords), [wire(i.coords) for i in poly.interiors])
    return cq.Solid.extrudeLinear(face, cq.Vector(0, 0, z1 - z0))


def bx(x0, x1, y0, y1, z0, z1):
    return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, cq.Vector(x0, y0, z0))


def fuse(shapes):
    s = shapes[0]
    if len(shapes) > 1:
        s = s.fuse(*shapes[1:]).clean()
    return s


def design(key, D):
    if key == "M0":
        return dict(head=1, ports=[[3, 1], [9, 1], [3, 11], [9, 11]], P=None, U=None, ts=[])
    d = D[key]
    ts = [d["layers"][0]["h"], d["layers"][1]["h"]] if len(d["layers"]) >= 2 else [d["layers"][0]["h"], 0.35]
    return dict(head=d["head"], ports=d["ports"], P=d["P"], U=d["U"], ts=ts, ext=d.get("ext"))


def build(key, D):
    g = design(key, D)
    parts = []
    if g["head"]:
        ya, yb = Y0, Y1
        parts += [bx(0.625, 11.375, 0.5, 1.5, TB, Z_CH), bx(0.625, 11.375, 10.5, 11.5, TB, Z_CH)]
    else:
        ya, yb = g.get("ext") or (Y0, Y1)
    for j in range(NCH):
        cx = X0 + PITCH * j
        parts.append(bx(cx - WC / 2, cx + WC / 2, ya, yb, TB, Z_CH))
    layers = []  # (z0, z1, polys)
    z = Z_CH
    if g["P"] is not None:
        for mask, vals, t in [(g["P"], [1, 2, 3], g["ts"][0]), (g["U"], [1, 2], g["ts"][1])]:
            polys = mask_polys(mask, vals)
            layers.append((z, z + t, polys))
            parts += [poly_solid(p, z, z + t) for p in polys]
            z += t
    ztop = z + LID
    # 포트: 원이 닿는 가장 높은 유체층 바닥부터 덮개 윗면까지
    for (px, py) in g["ports"]:
        circ = sbox(px - PORT_D / 2, py - PORT_D / 2, px + PORT_D / 2, py + PORT_D / 2).centroid.buffer(PORT_D / 2, 32)
        zstart = TB  # 매니폴드층이 없으면(M0) 헤더까지
        for (z0, z1, polys) in reversed(layers):
            if any(p.intersects(circ) for p in polys):
                zstart = z0; break
        parts.append(cq.Solid.makeCylinder(PORT_D / 2, ztop - zstart, cq.Vector(px, py, zstart)))
    fluid = fuse(parts)
    # 포트와 이어지지 않은 고립 유체(입출구 없는 막힌 칸)는 CFD가 못 푸므로 고체로 채운다
    port_cyls = parts[-len(g["ports"]):]
    keep, dropped = [], []
    for so in fluid.Solids():
        (keep if any(so.intersect(pc).Volume() > 1e-9 for pc in port_cyls) else dropped).append(so)
    fluid = keep[0] if len(keep) == 1 else cq.Compound.makeCompound(keep)
    g["dropped_mm3"] = round(sum(d.Volume() for d in dropped), 4)
    # 고체: 바닥 16칸 기둥을 이어 붙여(면 분할 유지) 유체를 뺀다
    dc = Z / NCELL
    cols = [bx(c * dc, (c + 1) * dc, r * dc, (r + 1) * dc, 0, ztop) for r in range(NCELL) for c in range(NCELL)]
    housing = cols[0].fuse(*cols[1:])          # clean() 하지 않음 → 칸 경계선 유지
    solid = housing.cut(fluid)
    return fluid, solid, ztop, g


def bottom_cells(solid):
    return [f for f in solid.Faces() if abs(f.Center().z) < 1e-6 and abs(f.normalAt().z + 1) < 1e-6]


def preview(key, fluid, g, path):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    verts, tris = fluid.tessellate(0.02)
    V = np.array([(v.x, v.y, v.z) for v in verts]); T = np.array(tris)
    fig = plt.figure(figsize=(11, 5.2))
    ax = fig.add_subplot(121, projection="3d")
    zc = V[T].mean(1)[:, 2]
    cols = plt.cm.viridis((zc - zc.min()) / max(np.ptp(zc), 1e-9))
    ax.add_collection3d(Poly3DCollection(V[T], facecolors=cols, edgecolor="none"))
    ax.set_xlim(0, 12); ax.set_ylim(0, 12); ax.set_zlim(0, V[:, 2].max())
    ax.set_box_aspect((12, 12, 4 * V[:, 2].max())); ax.view_init(40, -60)
    ax.set_title(f"{key} fluid body (color = height)")
    ax2 = fig.add_subplot(122)
    for t, c in sorted(zip(V[T], cols), key=lambda a: a[0][:, 2].mean()):
        ax2.fill(t[:, 0], t[:, 1], color=c, lw=0)
    for k in range(NCELL + 1):
        ax2.plot([0, 12], [3 * k] * 2, "k", lw=.6); ax2.plot([3 * k] * 2, [0, 12], "k", lw=.6)
    for r in range(NCELL):
        for c in range(NCELL):
            ax2.text(3 * c + 1.5, 3 * r + 1.5, f"{r+1}_{c+1}", ha="center", va="center", color="crimson", fontsize=9, weight="bold")
    for i, (px, py) in enumerate(g["ports"]):
        ax2.plot(px, py, "o", mfc="none", mec="k", ms=9); ax2.text(px + .3, py + .3, "IN" if i < 2 else "OUT", fontsize=8)
    ax2.set_xlim(0, 12); ax2.set_ylim(0, 12); ax2.set_aspect("equal")
    ax2.set_title("top view + bottom heat cells (row_col)"); ax2.set_xlabel("x [mm]"); ax2.set_ylabel("y [mm]")
    fig.tight_layout(); fig.savefig(path, dpi=110); plt.close(fig)


def main():
    D = json.loads(SRC.read_text())
    keys = sys.argv[1:] or ["M0", "M1", "M3", "M4", "M5", "D0", "D1", "D2", "D4", "D5", "D6"]
    out = Path("out/step_html"); out.mkdir(parents=True, exist_ok=True)
    rows = []
    for k in keys:
        fluid, solid, ztop, g = build(k, D)
        asm = cq.Assembly(name=f"manifold_{k}")
        asm.add(cq.Workplane().add(fluid), name="fluid", color=cq.Color(0.2, 0.5, 1.0, 1))
        asm.add(cq.Workplane().add(solid), name="solid", color=cq.Color(0.75, 0.75, 0.78, 1))
        asm.save(str(out / f"{k}.step"), exportType="STEP")
        ov = fluid.intersect(solid).Volume()
        nb = len(bottom_cells(solid))
        info = dict(key=k, name=NAMES[k], height_mm=round(ztop, 3), fluid_solids=len(fluid.Solids()),
                    solid_solids=len(solid.Solids()), fluid_mm3=round(fluid.Volume(), 3),
                    solid_mm3=round(solid.Volume(), 3), filled_dead_fluid_mm3=g['dropped_mm3'], bottom_faces=nb, overlap_mm3=round(ov, 6))
        rows.append(info); print(info, flush=True)
        preview(k, fluid, g, out / f"{k}.png")
    (out / "check.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
