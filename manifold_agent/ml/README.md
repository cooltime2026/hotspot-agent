# ml/ — 사진 → 데이터 → 머신러닝

## 흐름
```
사용자 캡처 ─(Claude가 색상바 숫자 읽음)─> ml/intake.py run      ─> data/direct_runs.csv
           └(채널 단면 사진, 코드가 색 읽음)> ml/intake.py section  ─> data/section_catalog.csv
                                                 flowdigit/run_all.py ─> data/flow_distribution_from_images.csv
ml/dataset.py ─> data/ml/thermal.csv, data/ml/flow.csv   (머신러닝용 표)
ml/train.py validate / fit / predict
```
- 숫자(최고온도, 압력 최대·최소, 속도 색상바 최댓값)는 **Claude가 사진을 보고 읽음**. 이 환경에 글자 인식(OCR)이 없음.
- 채널 22개 유속은 **코드가 색으로 읽음**(`flowdigit/digitize.py`).

## Run 1개에 필요한 사진
1. 바닥 온도 그림 + 온도 색상바 (최댓값 숫자 보이게)
2. 압력 그림 + 압력 색상바 (최대·최소 숫자) → 유속 판별에도 씀
3. (유량분배용) 채널 단면 Velocity Magnitude + 속도 색상바 (최댓값 숫자). 절단면 y도 알려주기.
4. 핫스팟 위치를 알 수 있는 설정 화면 (어느 두 칸인지)

## 명령
```
python ml/intake.py image 새사진.png           # images/에 번호 붙여 등록, 중복 검사
python ml/intake.py run --design M0 --hotspot 1_1,1_2 --tmax 150 --pmax 900 --pmin -50 --v 0.497 --img 208,209
python ml/intake.py section --img 210 --design M0 --v 0.497 --vmax 0.72 --cut-y 6.0
python ml/intake.py check
python flowdigit/run_all.py
python ml/dataset.py
python ml/train.py validate
python ml/train.py fit
python ml/train.py predict --design D0 --hotspot 2_2,3_2 --Q 50
```

## 현재 검증 결과 (40 Run: D0 35, D1 5)
- 압력 aQ+bQ²: 유량 하나 빼고 맞히기 최대 오차 D0 2.2%, D1 1.3%.
- 온도, 이미 돌린 핫스팟의 다른 유량(경향식): 평균 1.7 ℃, 최대 8.0 ℃(양 끝 유량 외삽).
- 온도, **안 돌린 핫스팟 위치**(D0 7곳 중 하나씩 빼기, GP): 평균 12.7 ℃ (기준선 28.8 ℃).
  가장자리 1_4+2_4는 42 ℃ 틀림(바깥으로 늘려 맞히는 경우). GP가 말한 95% 범위가 실제를 담은 비율 69% → 범위를 과신함.
  → 위치 예측을 믿으려면 핫스팟 위치가 더 필요. '한 칸씩 가열' 16 Run이 가장 효율적.
- 다른 형상 예측: 불가(학습한 형상 D0, D1뿐).

## 핫스팟별 최적 매니폴드 (`ml/optimize.py`)
```
python ml/optimize.py coverage                     # 핫스팟 × 형상: 몇 유량 돌았는지
python ml/optimize.py best --hotspot 3_4,4_4 --tlimit 100 --pump 2
python ml/optimize.py all                          # → data/ml/best_by_hotspot.csv, design_curves.csv
```
- 기준 ① 같은 유량 최저 온도 ② 같은 펌프 동력(Δp·Q) 최저 온도 ③ 목표 온도를 최소 펌프 동력으로(최적 유량 포함).
- **같은 핫스팟을 여러 형상에서 돌려야 비교 가능.** thermal.csv에 P_total_W, R_th_K_W, W_pump_mW 열 추가.

## 두 채팅 데이터 합치기
```
python ml/merge.py ../다른쪽/manifold_agent --dry-run   # 미리 보기
python ml/merge.py ../다른쪽/manifold_agent
python flowdigit/run_all.py && python ml/dataset.py && python ml/intake.py check
```

## 업데이트 (M0 완료 후, 62 Run)
- 형상 전용 GP: 안 돌린 핫스팟 위치 빼기 검증 평균 오차 D0 10.1 ℃, M0 4.1 ℃ (공용 GP는 D0 19.5 ℃). `train.py validate` 시험 C.
- 수평 단면 속도 읽기: `flowdigit/planview.py`, 관성 요약: `ml/inertia.py`.

## 핫스팟 자동 판별
`python ml/find_hotspot.py <사진번호> <Tmax> [<사진번호> <Tmax> ...]` — 바닥 온도 사진만으로 핫스팟 두 칸 추정(시험 91%, 확신 높음일 때 97%).
