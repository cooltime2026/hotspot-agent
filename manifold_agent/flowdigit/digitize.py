"""SimScale 캡처(채널 단면 + Velocity Magnitude 색상)에서 채널 22개의 평균 유속을 읽는다.

순서
 1) 속도 색상바(무지개색) 찾기 → 색 → 값(0~vmax) 대응표
 2) 단면에서 속도 색 픽셀(무지개색에 가깝고 온도 색상표보다 가까운 것) 찾기
 3) 연결 덩어리 중 채널 크기·모양의 덩어리를 골라, 한 줄로 늘어선 22개 배열에 맞춤(원근 반영 2차식)
 4) 채널마다 예상 위치의 안쪽 상자에서 평균 유속 계산 (매니폴드와 붙은 채널도 채널 부분만 읽음)
"""
from __future__ import annotations
from collections import deque
import numpy as np
from PIL import Image

N_CH = 22


def _runs(mask_row):
    xs = np.where(mask_row)[0]
    if len(xs) == 0:
        return []
    out, s = [], xs[0]
    for a, b in zip(xs[:-1], xs[1:]):
        if b != a + 1:
            out.append((s, a)); s = b
    out.append((s, xs[-1]))
    return out


def find_colorbars(im, min_rows=10):
    """화면 아래쪽 긴 채색 막대들: [(y_mid, x0, x1, kind)] kind='rainbow'|'thermal'"""
    H, W, _ = im.shape
    sat = im.max(2) - im.min(2)
    rows = {}
    for y in range(int(H * 0.45), H):
        for x0, x1 in _runs(sat[y] > 70):
            if x1 - x0 > 120:
                rows.setdefault((x0 // 6, x1 // 6), []).append((y, x0, x1))
    bars = []
    # 색상바는 높이가 있음 (판 테두리 같은 얇은 선 제외, D0·D1 채팅 수정: 단면 사진 23·29·37).
    # 단, 온도·수평 단면 그림(tempmap/planview/chantemp)은 색상바가 얇게 찍힌 사진이 많아 min_rows=1 로 예전 방식 사용.
    for lst in [l for l in rows.values() if len(l) >= 4 and len(set(r[0] for r in l)) >= min_rows]:
        ys = [r[0] for r in lst]; mid = lst[len(lst) // 2]
        y, x0, x1 = mid
        # 끝 표시(삼각형) 피하려고 안쪽 2px
        seg = im[y, x0 + 2:x1 - 1]
        first = seg[:4].mean(0)
        kind = "rainbow" if (first[2] > 150 and first[0] < 90) else "thermal"
        bars.append((y, x0 + 2, x1 - 1, kind, min(ys), max(ys)))
    # 같은 막대 중복 제거
    bars.sort()
    out = []
    for b in bars:
        if out and abs(out[-1][0] - b[0]) < 6 and abs(out[-1][1] - b[1]) < 10:
            continue
        out.append(b)
    return out


def lut_from_bar(im, bar):
    y, x0, x1 = bar[0], bar[1], bar[2]
    cols = im[bar[4]:bar[5] + 1, x0:x1 + 1].mean(0)   # 막대 높이 평균
    return cols  # 왼쪽(0) → 오른쪽(vmax)


def components(mask, min_n=8, max_n=5000):
    H, W = mask.shape
    lab = np.zeros(mask.shape, np.int32); comps = []; n = 0
    for y, x in zip(*np.nonzero(mask)):
        if lab[y, x]:
            continue
        n += 1; q = deque([(y, x)]); lab[y, x] = n; pts = []
        while q:
            a, b = q.popleft(); pts.append((a, b))
            for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                c, d = a + da, b + db
                if 0 <= c < H and 0 <= d < W and mask[c, d] and not lab[c, d]:
                    lab[c, d] = n; q.append((c, d))
        if min_n <= len(pts) <= max_n:
            comps.append(np.array(pts))
    return comps


def digitize(path, vmax, debug_png=None):
    im = np.array(Image.open(path).convert("RGB")).astype(float)
    H, W, _ = im.shape
    bars = find_colorbars(im)
    vb = [b for b in bars if b[3] == "rainbow"]
    if not vb:
        raise RuntimeError("속도 색상바를 못 찾음")
    vbar = vb[-1] if len(vb) > 1 else vb[0]
    vl = lut_from_bar(im, vbar)
    # 색상(hue) 기반: 반투명 단면이 회색과 섞여도 hue는 유지됨
    def hue(c):
        c = np.asarray(c, float); mx = c.max(-1); mn = c.min(-1); d = np.maximum(mx - mn, 1e-6)
        r, g, b = c[..., 0], c[..., 1], c[..., 2]
        h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
        return h, (mx - mn) / np.maximum(mx, 1e-6)
    hb, _ = hue(vl)
    hb = np.where(hb > 300, hb - 360, hb)            # 빨강 근처 연속
    frac = (np.arange(len(vl)) + 0.5) / len(vl)
    # 색상바는 띠(band)로 끊겨 있음 → 같은 색 띠마다 중앙 위치를 값으로
    hq = np.round(hb).astype(int)
    bands = []
    i0 = 0
    for i in range(1, len(hq) + 1):
        if i == len(hq) or abs(hq[i] - hq[i0]) > 2:
            if i - i0 >= 3:                          # 띠 경계의 1~2px 섞인 색은 버림
                bands.append((hb[i0:i].mean(), frac[i0:i].mean()))
            i0 = i
    nband = len(bands)
    bh = np.array([b[0] for b in bands]); bf = np.array([b[1] for b in bands])
    o = np.argsort(-bh); hs_u = -bh[o]; fs_band = bf[o]
    hp, sp = hue(im)
    hp = np.where(hp > 300, hp - 360, hp)
    # 가장 가까운 띠의 중앙값
    kk = np.abs(hp[..., None] - bh[None, None, :]).argmin(-1)
    val = bf[kk] * vmax
    isvel = (sp > 0.45) & (hp >= -10) & (hp <= 250) & ((im.max(2) - im.min(2)) > 50)
    isvel_strict = isvel & (hp >= 75)                # 파랑~초록: 온도 색상표에 없는 색 → 채널 찾기용
    # 색상바 영역 제외
    for b in bars:
        isvel[max(0, b[4] - 30):b[5] + 25, max(0, b[1] - 40):b[2] + 40] = False
    for b in bars:
        isvel_strict[max(0, b[4] - 30):b[5] + 25, max(0, b[1] - 40):b[2] + 40] = False
    comps = components(isvel_strict)
    # 채널 후보: 세로로 길쭉하거나 정사각에 가까운 작은 덩어리
    cand = []
    for p in comps:
        h = np.ptp(p[:, 0]) + 1; w = np.ptp(p[:, 1]) + 1
        if 4 <= w <= 60 and 4 <= h <= 90 and 0.5 <= h / w <= 5 and len(p) >= 0.45 * h * w:
            cand.append(dict(cy=p[:, 0].mean(), cx=p[:, 1].mean(), h=h, w=w, n=len(p), pts=p))
    if len(cand) < 6:
        raise RuntimeError(f"채널 후보 부족 ({len(cand)})")
    # 크기 비슷한 것끼리 (중앙값 ±50%)
    mh = np.median([c["h"] for c in cand]); mw = np.median([c["w"] for c in cand])
    cand = [c for c in cand if 0.5 * mh <= c["h"] <= 1.6 * mh and 0.5 * mw <= c["w"] <= 1.6 * mw]
    # 한 줄 맞추기: cy = a + b*cx + c*cx^2 (RANSAC 단순형)
    xs = np.array([c["cx"] for c in cand]); ys = np.array([c["cy"] for c in cand])
    best = None
    rng = np.random.default_rng(0)
    for _ in range(400):
        idx = rng.choice(len(cand), 3, replace=False)
        try:
            co = np.polyfit(xs[idx], ys[idx], 2)
        except Exception:
            continue
        res = np.abs(np.polyval(co, xs) - ys)
        inl = res < 0.35 * mh
        if best is None or inl.sum() > best[0]:
            best = (inl.sum(), inl)
    keep = [c for c, k in zip(cand, best[1]) if k]
    keep.sort(key=lambda c: c["cx"])
    # 간격으로 채널 번호 부여
    cx = np.array([c["cx"] for c in keep])
    gaps = np.diff(cx); pitch = np.median(gaps[gaps > 0.5 * np.median(gaps)]) if len(gaps) else 1
    idx = np.round((cx - cx[0]) / pitch).astype(int)
    # 원근으로 간격이 서서히 변함 → 번호를 다시 다듬기 (2차 맞춤 반복)
    for _ in range(3):
        if len(set(idx)) < 4:
            break
        cfx = np.polyfit(idx, cx, 2)
        pred = np.polyval(cfx, np.arange(idx.max() + 3))
        idx = np.array([int(np.argmin(np.abs(pred - x))) for x in cx])
    span = idx.max() - idx.min() + 1
    offset = idx.min()
    idx = idx - offset
    # 22개가 아닌 경우: 끝 채널이 안 보이는 경우 등 → 품질 경고
    cyv = np.array([c["cy"] for c in keep]); cfy = np.polyfit(cx, cyv, 2)
    cfx = np.polyfit(idx, cx, 2 if len(set(idx)) > 3 else 1)
    hh = np.median([c["h"] for c in keep]); ww = np.median([c["w"] for c in keep])
    res = []
    for j in range(N_CH):
        x = np.polyval(cfx, j); y = np.polyval(cfy, x)
        ys0, ys1 = int(round(y - 0.3 * hh)), int(round(y + 0.3 * hh))
        xs0, xs1 = int(round(x - 0.3 * ww)), int(round(x + 0.3 * ww))
        if xs0 < 0 or xs1 >= W or ys0 < 0 or ys1 >= H:
            res.append(dict(j=j, v=np.nan, npx=0, frac=0)); continue
        box = isvel[ys0:ys1 + 1, xs0:xs1 + 1]; vv = val[ys0:ys1 + 1, xs0:xs1 + 1][box]
        # 단면 전체(테두리 포함) 평균 = 유량/면적의 추정값
        Y0, Y1 = int(round(y - 0.5 * hh - 1)), int(round(y + 0.5 * hh + 1))
        X0, X1 = int(round(x - 0.5 * ww - 1)), int(round(x + 0.5 * ww + 1))
        fb = isvel[Y0:Y1 + 1, X0:X1 + 1]; fv = val[Y0:Y1 + 1, X0:X1 + 1][fb]
        res.append(dict(j=j, v=float(np.mean(fv)) if len(fv) else np.nan, v_center=float(np.mean(vv)) if len(vv) else np.nan,
                        vstd=float(np.std(fv)) if len(fv) else np.nan,
                        npx=int(fb.sum()), frac=float(box.mean()), x=float(x), y=float(y)))
    info = dict(n_detected=len(keep), span=int(span), pitch_px=float(pitch), ch_h_px=float(hh), ch_w_px=float(ww),
                band_mps=vmax / max(nband, 1), n_bands=nband, bar=vbar[:3])
    if debug_png:
        from PIL import ImageDraw
        img = Image.open(path).convert("RGB"); dr = ImageDraw.Draw(img)
        for r in res:
            if "x" in r:
                dr.rectangle([r["x"] - 0.3 * ww, r["y"] - 0.3 * hh, r["x"] + 0.3 * ww, r["y"] + 0.3 * hh], outline=(255, 0, 255))
                dr.text((r["x"] - 4, r["y"] + 0.6 * hh), str(r["j"]), fill=(0, 0, 0))
        for c in keep:
            dr.point((c["cx"], c["cy"]), fill=(0, 0, 0))
        img.save(debug_png)
    return res, info
