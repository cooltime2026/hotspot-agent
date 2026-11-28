"""포스터 '① 해석한 매니폴드' 칸 그림 — SimScale 로 돌린 모양 전부(같은 모양 합침), 묶음별 줄, 핫스팟별 1등 ★
  python geometry/poster_manifolds.py   → out/poster_icons/manifolds_panel.png/svg
"""
from pathlib import Path
import numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Patch, FancyBboxPatch
from matplotlib.lines import Line2D
ROOT = Path(__file__).resolve().parents[1]
src = (ROOT / "geometry/plot_gallery.py").read_text(encoding="utf-8")
g = {"__file__": str(ROOT / "geometry/plot_gallery.py"), "__name__": "g"}
exec(compile(src[:src.index("NOTE =")], "g", "exec"), g)
items, C_P, C_U, C_CH, C_PORT = g["items"], g["C_P"], g["C_U"], g["C_CH"], g["C_PORT"]
matplotlib.rcParams.update({"font.family": ["WenQuanYi Zen Hei", "DejaVu Sans"], "svg.fonttype": "none"})
PUR, PINK, TXT = "#5b2a6e", "#e0457b", "#2b2b2b"
BY = {it[0].split(" = ")[0]: it for it in items}
import re, json as _json
# 이름 = HTML v23 (hotspot_agent_v23_ML) 화면 이름 규칙(mlShapeOf / mlNiceOf) 그대로. (줄1 이름, 줄2 세부)
SHORT = {"M0": ("매니폴드 없음", ""), "M1": ("중앙 집중 빗살형", "헤더형"), "M3": ("V자 빗살형", "헤더형"),
         "M4": ("핫스팟 직상부 공급형", ""), "D0": ("이중 바람개비형", ""), "D1": ("말굽형", ""),
         "L1": ("가로 띠형 15줄", "국소 개방"), "E1": ("가로 띠형 15줄", "가장자리 급수"), "F1": ("F형", "핫스팟 줄 전용 입구"),
         "S1": ("흡입형", "핫스팟 위 배출"), "S2": ("바람개비형", "슬롯 0.4"), "S3": ("대역 대향류형", "방향 반대"),
         "S4": ("V자 빗살형", "폭 0.4 · 간격 1.2"), "S5": ("V자 빗살형", "폭 0.4 · 간격 2"), "S6": ("V자 빗살형", "폭 0.4 · 간격 1"),
         "S8": ("V자 빗살형", "폭 0.8 · 간격 1"), "S9": ("V자 빗살형", "폭 0.8 · 간격 1")}
for _it in items:
    _k = _it[0].split(" = ")[0]
    if _k[0] in "ABC":
        _p = _json.loads((ROOT / f"out/step_param_v3/{_k}.json").read_text())["params"]
        SHORT[_k] = (f"가로 띠형 {_p['n']}줄", f"띠 폭 비율 {_p['wf']:.2f}")
BEST = {"S2": "2_2+3_2", "S5": "2_1+2_2", "F1": "1_3+1_4", "A7": "3_3+3_4"}     # 0.912 m/s 핫스팟별 1등
ROWS = [("기본 형상", "6종", ["M0", "M1", "M3", "M4", "D0", "D1"]),
        ("가로 띠형", "8종", [f"A{i}" for i in range(1, 9)]),
        ("가로 띠형", "8종", [f"B{i}" for i in range(1, 9)]),
        ("가로 띠형\n· F형", "4종 + 3종", ["C1", "C2", "C3", "C4", None, "L1", "E1", "F1"]),
        ("흡입 · 바람개비\n· 대역 · V자 빗살", "8종", ["S1", "S2", "S3", "S4", "S5", "S6", "S8", "S9"])]


def tile(ax, it, key):
    name, desc, P, U, ports, head = it
    ax.add_patch(Rectangle((0, 0), 12, 12, fc="white", ec="#666", lw=.8, zorder=0))
    y0, y1 = (1.5, 10.5) if head else (0.6, 11.4)
    for j in range(22):
        ax.add_patch(Rectangle((0.625 + 0.5 * j, y0), 0.25, y1 - y0, fc=C_CH, ec="none", zorder=1))
    if head:
        for a, b in [(0.5, 1.5), (10.5, 11.5)]:
            ax.add_patch(Rectangle((0.625, a), 10.75, b - a, fc=C_CH, ec="none", zorder=1))
    for A, col, z in [(U, C_U, 2), (P, C_P, 3)]:
        if A is None: continue
        n = A.shape[0]; img = np.zeros((n, n, 4)); img[A > 0] = (*matplotlib.colors.to_rgb(col), 1)
        ax.imshow(img, origin="lower", extent=[0, 12, 0, 12], interpolation="nearest", zorder=z)
    for (px, py) in ports:
        ax.add_patch(Circle((px, py), 0.6, fc="white", ec=C_PORT, lw=1.3, zorder=4))
    if key in BEST:
        ax.add_patch(Rectangle((-.5, -.5), 13, 13, fill=False, ec=PINK, lw=2.6, zorder=6, clip_on=False))
        ax.text(12.4, 12.4, "★", ha="center", va="center", fontsize=11, color=PINK, zorder=7, clip_on=False)
    lab = name.replace(" = ", "=")
    t1, t2 = SHORT.get(key, (lab, ""))
    ax.text(6, -1.0, t1, ha="center", va="top", fontsize=7.0, color=TXT, weight="bold")
    ax.text(6, -3.0, (t2 + f"  ({lab})").strip(), ha="center", va="top", fontsize=5.9, color="#555555")
    ax.set_xlim(-.6, 12.6); ax.set_ylim(-.6, 12.6); ax.set_aspect("equal"); ax.axis("off")


if __name__ == "__main__":
    W, H = 8.6, 6.6
    fig = plt.figure(figsize=(W, H))
    lw_, top, rh = .14, .955, .172          # 왼쪽 묶음 이름 폭, 맨 위, 줄 높이
    tw = (1 - lw_ - .01) / 8
    for r, (gname, cnt, keys) in enumerate(ROWS):
        yb = top - (r + 1) * rh
        bg = fig.add_axes([.005, yb + .02, lw_ - .015, rh - .03]); bg.axis("off"); bg.set_xlim(0, 1); bg.set_ylim(0, 1)
        bg.add_patch(FancyBboxPatch((0, .06), 1, .88, boxstyle="round,pad=0,rounding_size=0.08", fc="#f3edf6", ec="none"))
        bg.text(.5, .6, gname, ha="center", va="center", fontsize=8.6, color=PUR, weight="bold", linespacing=1.2)
        bg.text(.5, .22, cnt, ha="center", va="center", fontsize=7.6, color=TXT)
        for c, k in enumerate(keys):
            if k is None: continue
            ax = fig.add_axes([lw_ + c * tw + tw * .1, yb + .045, tw * .8, rh * .78])
            tile(ax, BY[k], k)
    fig.legend([Patch(fc=C_P), Patch(fc=C_U), Patch(fc=C_CH), Line2D([], [], marker="o", ls="", mfc="white", mec=C_PORT, ms=7),
                Line2D([], [], marker="s", ls="", mfc="none", mec=PINK, mew=2, ms=8)],
               ["관통층", "덮개 홈층", "마이크로채널", "입·출구 포트", "핫스팟 위치별 1등"], loc="lower center", ncol=5, fontsize=8.5, frameon=False,
               bbox_to_anchor=(.5, -.005), handletextpad=.4, columnspacing=1.2)
    out = ROOT / "out/poster_icons"
    fig.savefig(out / "manifolds_panel.png", dpi=300, transparent=True); fig.savefig(out / "manifolds_panel.svg", transparent=True)
    print("저장", len(items), "종")
