"""포스터 '설계 방법' 그림 — 참고 포스터(실험방법) 방식: 그림 흐름 + [단계] + 조건 목록  → out/poster_icons/method_*.png/svg

  python geometry/poster_method.py
"""
from pathlib import Path
import sys, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, Polygon, FancyArrowPatch, Circle

sys.path.insert(0, str(Path(__file__).resolve().parent))
import poster_icons as PI  # noqa: E402

matplotlib.rcParams.update({"font.family": ["WenQuanYi Zen Hei", "DejaVu Sans"], "svg.fonttype": "none"})
OUT = PI.OUT
PUR, PUR2, PINK, BLUE, LBLUE, GRAY, LG = PI.PUR, PI.PUR2, PI.PINK, PI.BLUE, PI.LBLUE, PI.GRAY, PI.LG
TXT = "#2b2b2b"


# ---------- 작은 그림들 ----------
def pic_manifold(ax):
    PI.canvas(ax)
    PI.rbox(ax, 1, 1, 8, 8, LBLUE, r=.3)
    for j in range(14):
        ax.add_patch(Rectangle((1.45 + j * .53, 1.3), .22, 7.4, fc="white", lw=0, zorder=2))
    for k in range(5):
        x0 = 1.0 if k % 2 == 0 else 2.2
        ax.add_patch(Rectangle((x0, 2.0 + k * 1.4), 6.8, .55, fc=PUR, lw=0, zorder=3))
    for (x, y) in [(2.2, 1.0), (7.8, 1.0), (2.2, 9.0), (7.8, 9.0)]:
        ax.add_patch(Circle((x, y), .55, fc="white", ec=PINK, lw=2.5, zorder=4))


def pic_layers(ax):
    PI.canvas(ax)
    def slab(y, fc, ec):
        ax.add_patch(Polygon([[1.2, y], [6.2, y], [8.8, y + 1.6], [3.8, y + 1.6]], fc=fc, ec=ec, lw=2, zorder=5 - y))
    slab(6.8, "white", GRAY)          # 덮개
    slab(4.9, LBLUE, BLUE)            # 덮개 홈층
    slab(3.0, "#d9c6e3", PUR)         # 관통층
    slab(1.1, "#f0f0f0", GRAY)        # 채널층 + 바닥
    for k in range(9):
        x = 1.8 + k * .55
        ax.plot([x, x + 2.6 * 0.6], [1.35, 1.35 + 1.6 * 0.6], color=GRAY, lw=1.6, zorder=6)
    for x in (3.2, 6.6):
        ax.annotate("", (x + .8, 8.0), (x + .8, 9.6), arrowprops=dict(arrowstyle="-|>", color=PINK, lw=2.5))


def pic_chart(ax):
    PI.canvas(ax)
    PI.rbox(ax, .8, .8, 8.4, 8.4, "white", PUR, 2.5, .35)
    xs = np.linspace(1.8, 8.2, 6); ys = 7.6 - 4.8 * (1 - np.exp(-(xs - 1.8) / 2.5))
    ax.plot(xs, ys, color=PINK, lw=3, marker="o", ms=7, mec="white", mew=1.5)
    ys2 = ys - 1.4 + .3 * (xs - 1.8) / 6.4
    ax.plot(xs, ys2, color=BLUE, lw=3, marker="s", ms=7, mec="white", mew=1.5)
    ax.plot([1.6, 1.6, 8.6], [8.4, 1.6, 1.6], color=GRAY, lw=2)


def pic_sliders(ax):
    PI.canvas(ax)
    for k, v in enumerate([.25, .7, .45, .6]):
        y = 8.2 - k * 2.1
        ax.plot([1, 9], [y, y], color=GRAY, lw=5, solid_capstyle="round")
        ax.plot([1, 1 + 8 * v], [y, y], color=PUR2, lw=5, solid_capstyle="round")
        ax.add_patch(Circle((1 + 8 * v, y), .6, fc="white", ec=PUR2, lw=3, zorder=3))


def pic_masks(ax):
    PI.canvas(ax)
    for off, base, band in [(0, "#d9c6e3", PUR), (1.6, LBLUE, BLUE)]:
        PI.rbox(ax, .7 + off, 2.6 - off, 6.3, 6.3, base, "white", 2, .25, z=2 + off)
        for k in range(5):
            ax.add_patch(Rectangle((1.0 + off, 3.3 - off + k * 1.15), 5.7, .45, fc=band if k % 2 else PINK, lw=0, zorder=3 + off))


def pic_check(ax):
    PI.canvas(ax)
    PI.rbox(ax, 1, 1, 8, 8, "white", PUR, 2.5, .35)
    rows = [("벽 ≥ 0.2 mm", True), ("띠 ≥ 0.35 mm", True), ("유로 연결", True), ("겹침 0", True)]
    for k, (t, ok) in enumerate(rows):
        y = 7.6 - k * 1.8
        ax.add_patch(Circle((2.3, y), .55, fc=PINK if ok else GRAY, lw=0))
        ax.plot([2.0, 2.25, 2.65], [y, y - .3, y + .3], color="white", lw=2.5)
        ax.text(3.2, y, t, va="center", fontsize=7.3, color=TXT)


def pic_table(ax):
    PI.canvas(ax)
    PI.rbox(ax, .8, 1.2, 8.4, 7.6, "white", PUR, 2.5, .3)
    ax.add_patch(Rectangle((.8, 7.2), 8.4, 1.6, fc="#d9c6e3", lw=0))
    for y in (2.8, 4.4, 5.8, 7.2):
        ax.plot([.8, 9.2], [y, y], color="#d0d0d0", lw=1.5)
    for x in (3.6, 6.4):
        ax.plot([x, x], [1.2, 8.8], color="#d0d0d0", lw=1.5)


def pic_compare(ax):
    PI.canvas(ax)
    ax.plot([1.2, 8.8], [1.2, 8.8], color=GRAY, lw=2, ls="--")
    for (x, y, c) in [(2.5, 3.1, BLUE), (4.0, 4.5, BLUE), (5.2, 5.0, BLUE), (6.3, 7.1, PINK), (7.5, 7.2, BLUE), (3.2, 2.6, BLUE)]:
        ax.add_patch(Circle((x, y), .48, fc=c, ec="white", lw=1.5, zorder=3))
    ax.plot([1, 1, 9], [9, 1, 1], color=GRAY, lw=2)


# ---------- 한 칸(패널) ----------
def panel(fig, rect, title, color, steps, conds, sub=None):
    x0, y0, w, h = rect
    bg = fig.add_axes(rect); bg.axis("off"); bg.set_xlim(0, 1); bg.set_ylim(0, 1)
    bg.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0,rounding_size=0.025", fc="white", ec=color, lw=2.2))
    bg.add_patch(FancyBboxPatch((0, .91), 1, .09, boxstyle="round,pad=0,rounding_size=0.025", fc=color, ec=color, lw=2.2))
    bg.text(.5, .955, title, ha="center", va="center", color="white", fontsize=13, weight="bold")
    n = len(steps); sw = w / n
    for i, (lab, cap, f) in enumerate(steps):
        cx = x0 + sw * (i + .5)
        bg.text((sw * (i + .5)) / w, .86, f"[{lab}]", ha="center", va="center", fontsize=9.6, color=PUR, weight="bold")
        ax = fig.add_axes([cx - sw * .36, y0 + h * .57, sw * .72, h * .25]); f(ax)
        bg.text((sw * (i + .5)) / w, .545, cap, ha="center", va="top", fontsize=8.2, color=TXT, linespacing=1.3)
        if i < n - 1:
            fig.patches.append(FancyArrowPatch((cx + sw * .37, y0 + h * .695), (cx + sw * .63, y0 + h * .695), transform=fig.transFigure,
                                               arrowstyle="-|>", mutation_scale=16, color=color, lw=2))
    bg.plot([.04, .96], [.435, .435], color="#e3dbe8", lw=1.2)
    y = .41
    for line in conds:
        if line.startswith("▶"):
            bg.text(.05, y, line, ha="left", va="top", fontsize=9.3, color=PUR, weight="bold"); y -= .046
        else:
            bg.text(.07, y, line, ha="left", va="top", fontsize=8.7, color=TXT); y -= .04


P1 = ("① SimScale 해석 데이터 구축", BLUE,
      [("형상 설계", "AutoCAD 도면\n또는 코드 자동 생성", pic_manifold),
       ("STEP 변환", "채널층·관통층·\n덮개 홈층·덮개", pic_layers),
       ("SimScale 해석", "열유동 연성 해석\n(CHT)", PI.icon1),
       ("결과 수치화", "사진 → 16칸 온도,\n채널 유량, 압력", pic_chart)],
      ["▶ 해석 조건", "- 칩 : 12 × 12 mm, 4 × 4 칸, 알루미늄", "- 열유속 : 핫스팟 2칸 300 W/cm², 그 외 50 W/cm²",
       "- 냉각수 : 물 20 °C, 정상상태 · 층류", "- 입구 2개 (유속), 출구 2개 (0 Pa)",
       "▶ 변수", "- 매니폴드 형상 38종, 핫스팟 위치 20가지", "- 유량 30 / 40 / 55 / 75 / 100 mL/min"])
P2 = ("② 매니폴드 형상 규칙화 · 자동 생성", PUR2,
      [("숫자 6개", "띠 수 · 띠 폭 ·\n모으는 위치 · V자 휨", pic_sliders),
       ("2층 유로", "관통층 (구멍)\n덮개 홈층 (등뼈)", pic_masks),
       ("제작 검사", "벽 두께 · 연결 ·\n겹침 자동 검사", pic_check)],
      ["▶ 형상 변수", "- 띠 수 n : 7 ~ 17개", "- 모으는 위치 · 정도 : yf, s", "- V자 휨 : xf, b   /   띠 폭 비율 wf : 0.5 ~ 0.85",
       "▶ 제작 조건", "- 띠 폭 ≥ 0.35 mm, 다른 유로 사이 벽 ≥ 0.2 mm", "- 축 정렬 계단 형상 (SimScale 메시 오류 방지)",
       "- 결과 : 변형 매니폴드 20종 (A · B · C) 자동 생성"])
P3 = ("③ 머신러닝 학습 · 원인 분석", PUR,
      [("데이터 정리", "Run 238건\n× 16칸 온도", pic_table),
       ("모델 학습", "칸별 온도 예측\n(릿지 회귀)", PI.icon3),
       ("빼고 맞히기", "형상 하나를 통째로\n빼고 예측 시험", pic_compare)],
      ["▶ 입력", "- 형상 특징 : 칸마다 물 흐름량, 죽은 구간,", "   찬물까지 거리 (형상 이름은 안 씀)", "- 핫스팟 위치, 유량",
       "▶ 출력", "- 16칸 온도 → 칩 최고 온도, 압력 강하",
       "▶ 데이터 분석", "- 가장자리 핫스팟 = 채널 끝 유량 부족 → 새 구조 필요"])
P4 = ("④ 새 구조 고안 · 검증 반복", PINK,
      [("새 형상", "원인에 맞춘 구조\n+ 머신러닝 설계", PI.icon4),
       ("사전 예측", "SimScale 전에\n온도 예측 기록", pic_compare),
       ("검증 · 재학습", "결과 등록 후\n모델 다시 학습", PI.icon5)],
      ["▶ 고안한 형상", "- L1 : 핫스팟 열만 여는 띠", "- F1 : 핫스팟 줄 전용 입구", "- E1 : 가장자리 직접 급수 (실패 → 원인 분석)",
       "▶ 머신러닝 설계", "- S1 ~ S9 : 바람개비형 · 대역형 · V자 빗살형 등",
       "▶ 반복", "- 예측 → SimScale → 비교 → 재학습 (238건까지)"])

if __name__ == "__main__":
    fig = plt.figure(figsize=(22, 7.2))
    ws = [.295, .222, .222, .222]; gap = .008; x = .004
    for (t, c, s, cd), w in zip([P1, P2, P3, P4], ws):
        panel(fig, [x, .02, w, .96], t, c, s, cd); x += w + gap
    fig.savefig(OUT / "method_all.png", dpi=220, transparent=True); fig.savefig(OUT / "method_all.svg", transparent=True)
    plt.close(fig)
    for k, (P, w) in enumerate(zip([P1, P2, P3, P4], [7.2, 5.6, 5.6, 5.6]), 1):
        fig = plt.figure(figsize=(w, 7.2)); panel(fig, [.01, .01, .98, .98], *P)
        fig.savefig(OUT / f"method_{k}.png", dpi=250, transparent=True); fig.savefig(OUT / f"method_{k}.svg", transparent=True); plt.close(fig)
    print("저장")
