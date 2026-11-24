# manifold_agent — 머신러닝 데이터

## ★ 웹 설계기 (설치 없이)

`manifold_designer.html` (저장소 맨 위, 또는 `manifold_agent/web/`) 을 브라우저로 열면 핫스팟을 눌러 최적 모양·유량·예상 온도를 바로 봄. STEP 은 페이지의 문장을 Claude 에게 보내거나 아래 명령으로.

## ★ 자동 최적 설계 (명령 하나)

```bash
cd manifold_agent
python ml/design.py 2_2,3_2 --target 85
```

- 핫스팟(칸 이름 r_c, SimScale 바닥 BOTTOM 시점 기준)과 목표 최고온도를 넣으면
  최적 띠형 매니폴드 모양 **STEP**, **최적 유량**, 예상 최고온도·압력·펌프 동력, 그림이 `out/design/` 에 나옴 (약 30~50초).
- 유량을 정하고 싶으면 `--flow 75` (mL/min), STEP 없이 숫자만 보려면 `--nostep`.
- 예측 오차: 돌려본 이웃 2칸 핫스팟 약 ±4 ℃. 1칸·떨어진 2칸은 학습 밖.


핫스팟 → 띠형 매니폴드 자동설계용 SimScale 결과와 학습 코드. 자세한 내용은 `HANDOFF.md` (20장부터).

- `data/direct_runs.csv` — 226개 Run (형상, 유속, 핫스팟, 최고온도, 압력)
- `data/ml/*.csv` — 학습용 표 (thermal.csv 등), `data/runs_log.md` — Run마다 기록
- `ml/` — 처리·학습 스크립트 (`intake.py check`, `family_model.py` 등), `*.pkl` 이전 모델
- `geometry/` — 숫자 6개 띠형 매니폴드 가족 (`param_manifold.py`), STEP 생성
- `out/step_param_v3/*.json` — A1~A8·B1~B8·C1~C4 모양 변수
- `out/auto_design_all/` — 136가지 핫스팟 자동설계 결과 (SUMMARY_adjacent.md 부터 보기)
- `out/auto_design/<핫스팟>/` — 핫스팟 8개 제안 3개씩 (STEP은 *_step.zip)
- `out/step_local/` — 새 모양 가족 L (국소 개방) L1~L4, STEP은 L1-L4_step.zip

들어 있지 않음(크기): 캡처 사진 `images/`(165 MB), STEP 파일(106 MB), 사용자 Word 문서.
필요 패키지: `pip install numpy pandas scikit-learn matplotlib pillow scipy cadquery shapely`
