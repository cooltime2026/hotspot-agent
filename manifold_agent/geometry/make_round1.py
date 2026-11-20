"""1차 변형 8개 고르기(공간을 고르게 채우는 라틴 하이퍼큐브) + STEP + 그림.  python geometry/make_round1.py"""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from geometry import param_manifold as PM

KEYS = ["n", "yf", "s", "xf", "b", "wf"]
KNOWN = [dict(n=13, yf=6, s=0.5, xf=6, b=0, wf=0.8), dict(n=13, yf=6, s=0.25, xf=6, b=0.8, wf=0.7)]   # M1, M3 근사


def norm(p):
    return np.array([(p[k] - PM.BOUNDS[k][0]) / (PM.BOUNDS[k][1] - PM.BOUNDS[k][0]) for k in KEYS])


def candidate(rng, m=8):
    u = (np.argsort(rng.random((len(KEYS), m)), axis=1).T + rng.random((m, len(KEYS)))) / m
    out = []
    for row in u:
        p = {k: PM.BOUNDS[k][0] + r * (PM.BOUNDS[k][1] - PM.BOUNDS[k][0]) for k, r in zip(KEYS, row)}
        p["n"] = int(round(p["n"])) | 1
        p = {k: (round(v, 2) if k != "n" else v) for k, v in p.items()}
        out.append(p)
    return out


def main():
    rng = np.random.default_rng(7)
    pool = []
    while len(pool) < 600:                       # 제작 제약을 지키는 후보만 모음
        for p in candidate(rng, 8):
            if PM.masks(p)[2]:
                pool.append(p)
    Zp = np.array([norm(p) for p in pool]); chosen = [norm(p) for p in KNOWN]; pick = []
    for _ in range(8):                           # 이미 고른 것(+M1, M3)과 가장 먼 후보를 차례로 고름(최대최소 거리)
        d = np.min([np.linalg.norm(Zp - z, axis=1) for z in chosen], axis=0)
        i = int(np.argmax(d)); pick.append(pool[i]); chosen.append(Zp[i])
    best = (float(np.max(d)), pick)
    print("마지막으로 고른 후보의 최소 거리", round(best[0], 3))
    designs = {f"A{i+1}": {**p, "n": PM.resolve(p)["n"]} for i, p in enumerate(sorted(best[1], key=lambda p: (p["yf"], p["xf"])))}
    Path("out/step_param").mkdir(parents=True, exist_ok=True)
    Path("out/step_param/round1.json").write_text(json.dumps(designs, indent=1))
    for k, p in designs.items():
        info = PM.build_step(k, p); print(k, p, "유효" if info["valid"] else "제약위반", "유체덩어리", info["fluid_solids"], "막힌유체", info["dead_fluid_filled_mm3"])

    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    from matplotlib import font_manager
    for f in font_manager.findSystemFonts():
        if "wqy-zenhei" in f:
            font_manager.fontManager.addfont(f); plt.rcParams["font.family"] = font_manager.FontProperties(fname=f).get_name()
    fig, axs = plt.subplots(2, 5, figsize=(17, 7.4))
    allp = [("M1(재현)", KNOWN[0]), ("M3(근사)", KNOWN[1])] + list(designs.items())
    for ax, (k, p) in zip(axs.flat, allp):
        r = PM.resolve(p)
        PM.draw(ax, p, f"{k}: 띠 {r['n']}개 yf={p['yf']} s={p['s']}\nxf={p['xf']} b={p['b']} wf={p['wf']}")
    fig.suptitle("1차 새 매니폴드 변형 8개 (A1~A8) + 기준 M1·M3   진한 색 = 관통층 띠(파랑 A망, 빨강 B망), 연한 색 = 덮개 홈층\n"
                 "노란 원 = 입구 (9,1),(9,11) (B망), 흰 원 = 출구 (3,1),(3,11) (A망)", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.92)); fig.savefig("out/step_param/round1.png", dpi=110)
    print("그림 out/step_param/round1.png")


if __name__ == "__main__":
    main()
