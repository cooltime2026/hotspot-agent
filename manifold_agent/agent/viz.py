"""매니폴드별 칩 온도 히트맵 (직접 중첩 계산 기반)."""
from __future__ import annotations
from pathlib import Path
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from . import config as C
from .superpose import Library

plt.rcParams["font.family"] = ["NanumGothic", "Noto Sans CJK KR", "DejaVu Sans"]


def heatmaps(model_dir, flux, flow, rows, path):
    lib = Library(joblib.load(Path(model_dir) / "model.joblib")["data"])
    flow = float(np.clip(flow, C.FLOW_MIN, C.FLOW_MAX))
    xy = lib.xy
    temps = {m: lib.temperature(m, flow, flux) for m in C.MANIFOLDS}
    vmin = min(t.min() for t in temps.values()); vmax = max(t.max() for t in temps.values())
    fig, axs = plt.subplots(1, len(C.MANIFOLDS), figsize=(4 * len(C.MANIFOLDS), 4), constrained_layout=True)
    rank = {r["manifold"]: k for k, r in enumerate(rows, 1)}
    for ax, m in zip(axs, C.MANIFOLDS):
        sc = ax.tricontourf(xy[:, 0], xy[:, 1], temps[m], levels=30, vmin=vmin, vmax=vmax, cmap="inferno")
        d = C.CHIP_MM / C.N_CELL
        for k in range(1, C.N_CELL):
            ax.axhline(k * d, color="w", lw=0.3, alpha=.4); ax.axvline(k * d, color="w", lw=0.3, alpha=.4)
        ax.set_title(f"{rank[m]}위 {m}  Tmax {temps[m].max():.1f}°C")
        ax.set_aspect("equal"); ax.set_xlabel("x [mm]")
    axs[0].set_ylabel("y [mm]")
    fig.colorbar(sc, ax=axs, shrink=0.8, label="T [°C]")
    fig.suptitle(f"chip temperature @ {flow:.0f} mL/min (superposition)")
    fig.savefig(path, dpi=130); plt.close(fig)
