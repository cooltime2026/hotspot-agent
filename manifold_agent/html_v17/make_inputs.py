"""cmp.js 입력 만들기: strip_masks.json (띠 가족 마스크, HTML 규칙 입구망=1), runs.json (비교할 SimScale Run)
  python html_v17/make_inputs.py   (manifold_agent 폴더에서)"""
import json, sys, numpy as np, pandas as pd
sys.path.insert(0, '.')
from geometry import param_manifold as PM
out = {}
for n in [f'{a}{i}' for a in 'AB' for i in range(1, 9)] + ['C1', 'C2', 'C3', 'C4']:
    p = json.load(open(f'out/step_param_v3/{n}.json'))['params']
    P, U, ok, _ = PM.masks({k: p[k] for k in ['n', 'yf', 's', 'xf', 'b', 'wf']})
    sw = lambda A: np.where(A == 1, 2, np.where(A == 2, 1, A))
    out[n] = dict(P=sw(P).reshape(-1).tolist(), U=sw(U).reshape(-1).tolist())
json.dump(out, open('html_v17/strip_masks.json', 'w'))
d = pd.read_csv('data/direct_runs.csv'); d['hs'] = d.heat.str.extract(r'at ([0-9_,]+)')[0].str.replace(',', '+')
d = d[d.design.isin(['M0', 'M1', 'M3', 'M4', 'D0', 'D1']) | (d.design.str[0].isin(['A', 'B', 'C']) & (d.inlet_velocity_m_s == 0.912))]
d[['design', 'hs', 'total_flow_mL_min', 'Tmax_bottom_C', 'p_max_Pa', 'p_min_Pa']].to_json('html_v17/runs.json', orient='values')
