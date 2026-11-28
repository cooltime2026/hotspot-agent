"""포스터 '설계 진행 과정' 5단계 아이콘 (직접 그린 그림, 저작권 걱정 없음) → out/poster_icons/

  python geometry/poster_icons.py
  icon1~5.png / .svg (투명 배경) + flow_strip.png (5단계 한 줄)
"""
from pathlib import Path
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, Rectangle, FancyArrowPatch, Arc, Polygon, Wedge

matplotlib.rcParams.update({"font.family": ["WenQuanYi Zen Hei", "DejaVu Sans"], "svg.fonttype": "none"})
OUT = Path(__file__).resolve().parents[1] / "out" / "poster_icons"; OUT.mkdir(parents=True, exist_ok=True)
PUR, PUR2, PINK, BLUE, LBLUE, GRAY, LG = "#5b2a6e", "#8e5aa3", "#e0457b", "#3f7fd8", "#a9d4f2", "#9a9a9a", "#ece6f0"
STEP_C = [BLUE, PUR2, PUR, PINK, PUR]


def canvas(ax):
    ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.set_aspect("equal"); ax.axis("off")


def rbox(ax, x, y, w, h, fc, ec="none", lw=0, r=0.25, z=1):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", fc=fc, ec=ec, lw=lw, zorder=z))


def icon1(ax):   # 기존 형상 해석: 판 위 온도 지도 + 핫스팟
    canvas(ax)
    T = np.array([[.35, .45, .55, .4], [.5, .95, .9, .55], [.45, .7, .65, .45], [.3, .4, .45, .35]])
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("t", ["#f6e9f7", "#c79bd6", PINK, "#a3123f"])
    rbox(ax, 1.1, 1.1, 7.8, 7.8, "white", PUR, 3, .4)
    for i in range(4):
        for j in range(4):
            ax.add_patch(Rectangle((1.5 + j * 1.75, 1.5 + (3 - i) * 1.75), 1.6, 1.6, fc=cmap(T[i, j]), ec="white", lw=2, zorder=2))
    for (i, j) in [(1, 1), (1, 2)]:
        ax.add_patch(Rectangle((1.5 + j * 1.75, 1.5 + (3 - i) * 1.75), 1.6, 1.6, fill=False, ec=PUR, lw=3.5, zorder=3))
    ax.text(5, .35, "", ha="center")


def icon2(ax):   # 규칙화·자동 생성: 조절 막대 3개 → 띠 매니폴드
    canvas(ax)
    for k, v in enumerate([.3, .7, .5]):
        y = 7.6 - k * 2.2
        ax.plot([.6, 3.6], [y, y], color=GRAY, lw=4, solid_capstyle="round", zorder=1)
        ax.plot([.6, .6 + 3 * v], [y, y], color=PUR2, lw=4, solid_capstyle="round", zorder=2)
        ax.add_patch(Circle((.6 + 3 * v, y), .42, fc="white", ec=PUR2, lw=3, zorder=3))
    ax.add_patch(FancyArrowPatch((4.0, 5.4), (5.1, 5.4), arrowstyle="-|>", mutation_scale=22, color=PUR, lw=3))
    rbox(ax, 5.4, 1.2, 4.2, 8.4, LBLUE, r=.3)
    for j in range(8):
        ax.add_patch(Rectangle((5.75 + j * .47, 1.5), .2, 7.8, fc="white", lw=0, zorder=2))
    for k in range(6):
        ax.add_patch(Rectangle((5.6, 2.0 + k * 1.25), 3.8, .5, fc=PUR, lw=0, zorder=3))


def icon3(ax):   # 머신러닝 학습: 신경망
    canvas(ax)
    L = [[2.5, 5, 7.5], [1.8, 4.1, 6.4, 8.7], [3.5, 6.5]]
    xs = [1.4, 5, 8.6]
    for a in range(2):
        for y0 in L[a]:
            for y1 in L[a + 1]:
                ax.plot([xs[a], xs[a + 1]], [y0, y1], color="#c9b3d3", lw=1.8, zorder=1)
    for x, ys, c in zip(xs, L, [BLUE, PUR2, PINK]):
        for y in ys:
            ax.add_patch(Circle((x, y), .72, fc=c, ec="white", lw=2.5, zorder=2))


def icon4(ax):   # 새 구조 고안: 전구 + 안에 새 모양
    canvas(ax)
    for a in np.linspace(20, 160, 5):
        r = np.radians(a); ax.plot([5 + 3.7 * np.cos(r), 5 + 4.6 * np.cos(r)], [6.2 + 3.1 * np.sin(r) * .95, 6.2 + 3.9 * np.sin(r) * .95], color=PINK, lw=3.5, solid_capstyle="round")
    ax.add_patch(Circle((5, 5.9), 3.0, fc="#fde3ec", ec=PINK, lw=3.5, zorder=2))
    ax.add_patch(Polygon([[3.4, 3.4], [6.6, 3.4], [6.0, 2.2], [4.0, 2.2]], fc="#fde3ec", ec=PINK, lw=3.5, zorder=1))
    for k, y in enumerate([1.6, 1.0]):
        rbox(ax, 3.9, y - .25, 2.2, .45, PUR, r=.2, z=3)
    # 안쪽: 핫스팟 줄 전용 입구 느낌의 L자 + 띠
    ax.add_patch(Rectangle((3.4, 4.3), 3.2, .5, fc=PUR, zorder=3))
    ax.add_patch(Rectangle((6.1, 4.3), .5, 3.2, fc=PUR, zorder=3))
    for y in (5.5, 6.6):
        ax.add_patch(Rectangle((3.6, y), 2.2, .45, fc=PUR2, zorder=3))
    ax.add_patch(Circle((6.35, 7.9), .38, fc=PINK, ec="white", lw=1.5, zorder=4))


def icon5(ax):   # 검증·재학습 반복: 돌아가는 화살표 + 체크
    canvas(ax)
    ax.add_patch(Arc((5, 5), 7.6, 7.6, theta1=25, theta2=165, color=PUR, lw=5))
    ax.add_patch(Arc((5, 5), 7.6, 7.6, theta1=205, theta2=345, color=PINK, lw=5))
    for ang, c, d in [(25, PUR, -1), (205, PINK, -1)]:
        r = np.radians(ang); x, y = 5 + 3.8 * np.cos(r), 5 + 3.8 * np.sin(r)
        t = np.array([-np.sin(r), np.cos(r)]) * d
        n = np.array([np.cos(r), np.sin(r)])
        ax.add_patch(Polygon([[x + t[0] * 1.0, y + t[1] * 1.0], [x + n[0] * .75, y + n[1] * .75], [x - n[0] * .75, y - n[1] * .75]], fc=c, zorder=3))
    ax.add_patch(Circle((5, 5), 2.2, fc=LG, ec="none"))
    ax.plot([3.9, 4.8, 6.3], [5.0, 4.0, 6.0], color=PUR, lw=5, solid_capstyle="round", solid_joinstyle="round")


ICONS = [icon1, icon2, icon3, icon4, icon5]
TITLE = ["① 기존 형상 해석", "② 형상 규칙화·자동 생성", "③ 머신러닝 학습·원인 분석", "④ 새 구조 고안", "⑤ 검증·재학습 반복"]
SUB = ["6종 · 145건", "20종 · 81건", "238건으로 학습", "3종 · 3건", "9종 · 9건"]

if __name__ == "__main__":
    for i, f in enumerate(ICONS, 1):
        fig, ax = plt.subplots(figsize=(3, 3)); f(ax)
        for ext in ("png", "svg"):
            fig.savefig(OUT / f"icon{i}.{ext}", dpi=300, transparent=True, bbox_inches="tight", pad_inches=0.05)
        plt.close(fig)
    fig = plt.figure(figsize=(16, 4.2))
    for i, f in enumerate(ICONS):
        x0 = 0.01 + i * 0.198
        bg = fig.add_axes([x0, 0.04, 0.17, 0.92]); bg.axis("off"); bg.set_xlim(0, 1); bg.set_ylim(0, 1)
        bg.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0,rounding_size=0.06", fc="white", ec=STEP_C[i], lw=2.5))
        bg.add_patch(FancyBboxPatch((0, .82), 1, .18, boxstyle="round,pad=0,rounding_size=0.06", fc=STEP_C[i], ec=STEP_C[i], lw=2.5))
        bg.text(.5, .91, TITLE[i], ha="center", va="center", color="white", fontsize=12.5, weight="bold")
        bg.text(.5, .08, SUB[i], ha="center", va="center", color=PUR, fontsize=12, weight="bold")
        ax = fig.add_axes([x0 + .025, 0.2, 0.12, 0.6]); f(ax)
        if i < 4:
            fig.patches.append(FancyArrowPatch((x0 + .172, .5), (x0 + .196, .5), transform=fig.transFigure, arrowstyle="-|>", mutation_scale=22, color=PUR, lw=2.5))
    fig.savefig(OUT / "flow_strip.png", dpi=250, transparent=True)
    fig.savefig(OUT / "flow_strip.svg", transparent=True)
    print("저장", sorted(p.name for p in OUT.iterdir()))
