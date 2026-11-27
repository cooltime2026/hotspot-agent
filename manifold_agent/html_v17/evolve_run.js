// 페이지(hotspot_agent_v17_ml.html)를 브라우저에서 열고 핫스팟마다 '머신러닝 새 설계'(1위)를 꺼낸다.
//   node html_v17/evolve_run.js out.json 1_3+1_4 2_2+3_2 ...      (manifold_agent 에서 실행)
// 유량 55 mL/min(0.912 m/s), 핫스팟 = 3×3 mm 칸 300 W/cm², 나머지 50 W/cm² (SimScale 설정과 같음).
// 결과: 핫스팟마다 {hotspot, name, evo:{fam,cnt,head,m,g:{cav,gro(RLE 240×240), pin, pout}}, mlT, simpleT, simpleDp, top5}
const {chromium} = require('playwright');
const fs = require('fs'), path = require('path');
(async () => {
  const [out, ...hss] = process.argv.slice(2);
  const file = 'file://' + path.resolve(__dirname, 'hotspot_agent_v17_ml.html');
  const browser = await chromium.launch();
  const res = fs.existsSync(out) ? JSON.parse(fs.readFileSync(out, 'utf8')) : {};
  for (const hs of hss) {
    const page = await browser.newPage();
    page.on('pageerror', e => console.log('  페이지 오류', hs, String(e).slice(0, 200)));
    await page.goto(file);
    await page.waitForFunction(() => typeof S !== 'undefined' && typeof schedule === 'function');
    const t0 = Date.now();
    await page.evaluate(hs => {
      S.hs = hs.split('+').map(c => { const [r, k] = c.split('_').map(Number); return {x: (k - .5) * 3, y: (r - .5) * 3, lx: 3, ly: 3, q: 300}; });
      S.Q = 55; S.q0 = 50; schedule();
    }, hs);
    try {
      await page.waitForFunction(() => AUTO && AUTO.mlopt !== undefined && AUTO.cands && AUTO.cands.some(c => c.ml === 1 && c.r), null, {timeout: 900000, polling: 2000});
    } catch (e) { console.log('  시간 초과', hs); await page.close(); continue; }
    const r = await page.evaluate(() => {
      const rle = a => { const o = []; let i = 0; while (i < a.length) { let j = i; while (j < a.length && a[j] === a[i]) j++; o.push(a[i], j - i); i = j; } return o; };
      const ev = AUTO.mlopt && AUTO.mlopt.evo, first = AUTO.cands.find(c => c.ml === 1);
      const top = AUTO.cands.filter(c => c.ml).sort((a, b) => a.ml - b.ml).map(c => ({ml: c.ml, name: c.name, mlT: isFinite(c.mls) ? 20 + Math.exp(c.mls) : null, meas: c.meas, simpleT: c.r && c.r.Tmax, simpleDp: c.r && c.r.dp}));
      return {name: first && first.name, isNew: !!(first && /머신러닝 새 설계/.test(first.base)),
        evo: ev ? {fam: ev.fam, from: ev.from, cnt: ev.cnt, head: ev.head, m: ev.m, mlT: 20 + Math.exp(ev.m),
                   g: {cav: rle(ev.g.cav), gro: rle(ev.g.gro), pin: ev.g.pin, pout: ev.g.pout}} : null,
        simpleT: first && first.r && first.r.Tmax, simpleDp: first && first.r && first.r.dp, top5: top, dbg: window.ML_DBG && {starts: ML_DBG.starts, solves: ML_DBG.solves}};
    });
    r.hotspot = hs; r.sec = Math.round((Date.now() - t0) / 1000);
    res[hs] = r; fs.writeFileSync(out, JSON.stringify(res));
    console.log(hs, r.sec + 's', r.isNew ? '새 설계' : '새 설계 없음', r.evo ? `${r.evo.fam} 예측 ${r.evo.mlT.toFixed(1)}℃` : '', r.name);
    await page.close();
  }
  await browser.close();
})();
