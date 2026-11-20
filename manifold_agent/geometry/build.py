"""매니폴드 4종 STEP 생성 (CadQuery).

python -m geometry.build            → out/step/manifold_<type>.step + 미리보기 PNG

각 STEP의 바디(이름):
  fluid              : 냉각수 유로 전체 (입구관 → 매니폴드 → 마이크로채널 → 출구관)
  heatsink           : 구리 히트싱크 (바닥 + 핀). 유로 부분은 비어 있음
  cover              : 매니폴드 커버. 유로 부분은 비어 있음
  chip_cell_<r>_<c>  : 칩을 4x4로 나눈 16개 바디 (r: y방향 1..4, c: x방향 1..4)
                       → SimScale에서 이 중 하나에만 발열(power source)을 준다
좌표: 칩 왼쪽 아래 모서리 = 원점, 단위 mm, 유동(채널) 방향 = +x, z=0 이 칩 윗면.
모든 치수는 P 딕셔너리에서 바꾼다 (실제 형상 치수 받으면 여기만 수정).
"""
from __future__ import annotations
from pathlib import Path
import cadquery as cq

P = dict(
    chip=20.0, chip_t=0.5, ncell=4,           # 칩
    base_t=0.5, ch_w=0.4, fin_w=0.4, ch_d=1.0,  # 히트싱크 / 마이크로채널
    cover_t=2.5,                               # 커버 두께
    pipe_d=2.0,                                # 입출구 지름
    hdr_w=3.0,                                 # U/Z 헤더 폭
    slot_w=2.0, n_slot=5, slot_d=1.5,          # 교차형 슬롯
    tree_w=1.0,                                # 트리 덕트 폭
)


def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def cyl(x, y, z0, z1, d):
    return cq.Workplane("XY").circle(d / 2).extrude(z1 - z0).translate((x, y, z0))


def union(parts):
    out = parts[0]
    for p in parts[1:]:
        out = out.union(p)
    return out


def channels(x0, x1):
    L, w, f = P["chip"], P["ch_w"], P["fin_w"]
    n = int((L + f) // (w + f)); used = n * w + (n - 1) * f; off = (L - used) / 2
    z0 = P["base_t"]; z1 = z0 + P["ch_d"]
    return [box(x0, x1, off + i * (w + f), off + i * (w + f) + w, z0, z1) for i in range(n)], n


def zl():
    zb = P["base_t"]; zt = zb + P["ch_d"]; ztop = zt + P["cover_t"]
    return zb, zt, ztop


def fluid_UZ(kind):
    L, hw, d = P["chip"], P["hdr_w"], P["pipe_d"]
    zb, zt, ztop = zl()
    ch, _ = channels(-0.01, L + 0.01)
    y0, y1 = -d / 2 - 0.5 - 0.5, L + d / 2 + 0.5 + 0.5
    hin = box(-hw, 0, y0, y1, zb, zt); hout = box(L, L + hw, y0, y1, zb, zt)
    yi = y0 + d / 2 + 0.5
    yo = yi if kind == "U" else y1 - d / 2 - 0.5
    pin = cyl(-hw / 2, yi, zt - 0.01, ztop, d); pout = cyl(L + hw / 2, yo, zt - 0.01, ztop, d)
    fp = (-hw - 2, L + hw + 2, y0 - 2, y1 + 2)
    return union(ch + [hin, hout, pin, pout]), fp


def fluid_interleaved():
    L, sw, ns, d = P["chip"], P["slot_w"], P["n_slot"], P["pipe_d"]
    zb, zt, ztop = zl(); zs = zt + P["slot_d"]
    ch, _ = channels(0, L)
    pitch = L / ns; parts = list(ch)
    pl = 2.5  # 플레넘 폭
    for i in range(ns):
        xc = (i + 0.5) * pitch
        if i % 2 == 0:   # 입구 슬롯 → 아래쪽(y<0) 입구 플레넘으로 연장
            parts.append(box(xc - sw / 2, xc + sw / 2, -1 - pl, L, zt - 0.01, zs))
        else:            # 출구 슬롯 → 위쪽(y>L) 출구 플레넘으로 연장
            parts.append(box(xc - sw / 2, xc + sw / 2, 0, L + 1 + pl, zt - 0.01, zs))
    x_in = (0.5 * pitch - sw / 2, (ns - 0.5) * pitch + sw / 2)
    x_out = (1.5 * pitch - sw / 2, (ns - 1.5) * pitch + sw / 2)
    parts.append(box(*x_in, -1 - pl, -1, zt - 0.01, zs))
    parts.append(box(*x_out, L + 1, L + 1 + pl, zt - 0.01, zs))
    parts.append(cyl(L / 2, -1 - pl / 2, zs - 0.01, ztop, d))
    parts.append(cyl(L / 2, L + 1 + pl / 2, zs - 0.01, ztop, d))
    fp = (-2, L + 2, -1 - pl - 2, L + 1 + pl + 2)
    return union(parts), fp


def _tree_side(sign, xedge):
    """sign=-1: 왼쪽(입구), +1: 오른쪽(출구). xedge: 칩 가장자리 x."""
    L, w, d = P["chip"], P["tree_w"], P["pipe_d"]
    zb, zt, ztop = zl()
    X = lambda a: xedge + sign * a           # 가장자리에서 바깥쪽으로 a mm
    def hbar(a0, a1, yc):
        xa, xb = sorted((X(a0), X(a1))); return box(xa, xb, yc - w / 2, yc + w / 2, zb, zt)
    def vbar(a, ya, yb):
        xa, xb = sorted((X(a), X(a + w))); return box(xa, xb, ya - w / 2, yb + w / 2, zb, zt)
    y4 = [L * (2 * i + 1) / 8 for i in range(4)]       # 4갈래 끝
    y2 = [(y4[0] + y4[1]) / 2, (y4[2] + y4[3]) / 2]
    yc = L / 2
    parts = [box(*sorted((X(0), X(1.0))), 0, L, zb, zt)]   # 칩 가장자리 분배 플레넘(폭 1mm)
    parts += [hbar(0.99, 2.5, y) for y in y4]
    parts += [vbar(2.5, y4[0], y4[1]), vbar(2.5, y4[2], y4[3])]
    parts += [hbar(2.5 + w - 0.01, 5.0, y) for y in y2]
    parts += [vbar(5.0, y2[0], y2[1])]
    pad = d + 0.6
    parts += [hbar(5.0 + w - 0.01, 7.0, yc)]
    xa, xb = sorted((X(7.0), X(7.0 + pad)))
    parts += [box(xa, xb, yc - pad / 2, yc + pad / 2, zb, zt)]
    parts += [cyl(X(7.0 + pad / 2), yc, zt - 0.01, ztop, d)]
    return parts, 7.0 + pad


def fluid_tree():
    L = P["chip"]
    ch, _ = channels(-0.01, L + 0.01)
    left, ext = _tree_side(-1, 0.0); right, _ = _tree_side(+1, L)
    fp = (-ext - 2, L + ext + 2, -2, L + 2)
    return union(ch + left + right), fp


def build(kind):
    if kind in ("U", "Z"): fluid, fp = fluid_UZ(kind)
    elif kind == "interleaved": fluid, fp = fluid_interleaved()
    elif kind == "tree": fluid, fp = fluid_tree()
    else: raise ValueError(kind)
    zb, zt, ztop = zl()
    x0, x1, y0, y1 = fp
    heatsink = box(x0, x1, y0, y1, 0, zt).cut(fluid)
    cover = box(x0, x1, y0, y1, zt, ztop).cut(fluid)
    # 유체도 하우징 안쪽만 남김 (모든 유로는 하우징 안에 있음)
    fluid = fluid.intersect(box(x0, x1, y0, y1, 0, ztop))
    n, L, t = P["ncell"], P["chip"], P["chip_t"]; dc = L / n
    asm = cq.Assembly(name=f"manifold_{kind}")
    asm.add(fluid, name="fluid", color=cq.Color(0.2, 0.5, 1.0, 1))
    asm.add(heatsink, name="heatsink", color=cq.Color(0.85, 0.55, 0.3, 1))
    asm.add(cover, name="cover", color=cq.Color(0.7, 0.7, 0.7, 1))
    cells = {}
    for r in range(n):
        for c in range(n):
            nm = f"chip_cell_{r+1}_{c+1}"
            cells[nm] = box(c * dc, (c + 1) * dc, r * dc, (r + 1) * dc, -t, 0)
            asm.add(cells[nm], name=nm, color=cq.Color(0.3, 0.3, 0.35, 1))
    return asm, {"fluid": fluid, "heatsink": heatsink, "cover": cover, **cells}


def check(kind, bodies):
    vol = {k: v.val().Volume() for k, v in bodies.items()}
    nsol = {k: len(v.solids().vals()) for k, v in bodies.items()}
    ov = []
    keys = ["fluid", "heatsink", "cover"]
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            ov.append((a, b, bodies[a].intersect(bodies[b]).val().Volume() if True else 0))
    return vol, nsol, ov


def preview(kind, fluid, path):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    verts, tris = fluid.val().tessellate(0.05)
    V = [(v.x, v.y, v.z) for v in verts]
    fig = plt.figure(figsize=(11, 5))
    ax = fig.add_subplot(121, projection="3d")
    ax.add_collection3d(Poly3DCollection([[V[i] for i in t] for t in tris], facecolor=(0.3, 0.6, 1, 1), edgecolor="none", shade=True))
    xs, ys, zs = zip(*V)
    ax.set_xlim(min(xs), max(xs)); ax.set_ylim(min(ys), max(ys)); ax.set_zlim(min(zs), max(zs))
    ax.set_box_aspect((max(xs) - min(xs), max(ys) - min(ys), 3 * (max(zs) - min(zs))))
    ax.view_init(35, -60); ax.set_title(f"{kind}: fluid body (3D)")
    ax2 = fig.add_subplot(122)
    for t in tris:
        p = [V[i] for i in t]; ax2.fill([q[0] for q in p], [q[1] for q in p], color=(0.3, 0.6, 1), lw=0)
    L, n = P["chip"], P["ncell"]
    for k in range(n + 1):
        ax2.plot([0, L], [k * L / n] * 2, "k", lw=0.5); ax2.plot([k * L / n] * 2, [0, L], "k", lw=0.5)
    for r in range(n):
        for c in range(n):
            ax2.text((c + .5) * L / n, (r + .5) * L / n, f"{r+1}_{c+1}", ha="center", va="center", fontsize=8, color="crimson")
    ax2.set_aspect("equal"); ax2.set_title("top view: fluid + chip cells (r_c)"); ax2.set_xlabel("x [mm] (flow in channels)"); ax2.set_ylabel("y [mm]")
    fig.tight_layout(); fig.savefig(path, dpi=120); plt.close(fig)


def main():
    out = Path("out/step"); out.mkdir(parents=True, exist_ok=True)
    for kind in ["U", "Z", "interleaved", "tree"]:
        asm, bodies = build(kind)
        asm.save(str(out / f"manifold_{kind}.step"), exportType="STEP")
        vol, nsol, ov = check(kind, bodies)
        print(f"[{kind}] fluid 체적 {vol['fluid']:.1f} mm³ (solid {nsol['fluid']}개), heatsink {vol['heatsink']:.1f}, cover {vol['cover']:.1f}, "
              f"칩칸 16개, 겹침 " + ", ".join(f"{a}-{b}:{v:.2e}" for a, b, v in ov))
        preview(kind, bodies["fluid"], out / f"manifold_{kind}.png")


if __name__ == "__main__":
    main()
