"""2차 변형 B1~B8: A1~A8 + M1·M3 근사와 겹치지 않게(최대최소 거리) 미리 고름 → v3 STEP.  python geometry/make_round2.py"""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from geometry import param_manifold as PM
from geometry.make_round1 import KEYS, KNOWN, norm, candidate

A = json.loads(Path("out/step_param/round1.json").read_text())
rng = np.random.default_rng(11); pool = []
while len(pool) < 800:
    for p in candidate(rng, 8):
        if PM.masks(p)[2] and PM.smooth_polys(p)[2] >= 0.2 - 1e-9:
            pool.append(p)
Zp = np.array([norm(p) for p in pool]); chosen = [norm(p) for p in KNOWN] + [norm(p) for p in A.values()]; pick = []
for _ in range(8):
    d = np.min([np.linalg.norm(Zp - z, axis=1) for z in chosen], axis=0)
    i = int(np.argmax(d)); pick.append(pool[i]); chosen.append(Zp[i])
B = {f"B{i+1}": {**p, "n": PM.resolve(p)["n"]} for i, p in enumerate(sorted(pick, key=lambda p: (p["yf"], p["xf"])))}
out = Path("out/step_param_v3"); (out / "round2.json").write_text(json.dumps(B, indent=1))
for k, p in B.items():
    i = PM.build_step_smooth(k, p)
    print(k, {x: i[x] for x in ["min_gap_mm", "fluid_solids", "dead_fluid_filled_mm3", "bottom_faces"]}, "띠", i["params"]["n"])
