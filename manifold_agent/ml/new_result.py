"""SimScale 결과 하나를 넣으면 끝까지 한 번에: 사진 등록 → Run 등록 → 칸 온도 읽기 → 점검 → 예측과 비교 → 재학습 → 웹(HTML) 갱신.

  python ml/new_result.py --design S4 --hotspot 1_3,1_4 --tmax 101.2 --pmax 3500 --pmin -700 \\
         --inlet "user (0.95,3.55)+(0.95,7.45)" --photos 바닥.png 채널층.png 압력.png
  (사진이 대화에 파일로 안 왔으면 --photos 빼기 → 숫자만 등록, 칸 온도 없음)
  --v 기본 0.912. 사진 순서: 바닥 온도, 채널층 온도, 윗면 압력.
끝나면: html_v17/artifact_body.html (아티팩트에 올릴 본문) 이 만들어짐 → Claude 가 아티팩트 갱신·GitHub 푸시.
형상 이름 규칙: A·B·C(띠, out/step_param_v3/<이름>.json) / S*(HTML v17 모양, out/step_v17/<이름>_mask.json) / F*(geometry/split_feed.py F).
"""
from __future__ import annotations
import argparse, json, re, subprocess, sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml")); sys.path.insert(0, str(ROOT))
EX = ROOT / "data" / "extra_photos.json"
PY = sys.executable


def sh(*a):
    r = subprocess.run([PY, *a], cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-2000:], r.stderr[-2000:]); raise SystemExit(f"실패: {' '.join(a)}")
    return r.stdout


def ml_predict(design, hotspot, Q):
    """지금(재학습 전) 칸 모델 + 실측 보정으로 예측 — HTML 의 cellScore + mlCorrect 와 같은 계산"""
    import base64
    import cell_model as CM, select_model as SM, shape_features as SF
    M = json.loads((ROOT / "ml/cell_model.json").read_text()); R = M["resid"]
    cells = [tuple(map(int, c.split("_"))) for c in hotspot.split("+")]
    key = "+".join(sorted(hotspot.split("+")))
    if re.match(r"^F\d", design):
        import f_family as FF
        from geometry import split_feed as SFd
        P, _ = FF.f_masks(SFd.F[design], "top" if all(r == 4 for r, _ in cells) else "bottom")
        s = SF.shape_summary(SF.openings_from_mask(P, 2, 1.5, 10.5)); fam = "F형"; Ph = np.where(P == 2, 1, np.where(P == 1, 2, 0))
    else:
        s = SM.summary_of(design)
        fam = "띠형" if re.match(r"^[ABC]\d", design) else None
        Ph = None
        if re.match(r"^S\d", design):
            m = json.loads((ROOT / f"out/step_v17/{design}_mask.json").read_text())
            Ph = np.array(m["cav"]).reshape(240, 240).reshape(120, 2, 120, 2).max(axis=(1, 3))
            fam = (m.get("base") or "").replace("머신러닝 설계 · ", "").split(" · ")[0].split(" (")[0]
        if design in CM.PRESET_SHAPES:      # 프리셋 D1: 핫스팟마다 실측 보정 (위치 맞춰 비교)
            Ph = CM.preset_mask(design); fam = design
        if re.match(r"^N\d", design):      # 머신러닝 새 설계 (out/new_designs, 페이지 진화와 같은 종류 이름으로 보정)
            m = json.loads((ROOT / f"out/new_designs/{design}_mask.json").read_text())
            Ph = np.array(m["cav"]).reshape(240, 240).reshape(120, 2, 120, 2).max(axis=(1, 3)); fam = m["fam"]
            if m.get("hs"):                 # 아무 배치 핫스팟: 칸마다 발열 몫, 이름표는 발열 큰 두 칸 (페이지 mlCells 와 같음)
                cells, key, _ = CM.hs_weights(m["hs"]); key = "+".join(sorted(key.split("+")))
    rows = pd.DataFrame(CM.cell_rows(s, cells, Q))
    lm = float(np.log(CM.pred_cells({"mu": np.array(M["mu"]), "sd": np.array(M["sd"]), "m": type("L", (), {"predict": lambda self, X: X @ np.array(M["coef"]) + M["intercept"]})()}, rows).max() - 20))
    if fam == "띠형" and Ph is None:
        lm += R["strip_hs"].get(key, R["strip"])
    elif fam and Ph is not None:
        best = (0.0, None)
        for sh_ in R["shapes"]:
            if sh_["fam"] != fam:
                continue
            A = np.frombuffer(base64.b64decode(sh_["P"]), np.uint8).reshape(120, 120)
            w = CM.align_w(Ph, A, sh_["hs"], key)        # 핫스팟 위치를 맞춰 옮긴 뒤 겹침² (2026-11-28)
            if w > best[0]: best = (w, sh_)
        r0 = R["strip_hs"].get(key, R["strip"]) if fam in ("F형", "띠형") else R.get("nohead", 0)
        lm += best[0] * (best[1]["r"] if best[1] else 0) + (1 - best[0]) * r0
    return 20 + np.exp(lm)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--design", required=True); ap.add_argument("--hotspot")
    ap.add_argument("--tmax", type=float, required=True); ap.add_argument("--pmax", type=float, required=True)
    ap.add_argument("--pmin", type=float, required=True); ap.add_argument("--v", type=float, default=0.912)
    ap.add_argument("--inlet", default=""); ap.add_argument("--photos", nargs="*"); ap.add_argument("--note", default="")
    a = ap.parse_args()
    import cell_model as _CM
    _fh = _CM.free_hs(a.design)
    if _fh:      # 아무 배치 설계(ml/design_any.py): 핫스팟은 설계 파일에 있음. 기록용 이름표 = 발열 큰 두 칸, 실제 배치는 note 에
        a.hotspot = ",".join(sorted(_CM.hs_weights(_fh)[1].split("+")))      # 정렬: intake·cellmaps 의 이름표와 같게
        a.note = (a.note + " " if a.note else "") + "아무 배치 핫스팟: " + " + ".join(f"({h['x']:g},{h['y']:g}) {h['lx']:g}x{h['ly']:g} mm {h['q']:g} W/cm2" for h in _fh)
    if not a.hotspot:
        raise SystemExit("--hotspot 필요 (예: 2_1,2_2)")
    hs = a.hotspot.replace(",", "+"); Q = round(a.v / 0.912 * 55.01, 2)
    try:
        pred = ml_predict(a.design, hs, Q)
    except Exception as e:
        pred = None; print("  (사전 예측 못 함:", e, ")")
    imgs = []
    if a.photos:
        before = max(int(p.stem) for p in (ROOT / "images").glob("*.png") if p.stem.isdigit())
        print(sh("ml/intake.py", "image", *a.photos).strip())
        imgs = [before + 1 + i for i in range(len(a.photos))]
    run = ["ml/intake.py", "run", "--design", a.design, "--hotspot", a.hotspot, "--tmax", str(a.tmax), "--pmax", str(a.pmax),
           "--pmin", str(a.pmin), "--v", str(a.v), "--inlet", a.inlet]
    run += ["--img", ",".join(map(str, imgs))] if imgs else ["--note", a.note or "사진 파일 미수신(값만)"]
    print(sh(*run).strip().splitlines()[-1])
    if len(imgs) >= 2:
        ex = json.loads(EX.read_text(encoding="utf-8")) if EX.exists() else {"bottom": [], "cht": []}
        ex["bottom"].append([a.design, hs, a.v, imgs[0]]); ex["cht"].append([a.design, hs, a.v, imgs[1], a.tmax, a.note])
        EX.write_text(json.dumps(ex, ensure_ascii=False, indent=1), encoding="utf-8")
        fh = sh("ml/find_hotspot.py", str(imgs[0]), str(a.tmax)).strip().splitlines()[-1]
        print("  핫스팟 자동 판정:", fh, "(설정:", hs, ")")
    for s_ in ["ml/cellmaps.py", "ml/chantemps.py", "ml/dataset.py"]:
        sh(s_)
    chk = sh("ml/intake.py", "check").strip().splitlines()[-1]; print("  점검:", chk)
    cmp_ = f"예측 {pred:.1f} ℃ → 실측 {a.tmax} ℃ (차이 {a.tmax - pred:+.1f})" if pred else "예측 없음"
    line = f"| {a.design}_hs{hs.replace('_', '').replace('+', '-')}_v{a.v} | {a.tmax} ℃ | {a.pmax:g} Pa | {a.pmin:g} Pa | - | " \
           f"{'사진 ' + ','.join(map(str, imgs)) if imgs else '사진 파일 미수신(값만)'}. 입구 {a.inlet}. ML(칸 모델+보정) {cmp_}. {a.note} |"
    with open(ROOT / "data/runs_log.md", "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print("  머신러닝:", cmp_)
    if re.match(r"^[ABC]\d", a.design):
        sh("ml/family_model.py", "fit")
    print(" ", sh("ml/cell_model.py", "fit", "10").strip().splitlines()[0])
    sh("ml/select_model.py", "fit", "3")
    print(" ", sh("html_v17/patch_ml.py").strip())
    s = (ROOT / "html_v17/hotspot_agent_v17_ml.html").read_text(encoding="utf-8")
    body = s[s.index("<body>") + 6:].lstrip("\n").rstrip()
    if body.endswith("</body></html>"):
        body = body[:-14].rstrip()
    (ROOT / "html_v17/artifact_body.html").write_text(body, encoding="utf-8")
    print("  끝: html_v17/artifact_body.html → 아티팩트 갱신, GitHub 푸시")


if __name__ == "__main__":
    main()
