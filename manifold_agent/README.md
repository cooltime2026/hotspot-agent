# manifold_agent — 머신러닝 데이터

핫스팟 → 띠형 매니폴드 자동설계용 SimScale 결과와 학습 코드. 자세한 내용은 `HANDOFF.md` (20장부터).

- `data/direct_runs.csv` — 226개 Run (형상, 유속, 핫스팟, 최고온도, 압력)
- `data/ml/*.csv` — 학습용 표 (thermal.csv 등), `data/runs_log.md` — Run마다 기록
- `ml/` — 처리·학습 스크립트 (`intake.py check`, `family_model.py` 등), `*.pkl` 이전 모델
- `geometry/` — 숫자 6개 띠형 매니폴드 가족 (`param_manifold.py`), STEP 생성
- `out/step_param_v3/*.json` — A1~A8·B1~B8·C1~C4 모양 변수

들어 있지 않음(크기): 캡처 사진 `images/`(165 MB), STEP 파일(106 MB), 사용자 Word 문서.
필요 패키지: `pip install numpy pandas scikit-learn matplotlib pillow scipy cadquery shapely`
