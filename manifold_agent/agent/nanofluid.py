"""나노유체 물성 + 물 결과 보정 (근사).

물성식
  밀도   ρ_nf = (1-φ)ρ_f + φρ_p                       (혼합법칙, Pak & Cho)
  비열   (ρc)_nf = (1-φ)(ρc)_f + φ(ρc)_p              (Xuan & Roetzel)
  열전도 Maxwell: k_nf = k_f (k_p+2k_f-2φ(k_f-k_p)) / (k_p+2k_f+φ(k_f-k_p))
  점도   Brinkman: μ_nf = μ_f / (1-φ)^2.5

보정 (SimScale은 물로만 돌렸다는 전제)
  - 압력강하: 층류 → Δp ∝ μ  →  Δp_nf = Δp_w · μ_nf/μ_w
  - 온도상승: 층류 완전발달 Nu≈일정 → h ∝ k.
    물 결과에서 대류 비율을 알 수 없으므로 범위로 제시:
      최선(전부 대류 저항)  ΔT_nf = ΔT_w · k_w/k_nf
      최악(변화 없음)        ΔT_nf = ΔT_w
    → 근사치. 정확한 값은 나노유체 물성으로 SimScale을 몇 개 돌려 확인해야 한다.
"""
from __future__ import annotations

WATER = {"rho": 997.0, "cp": 4180.0, "k": 0.607, "mu": 8.9e-4}
PARTICLES = {
    "Al2O3": {"rho": 3970.0, "cp": 765.0, "k": 40.0},
    "CuO":   {"rho": 6500.0, "cp": 535.6, "k": 20.0},
    "TiO2":  {"rho": 4250.0, "cp": 686.2, "k": 8.95},
    "Cu":    {"rho": 8933.0, "cp": 385.0, "k": 401.0},
}


def properties(particle: str, phi: float, base=WATER):
    if not 0 <= phi <= 0.06:
        raise ValueError("부피분율 φ는 0~0.06(6%) 범위만 지원 (상관식 유효범위)")
    p = PARTICLES[particle]; f = base
    rho = (1 - phi) * f["rho"] + phi * p["rho"]
    rhocp = (1 - phi) * f["rho"] * f["cp"] + phi * p["rho"] * p["cp"]
    k = f["k"] * (p["k"] + 2 * f["k"] - 2 * phi * (f["k"] - p["k"])) / (p["k"] + 2 * f["k"] + phi * (f["k"] - p["k"]))
    mu = f["mu"] / (1 - phi) ** 2.5
    return {"rho": rho, "cp": rhocp / rho, "k": k, "mu": mu}


def correction(particle: str, phi: float):
    nf = properties(particle, phi)
    return {
        "props": nf,
        "dT_factor_best": WATER["k"] / nf["k"],   # 온도상승 배율 하한
        "dT_factor_worst": 1.0,                    # 온도상승 배율 상한
        "dp_factor": nf["mu"] / WATER["mu"],
    }
