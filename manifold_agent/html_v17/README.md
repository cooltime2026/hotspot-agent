# HTML v17 계산식 ↔ SimScale 비교 (2026-11-27)

- `hotspot_agent_v17.html`: 사용자가 준 원본 (수정 안 함).
- `./extract.sh` → `node cmp.js` : HTML 의 간이 계산(evaluate + flowSolve, 코드 그대로)을 Node 에서 돌려 SimScale 187 Run 과 비교.
  (strip_masks.json, runs.json 은 HANDOFF 21-7 의 파이썬 코드로 만듦) 결과: `data/ml/html_v17_vs_simscale.csv`
- 입구 방향은 SimScale 실제 설정(data/design_meta.json)에 맞춤. 띠 가족은 param_manifold.masks() 를 HTML 마스크로(입구망=1).
- 3D NS(16차)는 형상이 고정(채널 0.6~11.4, 층 0.5/0.35)이라 띠 가족(헤더, 0.15/0.4)은 못 풂 → 비교 안 함.
