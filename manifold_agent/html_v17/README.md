# HTML v17 계산식 ↔ SimScale 비교 (2026-11-27)

- `hotspot_agent_v17.html`: 사용자가 준 원본 (수정 안 함).
- `./extract.sh` → `node cmp.js` : HTML 의 간이 계산(evaluate + flowSolve, 코드 그대로)을 Node 에서 돌려 SimScale 187 Run 과 비교.
  (먼저 manifold_agent 에서 `python html_v17/make_inputs.py` → strip_masks.json, runs.json) 결과: `data/ml/html_v17_vs_simscale.csv`
- 입구 방향은 SimScale 실제 설정(data/design_meta.json)에 맞춤. 띠 가족은 param_manifold.masks() 를 HTML 마스크로(입구망=1).
- 3D NS(16차)는 형상이 고정(채널 0.6~11.4, 층 0.5/0.35)이라 띠 가족(헤더, 0.15/0.4)은 못 풂 → 비교 안 함.

## 머신러닝 매니폴드 판: `hotspot_agent_v17_ml.html`
- 만들기: `python html_v17/patch_ml.py` (원본 + 저장소 맨 위 manifold_designer.html 의 ML 코드·모델 숫자)
- 바뀐 것: 자동 최적 매니폴드의 후보 모양(autoSpecs 4+1종) → 머신러닝이 고른 띠 모양 1개. 계산 엔진은 그대로.
- 3D NS 단계는 건너뜀(형상이 헤더 없는 0.5/0.35 로 고정이라 띠 모양을 못 풂).
- 계산식이 '단상 범위 밖' 등으로 유효하지 않다고 해도 머신러닝 모양은 표시(경고는 원래 문구).
- 모델 재학습 후: manifold_designer.html 의 모델 숫자 갱신 → patch_ml.py 다시 실행.
