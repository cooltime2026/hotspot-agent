"""N1~N24 한눈에 (윗면에서 본 관통층·덮개 홈, 포트, 핫스팟 칸) → out/new_designs/overview.png  (2026-11-28)
색: 파랑 = 입구망, 빨강 = 출구망 (진한 = 관통층 슬롯, 연한 = 덮개 홈), 흰 원 = 입구 포트, 노란 원 = 출구 포트, 검은 테두리 = 핫스팟 칸.
그림은 앞면(위에서 내려다봄, y 위쪽) 기준. 칸 이름 r_c 는 y=(r-1)*3~r*3 (바닥에서 보면 위아래 뒤집힘)."""
import json
from pathlib import Path
import numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
matplotlib.rcParams["font.family"] = ["WenQuanYi Zen Hei", "DejaVu Sans"]
OUT = Path(__file__).resolve().parents[1] / "out/new_designs"
fs = sorted(OUT.glob("N*_mask.json"), key=lambda f: int(f.stem.split("_")[0][1:]))
nr = int(np.ceil(len(fs) / 6))
fig, axs = plt.subplots(nr, 6, figsize=(24, 4.4 * nr))
for ax, f in zip(axs.flat, fs):
    m = json.loads(f.read_text()); cav = np.array(m["cav"]).reshape(240, 240); gro = np.array(m["gro"]).reshape(240, 240)
    img = np.ones((240, 240, 3))
    img[gro == 1] = (.75, .85, 1); img[gro == 2] = (1, .8, .78); img[cav == 1] = (.1, .35, .9); img[cav == 2] = (.85, .2, .15)
    ax.imshow(img, origin="lower", extent=(0, 12, 0, 12))
    if m.get("hs"):      # 아무 배치
        for h in m["hs"]:
            ax.add_patch(Rectangle((h["x"] - h["lx"] / 2, h["y"] - h["ly"] / 2), h["lx"], h["ly"], fill=False, ec="k", lw=2.5))
            ax.text(h["x"], h["y"], f"{h['q']:g}", ha="center", va="center", fontsize=8, weight="bold")
    else:
        for c in m["hotspot"].split("+"):
            r, k = map(int, c.split("_")); ax.add_patch(Rectangle(((k - 1) * 3, (r - 1) * 3), 3, 3, fill=False, ec="k", lw=2.5))
    for x, y in m["pin"]: ax.add_patch(Circle((x, y), .4, fc="white", ec="#1f4fd8", lw=2))
    for x, y in m["pout"]: ax.add_patch(Circle((x, y), .4, fc="gold", ec="#c0301a", lw=2))
    ax.set_xlim(0, 12); ax.set_ylim(0, 12); ax.set_xticks([0, 3, 6, 9, 12]); ax.set_yticks([0, 3, 6, 9, 12]); ax.tick_params(labelsize=7)
    ax.set_title(f"{m['name']}  핫스팟 {'아무 배치 ' + str(len(m['hs'])) + '곳' if m.get('hs') else m['hotspot']}\n{m['fam']}{' (헤더형)' if m['head'] else ''}에서 진화 · 예상 {m['mlT']:.1f} ℃", fontsize=11)
fig.suptitle("머신러닝 새 설계 N1~N24 (윗면에서 본 모양 · 파랑 입구망 / 빨강 출구망 · 진한 = 슬롯, 연한 = 덮개 홈 · 검은 칸 = 핫스팟) — 예상 온도는 확인 안 됨", fontsize=15, weight="bold")
for ax in axs.flat[len(fs):]:
    ax.axis("off")
fig.tight_layout(rect=(0, 0, 1, .965)); fig.savefig(OUT / "overview.png", dpi=70)
print("저장", OUT / "overview.png")
