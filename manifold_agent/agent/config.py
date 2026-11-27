"""공통 설정. SimScale 조건과 반드시 일치시킬 것."""
MANIFOLDS = ["M0", "M1", "M3", "M4", "M5", "D0", "D1", "D2", "D4", "D5", "D6"]
MANIFOLD_KO = {"M0": "매니폴드 없음", "M1": "중앙 집중 빗살형", "M3": "V자 빗살형", "M4": "핫스팟 직상부 공급형",
               "M5": "파도형 빗살", "D0": "이중 바람개비형", "D1": "말굽형", "D2": "엇갈린 막대형",
               "D4": "흡입 바람개비형", "D5": "말굽 완충형", "D6": "가로 빗살형"}
FLOWS_MLMIN = [30, 40, 55, 75, 100]      # SimScale에서 돌린 유량 5수준
FLOW_MIN, FLOW_MAX = min(FLOWS_MLMIN), max(FLOWS_MLMIN)
N_CELL = 4                                # 칩 4x4 = 16칸
Q0_WCM2 = 100.0                           # SimScale에서 한 칸에 준 단위 열유속 [W/cm^2]
T_IN_C = 20.0                             # 입구온도 [°C]
CHIP_MM = 12.0                            # 판 한 변 [mm] (HTML 에이전트와 동일)
