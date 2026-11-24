// 자동 최적 매니폴드 — 계산 핵심 (Python ml/family_model.py v2b · geometry/param_manifold.py 와 같은 식)
const CORE = (() => {
  const T_IN = 20;
  const YA = 1.7, YB = 10.3, XP0 = 1.6, XP1 = 10.4, WMIN = 0.35, GMIN = 0.2, RES = 0.1, N = 120;

  function parseCells(cells) { return cells.slice().sort().map(c => c.split('_').map(Number)); }

  function hsPos(cells) {           // family_model.hs_pos
    const cs = parseCells(cells);
    const ys = cs.map(([r]) => (r - 0.5) * 3), xs = cs.map(([, c]) => (c - 0.5) * 3);
    const edgeY = Math.min(...ys.map(y => Math.min(y, 12 - y))) / 12;
    const xc = xs.reduce((a, b) => a + b, 0) / xs.length / 12;
    const vert = cs.length > 1 && cs[0][1] === cs[1][1] ? 1 : 0;
    return [edgeY, xc, vert, edgeY * xc];
  }

  function features(H, Q, logG, wf, dy) {   // family_model.simple_X
    const lq = Math.log(Q / 55);
    return [...H, lq, ...H.map(h => h * lq), logG, wf, dy, ...H.map(h => h * logG)];
  }

  function kindOf(cells, M) {
    const cs = parseCells(cells);
    const key = cells.slice().sort().join('+');
    const adj = cs.length === 2 && Math.abs(cs[0][0] - cs[1][0]) + Math.abs(cs[0][1] - cs[1][1]) === 1;
    const seen = M.seenSet.has(key);
    const edge = cs.every(([r]) => r === 1) || cs.every(([r]) => r === 4);
    if (adj && seen) return { kind: 'seen', label: '실제로 돌려본 위치', err: '±4 ℃ 정도', sig: M.sig_seen, edge: edge && cs.length === 2 };
    if (adj) return { kind: 'adj', label: '이웃 2칸, 안 돌려본 위치', err: '±5 ℃ 정도', sig: M.sig_unseen, edge: edge && cs.length === 2 };
    return { kind: 'out', label: '1칸 또는 떨어진 2칸 (학습 밖)', err: '믿기 어려움', sig: M.sig_unseen * 2, edge: false };
  }

  // cells: ['2_2','3_2'], target ℃, flow: null(자동) 또는 숫자
  function design(M, cells, target, flow) {
    const H = hsPos(cells);
    const hy = parseCells(cells).reduce((a, [r]) => a + (r - 0.5) * 3, 0) / cells.length;
    const k = kindOf(cells, M);
    const flows = flow ? [flow] : Array.from({ length: 46 }, (_, i) => 55 + i);
    const C = M.cand, coef = M.coef, b0 = M.intercept;
    let best = null;
    for (let i = 0; i < C.length; i++) {
      const [n, yf, s, xf, b, wf, seff, logG, dp55] = C[i];
      const dy = Math.abs(hy - yf) / 12 * Math.min(seff, 1);
      for (const Q of flows) {
        const x = features(H, Q, logG, wf, dy);
        let m = b0; for (let j = 0; j < x.length; j++) m += coef[j] * x[j];
        const T = T_IN + Math.exp(m), Thi = T_IN + Math.exp(m + k.sig);
        const dp = dp55 * Math.pow(Q / 55, M.p_m), W = dp * Q / 60e6 * 1e3;
        const ok = Thi <= target;
        const key = ok ? [0, W, 0] : [1, Thi, W];
        if (!best || key[0] < best.key[0] || (key[0] === best.key[0] && (key[1] < best.key[1] || (key[1] === best.key[1] && key[2] < best.key[2]))))
          best = { key, i, Q, T, Thi, dp, W, ok };
      }
    }
    const c = C[best.i];
    return { ...best, p: { n: c[0], yf: c[1], s: c[2], xf: c[3], b: c[4], wf: c[5], s_eff: c[6] }, v: best.Q / 55 * 0.912, k };
  }

  // ── 그림용: param_manifold.band_layout / squeeze / masks (s 대신 s_eff 사용)
  function bandLayout(p) {
    const n = p.n | 1, NY = 2001, y = new Float64Array(NY), cdf = new Float64Array(NY);
    for (let i = 0; i < NY; i++) y[i] = YA + (YB - YA) * i / (NY - 1);
    const rho = y.map(v => 1 + 4 * p.s_eff * Math.exp(-((v - p.yf) ** 2) / (2 * 1.3 ** 2)));
    for (let i = 1; i < NY; i++) cdf[i] = cdf[i - 1] + (rho[i] + rho[i - 1]) / 2 * (y[i] - y[i - 1]);
    const tot = cdf[NY - 1]; for (let i = 0; i < NY; i++) cdf[i] /= tot;
    const edges = [];
    for (let k = 0; k <= n; k++) {
      const t = k / n; let j = 0; while (j < NY - 2 && cdf[j + 1] < t) j++;
      const a = cdf[j], bb = cdf[j + 1]; edges.push(bb > a ? y[j] + (y[j + 1] - y[j]) * (t - a) / (bb - a) : y[j]);
    }
    const centers = [], width = [], pitch = [];
    for (let k = 0; k < n; k++) {
      const pt = edges[k + 1] - edges[k]; centers.push((edges[k + 1] + edges[k]) / 2); pitch.push(pt);
      width.push(Math.min(Math.max(p.wf * pt, WMIN), pt - GMIN));
    }
    return { centers, width, pitch };
  }

  function squeeze(p, x, L) {
    const w = Math.min(1, Math.abs(x - p.xf) / 4.4);
    let f = 1 - p.b * w / 4.3;
    if (f > 1) {
      let k = 0; for (let i = 1; i < L.centers.length; i++) if (Math.abs(L.centers[i] - 6) > Math.abs(L.centers[k] - 6)) k = i;
      f = Math.min(f, (4.3 - L.width[k] / 2) / Math.max(Math.abs(L.centers[k] - 6), 1e-6));
    }
    return f;
  }

  function mask(p) {   // 관통층 P: Uint8Array(N*N), [iy*N+ix], 1 = A망(출구), 2 = B망(입구)
    const L = bandLayout(p), P = new Uint8Array(N * N);
    for (let ix = 0; ix < N; ix++) {
      const x = (ix + 0.5) * RES; if (x < XP0 || x > XP1) continue;
      const f = squeeze(p, x, L);
      L.centers.forEach((c, k) => {
        const w = L.width[k] * f;
        const yc = Math.min(Math.max(6 + (c - 6) * f, 1.7 + w / 2), 10.3 - w / 2);
        const i0 = Math.round((yc - w / 2) / RES), i1 = Math.round((yc + w / 2) / RES);
        for (let iy = i0; iy < i1; iy++) P[iy * N + ix] = k % 2 === 0 ? 1 : 2;
      });
    }
    return P;
  }

  function prepare(M) { M.seenSet = new Set(M.seen); return M; }
  return { design, mask, bandLayout, hsPos, kindOf, prepare, N, RES };
})();
if (typeof module !== 'undefined') module.exports = CORE;
