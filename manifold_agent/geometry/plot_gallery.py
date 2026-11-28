"""지금까지 SimScale 로 분석한 매니폴드 전부 한 장에 (관통층·덮개 홈층·마이크로채널·포트).
  python geometry/plot_gallery.py   → out/gallery_all_manifolds.png
"""
import csv, json, sys
from pathlib import Path
import numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
matplotlib.rcParams["font.family"] = ["WenQuanYi Zen Hei", "DejaVu Sans"]
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "ml"))
from geometry import param_manifold as PM, local_manifold as LM, edge_feed as EF, split_feed as SFd
import f_family as FF
C_P, C_U, C_CH, C_PORT = "#5b1d4f", "#a9d8f2", "#d9d9df", "#e0569b"
STRIP_PORTS = [[3, 1], [3, 11], [9, 1], [9, 11]]

runs = list(csv.DictReader(open(ROOT / "data/direct_runs.csv", encoding="utf-8")))
def record(d):
    r = [x for x in runs if x["design"] == d and abs(float(x["inlet_velocity_m_s"]) - 0.912) < 1e-3]
    if not r: return ""
    b = min(r, key=lambda x: float(x["Tmax_bottom_C"]))
    return f"0.912 m/s {len(r)}회 · 최저 {float(b['Tmax_bottom_C']):.1f} ℃ ({b['heat'].split('at ')[1].replace(',', '+')})"

D = json.loads((ROOT / "geometry/src/designs.json").read_text())
items = []   # (이름, 설명, P, U, 포트, 헤더형)
items.append(("M0", "매니폴드 없음 (기준)", None, None, [[3, 1], [9, 1], [3, 11], [9, 11]], 1))
for k, nm in [("M1", "중앙 집중 빗살형"), ("M3", "V자 빗살형"), ("M4", "직상부 공급형"), ("D0", "이중 바람개비형"), ("D1", "말굽형")]:
    items.append((k, nm, np.array(D[k]["P"]).reshape(120, 120), np.array(D[k]["U"]).reshape(120, 120), D[k]["ports"], D[k]["head"]))
for fam, nm in [("A", "띠형 1차"), ("B", "띠형 2차"), ("C", "겨냥 띠형")]:
    for i in range(1, 9):
        f = ROOT / f"out/step_param_v3/{fam}{i}.json"
        if not f.exists(): continue
        p = json.loads(f.read_text())["params"]; P, U, _, _ = PM.masks({k: p[k] for k in ["n", "yf", "s", "xf", "b", "wf"]})
        items.append((f"{fam}{i}", f"{nm} · 띠 {p['n']}개", P, U, STRIP_PORTS, 1))
hs, p = LM.L["L1"]; x0, x1 = LM.hotspot_x(hs); P, U, _, _ = LM.masks({**p, "x0": x0, "x1": x1})
items.append(("L1", "국소 개방형 (Claude 발명)", P, U, STRIP_PORTS, 1))
p = EF.E["E1"]; P, U, _, _ = PM.masks({k: p[k] for k in ["n", "yf", "s", "xf", "b", "wf"]}); P = P.copy(); P[6:14, 86:111] = 2
items.append(("E1", "가장자리 직접 급수 (Claude 발명)", P, U, STRIP_PORTS, 1))
P, U = FF.f_masks(SFd.F["F1"], "bottom")
items.append(("F1", "핫스팟 줄 전용 입구 (Claude 발명)", P, U, STRIP_PORTS, 1))
for i in range(1, 20):
    f = ROOT / f"out/step_v17/S{i}_mask.json"
    if not f.exists() or not any(r["design"] == f"S{i}" for r in runs): continue
    m = json.loads(f.read_text()); base = (m.get("base") or "")
    for pre in ["머신러닝 설계 · ", "1위 머신러닝 최적 · "]: base = base.replace(pre, "")
    if "위 · " in base[:12]: base = base.split(" · ", 1)[1]
    cav = np.array(m["cav"]).reshape(240, 240); gro = np.array(m["gro"]).reshape(240, 240)
    short = base.replace("(양끝 공급, 핫스팟 위 배출) ", "").replace(" · 슬롯이 핫스팟 바깥", "").replace("빗살 폭 ", "폭 ").replace("좌우 여유 ", "여유 ").strip(" ·")
    items.append((f"S{i}", f"{short} (v17·머신러닝)", cav, gro, m["pin"] + m["pout"], 0))

ncol = 8; nrow = -(-len(items) // ncol)
fig, axs = plt.subplots(nrow, ncol, figsize=(ncol * 2.6, nrow * 3.25))
for ax in axs.flat: ax.axis("off")
for ax, (name, desc, P, U, ports, head) in zip(axs.flat, items):
    ax.add_patch(Rectangle((0, 0), 12, 12, fc="white", ec="#555", lw=1, zorder=0))
    y0, y1 = (1.5, 10.5) if head else (0.6, 11.4)
    for j in range(22):
        ax.add_patch(Rectangle((0.625 + 0.5 * j, y0), 0.25, y1 - y0, fc=C_CH, ec="none", zorder=1))
    if head:
        for a, b in [(0.5, 1.5), (10.5, 11.5)]: ax.add_patch(Rectangle((0.625, a), 10.75, b - a, fc=C_CH, ec="none", zorder=1))
    for A, col in [(U, C_U), (P, C_P)]:
        if A is None: continue
        n = A.shape[0]; img = np.zeros((n, n, 4)); rgb = matplotlib.colors.to_rgb(col); img[A > 0] = (*rgb, 1)
        ax.imshow(img, origin="lower", extent=[0, 12, 0, 12], interpolation="nearest", zorder=2 if col == C_U else 3)
    for (px, py) in ports:
        ax.add_patch(Circle((px, py), 0.45, fc="white", ec=C_PORT, lw=1.6, zorder=4))
    ax.set_xlim(-.3, 12.3); ax.set_ylim(-.3, 12.3); ax.set_aspect("equal")
    ax.set_title(f"{name}  " + (desc.replace(" (", "\n(", 1) if len(desc) > 22 else desc), fontsize=8.3, weight="bold", pad=3)
    ax.text(6, -1.1, record(name), ha="center", va="top", fontsize=7, color="#444")
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
fig.legend([Patch(fc=C_P), Patch(fc=C_U), Patch(fc=C_CH), Line2D([], [], marker="o", ls="", mfc="white", mec=C_PORT, ms=9)],
           ["관통층", "덮개 홈층", "마이크로채널", "입·출구 포트"], loc="lower center", ncol=4, fontsize=12, frameon=False)
fig.suptitle(f"지금까지 SimScale 로 분석한 매니폴드 {len(items)}종 (위에서 내려다봄, 12 × 12 mm)  ·  아래 글자 = 0.912 m/s 실측 횟수와 가장 낮은 최고온도",
             fontsize=14, weight="bold")
fig.tight_layout(rect=(0, .03, 1, .97)); out = ROOT / "out/gallery_all_manifolds.png"; fig.savefig(out, dpi=110)
print("저장", out, len(items), "종")
