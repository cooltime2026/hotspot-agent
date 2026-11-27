"""새 모양 가족 F: '핫스팟 줄 전용 입구' (Split-Feed) — 가장자리(1행) 핫스팟용 발명 2.

  python geometry/split_feed.py          # F1 만들기 → out/step_split/

데이터 근거 (data/ml/cell_temps.csv, 2026-11-27):
  핫스팟이 아닌 칸끼리 비교하면 '가장자리 행(1·4행) − 가운데 행(2·3행)' 온도 차이가
    띠 가족 A·B·C·M (채널 y 1.5~10.5, 헤더 끝은 막다른 골목)  평균 +8 ℃ (74+ Run)
    D0·D1 (채널 y 0.6~11.4, 채널 끝 바로 위에 띠가 있어 끝까지 물이 흐름)  평균 −5 ℃ (25 Run)
  → 가장자리 줄이 덜 식는 것은 핫스팟과 상관없이 늘 있는 현상. 원인 후보 = 1행 아래쪽(y<2)에 흐르는 물이 거의 없음.
  (D는 매니폴드도 달라서 채널 끝 하나만의 효과라고 확정은 못 함)

아이디어:
  SimScale 입구는 2개이고 각각 Q/2 를 넣는다(속도 경계조건).
  띠 가족에서는 아래 입구 (9,1) 물도 오른쪽 등뼈를 타고 판 전체로 퍼진다.
  F 는 오른쪽 등뼈(B망)의 아래 끝(y 1.5~2.35)을 끊는다 →
    아래 입구 물 Q/2 전부: 입구 받침 → 관통층 구멍(E1과 같은 자리) → 채널층 아래 헤더(y 0.5~1.5)
    → 22개 채널 끝 → 첫 띠(A망, 회수, y ≈1.8~2.15) 로만 나감.  = 1행 아래쪽 띠 하나에 전체 물의 절반.
    위 입구 물 Q/2 는 등뼈 → 나머지 띠 전부 (판 나머지는 띠 15 모양의 반 유량).
  덤: 등뼈를 끊은 자리(x 10.4~11.4)에 첫 띠(A)를 늘려서, 띠 가족에서 늘 죽어 있던 오른쪽 채널 2개(x 10.75, 11.25)도
      1행에서는 헤더→첫 띠로 흐르게 함 (모서리 1_4 용).
E1 과 차이: E1 은 아래 입구 물이 구멍과 등뼈로 나뉨(얼마씩인지 모름). F1 은 반을 강제로 1행에 보냄.
대가(예상): 2~4행은 물이 반 → 배경 온도 상승. 압력은 낮아질 것(위 입구가 반 유량만 밀면 됨). 둘 다 확인 안 됨.
4행 핫스팟은 위아래 뒤집은 모양(y → 12−y)을 쓰면 됨.
STEP 규칙은 v3 와 같음 (축 정렬, 0.05 mm 격자, 다른 망 벽 ≥ 0.2 mm). 층 사이(관통층↔덮개 홈층)도 다른 망끼리 안 겹치게 검사.
"""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from geometry import param_manifold as PM  # noqa: E402

BASE = ["n", "yf", "s", "xf", "b", "wf"]
_SP0 = PM.smooth_polys
HOLE = (8.6, 0.6, 11.1, 1.4)          # E1 과 같은 구멍 (입구 받침 안쪽, 아래 헤더 위)
GAP = 0.2


def smooth_polys(p):
    from shapely.geometry import box
    from shapely.ops import unary_union
    Pl, Ul, _ = _SP0({k: p[k] for k in BASE})
    # 첫 띠(가장 아래 A망) 찾기
    a0 = min((g for v, g in Pl if v == 1), key=lambda g: g.bounds[1])
    y0, y1 = a0.bounds[1], a0.bounds[3]
    ycut = round((y1 + GAP) / 0.05) * 0.05
    if ycut < y1 + GAP - 1e-9:
        ycut += 0.05
    # 관통층: 구멍(B) + 첫 띠를 오른쪽 끝(11.4)까지 늘림
    P1 = [g for v, g in Pl if v == 1 and g is not a0] + [unary_union([a0, box(PM.XP1, y0, 11.4, y1)])]
    Pl = [(1, g) for g in P1] + [(v, g) for v, g in Pl if v == 2] + [(2, box(*HOLE))]
    # 덮개 홈층: 오른쪽 등뼈(B) 아래 끝 y 1.5 ~ ycut 잘라냄 → 아래 입구 받침은 구멍으로만 이어짐
    cut = box(PM.XP1, 1.5, 11.5, ycut)
    U2 = unary_union([g for v, g in Ul if v == 2]).difference(cut)
    U2 = list(U2.geoms) if hasattr(U2, "geoms") else [U2]
    Ul = [(v, g) for v, g in Ul if v == 1] + [(2, g) for g in U2]
    gap = min(a.distance(b) for lay in (Pl, Ul) for va, a in lay for vb, b in lay if va != vb)
    # 층 사이: 관통층 A ↔ 덮개 B (그리고 반대) 가 xy 로 겹치거나 닿으면 두 망이 이어짐 → 금지
    xgap = min(a.distance(b) for va, a in Pl for vb, b in Ul if va != vb)
    return Pl, Ul, min(gap, xgap), dict(ycut=ycut, a0=(y0, y1), xgap=xgap, n_U2=len(U2))


def build_step(name, p, outdir="out/step_split"):
    Pl, Ul, gap, info0 = smooth_polys(p)
    assert gap >= GAP - 1e-6, f"벽 부족 {gap}"
    assert info0["n_U2"] == 2, "B망 덮개층이 '아래 받침'과 '나머지' 두 조각이어야 함"
    orig = PM.smooth_polys
    PM.smooth_polys = lambda _q: (Pl, Ul, gap)
    try:
        info = PM.build_step_smooth(name, {k: p[k] for k in BASE}, outdir=outdir)
    finally:
        PM.smooth_polys = orig
    info.update(split_feed=True, ycut=info0["ycut"], first_band=info0["a0"], min_gap_mm=round(gap, 3))
    (Path(outdir) / f"{name}.json").write_text(json.dumps(info, ensure_ascii=False, indent=1, default=float))
    return info


def draw(path, p, title):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    Pl, Ul, gap, info = smooth_polys(p)
    fig, axs = plt.subplots(1, 2, figsize=(11, 5.4))
    col = {1: "#3b6fd8", 2: "#d9483b"}
    for ax, lay, nm in [(axs[0], Pl, "관통층 P (채널 바로 위 구멍)"), (axs[1], Ul, "덮개 홈층 U (등뼈·받침)")]:
        for v, g in lay:
            for gg in (g.geoms if hasattr(g, "geoms") else [g]):
                x, y = gg.exterior.xy; ax.fill(x, y, color=col[v], alpha=.8, lw=0)
        ax.axhspan(0.5, 1.5, color="0.6", alpha=.25)
        for k in range(5):
            ax.axhline(3 * k, c="k", lw=.4); ax.axvline(3 * k, c="k", lw=.4)
        for i, (px, py) in enumerate(PM.PORTS):
            ax.plot(px, py, "o", mfc="white" if i < 2 else "gold", mec="k", ms=9)
        ax.set_xlim(0, 12); ax.set_ylim(0, 12); ax.set_aspect("equal"); ax.set_title(nm, fontsize=10)
    axs[1].add_patch(plt.Rectangle((PM.XP1, 1.5), 1.1, info["ycut"] - 1.5, fill=False, ec="k", ls="--", lw=1.2))
    axs[1].text(9.0, 2.9, "등뼈 끊음", fontsize=9)
    fig.suptitle(title + "   (파랑 A망=출구 (3,1)(3,11) / 빨강 B망=입구 (9,1)(9,11) 금색, 회색 띠 = 채널층 헤더)", fontsize=9)
    fig.tight_layout(); fig.savefig(path, dpi=110); plt.close(fig)


F = {
    "F1": dict(n=15, yf=6.0, s=0.0, xf=6.0, b=0.0, wf=0.7),     # E1 과 같은 띠 15 (B4 와 비슷)
}

if __name__ == "__main__":
    import matplotlib; matplotlib.rcParams["font.family"] = ["WenQuanYi Zen Hei", "DejaVu Sans"]
    out = Path("out/step_split"); out.mkdir(parents=True, exist_ok=True)
    for name, p in F.items():
        b = build_step(name, p)
        draw(out / f"{name}_layers.png", p, f"{name}: 아래 입구 → 1행 헤더 전용")
        print(name, {k: b[k] for k in ["fluid_solids", "min_gap_mm", "fluid_mm3", "bottom_faces", "ycut", "dead_fluid_filled_mm3"]})
    (out / "round_F.json").write_text(json.dumps(F, ensure_ascii=False, indent=1))
