// 핫스팟마다 '머신러닝 새 설계'를 깊게 찾는다 (2026-11-28). 페이지의 모양 규칙·제작 검사(aCheck)·점수(cellScore+mlCorrect)·유량 계산(flowSolve)을 그대로 씀.
//   node html_v17/evolve_deep.js out/new_designs/deep.json 1_3+1_4 2_2+3_2 ...      (manifold_agent 에서)
// 페이지 mlEvolve 와 다른 점: 출발 모양이 더 많음(v17 종류마다 3개 + 실측 모양 상위 3개 + 띠 3개 + F 1개), 출발마다 2번(다른 난수) × 700번,
//   유량 계산은 quick 이 아니라 정식(flowSolve(...,false)) — quick 은 바람개비형 등에서 수렴을 못 해 좋은 모양을 버렸음.
//   그리고 1위는 '많이 바뀐 것'이 아니라 '점수(예상 온도)가 가장 좋은 새 모양'(실측 모양과 겹침 85 % 미만, 3번 이상 바뀜, 유량 계산 됨).
// 결과: 핫스팟마다 best(1위) + alts(종류가 다른 후보 4개까지) + lib(실측 모양 예상, 2~5위 비교용).
const {chromium} = require('playwright');
const fs = require('fs'), path = require('path');

const DEEP = String.raw`
async function deepDesign(key,Q,iters,hsIn){
  const hs=hsIn||key.split('+').map(c=>{const [r,k]=c.split('_').map(Number);return {x:(k-.5)*3,y:(r-.5)*3,lx:3,ly:3,q:300}});   // hsIn: 아무 배치 [{x,y,lx,ly,q}] (위치·크기·열유속)
  const cells=mlCells(hs),R=(a,b,st)=>{const o=[];for(let v=a;v<=b+1e-9;v+=st)o.push(+v.toFixed(2));return o},mm=m=>m==='full'?'전폭 슬롯':'좌우 여유 '+m+' mm';
  const jobs=[];const add=(fam,name,make)=>jobs.push({fam,name,make});
  for(const gg of [0,1])for(const m of [...R(0,3,.5),'full'])for(const s of R(.4,1.2,.2))add('흡입형','흡입형 · 슬롯 '+s+' mm · '+mm(m)+(gg?' · 가운데 한 줄':''),()=>aSwap(famDirect(hs,s,m,gg)));
  for(const w of R(.4,1.0,.2))for(const pp of R(1.0,3.0,.2))add('V자 빗살형','V자 빗살형 · 빗살 폭 '+w+' mm · 간격 '+pp+' mm',()=>famV(hs,w,pp));
  for(const f of [0,1])add('대역 대향류형','대역 대향류형'+(f?' · 방향 반대':''),()=>famBand(hs,f));
  for(const m of [...R(.5,2.5,.5),'vor'])for(const s of R(.4,1.0,.2))for(const gp of R(-.6,.4,.2))for(const r of [0,1])
    add('바람개비형','바람개비형 · 슬롯 '+s+' mm · '+(m==='vor'?'이웃 핫스팟 중간까지':mm(m))+' · 슬롯 간격 '+gp+' mm'+(r?' · 좌우 반전':''),()=>famPin(hs,m,r,s,gp));
  const libP=[],libH=[],sw=v=>v===1?2:v===2?1:0;
  {const seen=new Set();for(const s of ML_LIB.S){if(s.head){libH.push(mlPool(mlRLE(s.cav,AG*AG)));continue}const k=JSON.stringify(s.cav);if(seen.has(k))continue;seen.add(k);libP.push(mlPool(mlRLE(s.cav,AG*AG)))}}
  for(const p of Object.values(ML_LIB.strip))libH.push(mlMasks(p).P.map(sw));
  for(const p of Object.values(ML_LIB.F))for(const sd of ['bottom','top']){const mk=mlMasksF(p,sd);if(mk)libH.push(mk.P.map(sw))}
  const maxIoU=(P,head)=>{let b=0;for(const L of (head?libH:libP))b=Math.max(b,mlIoU(P,L));return b};
  // 물이 안 흐르는 채널 수(공급→회수 구간이 하나도 없는 채널, 22개 중). DEADMAX 가 있으면 그보다 많은 모양은 버림 (모델이 죽은 칸 온도를 낮게 보는 약점 대비)
  const nDead=(P,head)=>selSummary(P,head?1.5:.6,head?10.5:11.4).segs.filter(x=>!x.length).length,DM=(typeof window.DEADMAX==='number')?window.DEADMAX:99;
  const scoreG=(g,fam)=>{const P=mlPool(g.cav),r=cellScore(SEL_M,P,!!g.head,cells,Q);if(r.out)return null;if(DM<22&&nDead(P,!!g.head)>DM)return null;return {m:mlCorrect(SEL_M,r.m,fam,P,cells).m,P}};
  const res=[];for(const j of jobs){let g=null;try{g=j.make()}catch(e){}if(!g||aCheck(g))continue;const sc=scoreG(g,j.fam);if(sc)res.push({...j,m:sc.m,P:sc.P})}
  res.sort((a,b)=>a.m-b.m);
  const fl=G.fQ?G.fQ(Q):G.f,Qt=Q*1e-6/60,solveOK=(g,head)=>{let s=null;try{s=flowSolve(mlCloneG(g),S.inl,Qt,fl,false)}catch(e){}return !!(s&&isFinite(s.Rl)&&(s.conv||head))};
  const seeds=[],cnt={};
  for(const r of res){if((cnt[r.fam]||0)>=3)continue;if(maxIoU(r.P,false)>=.85)continue;const g=r.make();if(!solveOK(g,false))continue;cnt[r.fam]=(cnt[r.fam]||0)+1;seeds.push({fam:r.fam,name:r.name,head:false,make:r.make,m0:r.m})}
  // 실측 모양(v17 형)도 출발점: 이 핫스팟 예상 점수 상위 3개 (겹침 85 % 미만이 될 때까지 바뀌어야 기록됨)
  {const L=mlLibrary(cells,Q).filter(x=>(x.kind==='S'||(x.kind==='P'&&!x.head))&&!x.out).slice(0,3).map(x=>x.kind==='P'?{...x,s:{fam:x.name,base:x.pname,make:()=>presetGeo(DESIGNS.find(q=>q.k===x.name))}}:x);for(const x of L){const sp=x.kind==='P'?{make:x.s.make}:mlLibSpec(x.s,x.name);const g=sp.make();if(aCheck(g)||!solveOK(g,false))continue;seeds.push({fam:x.s.fam,name:'실측 '+x.name+' · '+x.s.base,head:false,make:sp.make,m0:x.m})}}
  const stripAll=[];for(const c of ML_M.cand){const p={n:c[0],yf:c[1],s:c[2],xf:c[3],b:c[4],wf:c[5],s_eff:c[6]},Ph=mlMasks(p).P.map(sw),r=cellScore(SEL_M,Ph,true,cells,Q);if(r.out)continue;stripAll.push({m:mlCorrect(SEL_M,r.m,'띠형',Ph,cells).m,p})}
  stripAll.sort((a,b)=>a.m-b.m);let ns=0;
  for(const x of stripAll.slice(0,80)){if(ns>=3)break;const c=mlStripCand(x.p,'');if(!c.g||aCheck(c.g))continue;if(maxIoU(mlPool(c.g.cav),true)>=.85)continue;const p=x.p;seeds.push({fam:'띠형',name:'띠형 · 띠 '+p.n+'개 · 폭 '+p.wf.toFixed(2),head:true,make:()=>mlStripCand(p,'').g,m0:x.m});ns++}
  {const rows=cells.map(c=>+c.split('_')[0]),sides=[];if(rows.includes(1))sides.push('bottom');if(rows.includes(4))sides.push('top');const Fs=[];
    for(const side of sides)for(const p of [...stripAll.slice(0,3).map(x=>x.p),...Object.values(ML_LIB.F)]){const mk=mlMasksF(p,side);if(!mk)continue;const c=mlStripCand(p,'',mk,side);if(!c.g||aCheck(c.g))continue;const sc=scoreG(c.g,'F형');if(sc)Fs.push({m:sc.m,p,side})}
    Fs.sort((a,b)=>a.m-b.m);if(Fs[0]){const x=Fs[0];seeds.push({fam:'F형',name:'F형 · 띠 '+x.p.n+'개',head:true,make:()=>mlStripCand(x.p,'',mlMasksF(x.p,x.side),x.side).g,m0:x.m})}}
  // 진화
  const snaps=[];
  for(const st of seeds)for(const rep of [0,1]){
    const rnd=mlRng([...(key+st.name+rep)].reduce((a,c)=>(a*31+c.charCodeAt(0))>>>0,7));
    const pick=(L,n)=>{for(let t=0;t<80;t++){const ix=(rnd()*AG)|0,iy=(rnd()*AG)|0;if(L[iy*AG+ix]===n)return [(ix+.5)*AR,(iy+.5)*AR]}return null};
    const ops=[(h,c)=>{const n=rnd()<.5?1:2,a=pick(rnd()<.5?h.gro:h.cav,n);if(!a)return false;const w=[.3,.4,.6][(rnd()*3)|0],L=.8+rnd()*3.2;aRect(h,h.cav,Math.max(XL,a[0]-L/2),Math.max(.6,a[1]-w/2),Math.min(XR,a[0]+L/2),Math.min(11.4,a[1]+w/2),n);c.add++;return true},
      (h,c)=>{const n=rnd()<.5?1:2,a=pick(h.gro,n);if(!a)return false;const L=1+rnd()*2.5,hz=rnd()<.5,cl=v=>Math.max(.6,Math.min(11.4,v));hz?aRect(h,h.gro,cl(a[0]-L/2),cl(a[1]-.4),cl(a[0]+L/2),cl(a[1]+.4),n):aRect(h,h.gro,cl(a[0]-.4),cl(a[1]-L/2),cl(a[0]+.4),cl(a[1]+L/2),n);c.gro++;return true}];
    let g;try{g=st.make()}catch(e){continue}if(!g||aCheck(g))continue;let cur=scoreG(g,st.fam);if(!cur)continue;let c0={add:0,cut:0,gro:0};
    const maxCh=st.head?20:12;
    for(let i=0;i<iters;i++){if(c0.add+c0.gro>=maxCh)break;const h=mlCloneG(g),c={...c0};h.bad=null;if(!ops[rnd()<.6?0:1](h,c)||h.bad||aCheck(h))continue;const sc=scoreG(h,st.fam);if(!sc)continue;
      const T=.03*Math.pow(.02,i/iters);if(sc.m<cur.m||rnd()<Math.exp(-(sc.m-cur.m)/T)){g=h;cur=sc;c0=c;
        if(c0.add+c0.gro>=3){const iou=maxIoU(sc.P,st.head);if(iou<.85)snaps.push({m:sc.m,g:mlCloneG(h),fam:st.fam,from:st.name,head:st.head,cnt:{...c0},iou,m0:st.m0})}}}
    if(i_yield++%2===0)await new Promise(r=>setTimeout(r))}
  snaps.sort((a,b)=>a.m-b.m);
  const out=[],famUsed=new Set();let solves=0;
  for(const sn of snaps){if(out.length>=5||solves>=40)break;if(out.length&&famUsed.has(sn.fam))continue;const P=mlPool(sn.g.cav);if(out.some(o=>mlIoU(P,o.P)>=.85))continue;solves++;
    if(!solveOK(sn.g,sn.head))continue;famUsed.add(sn.fam);out.push({...sn,P})}
  const rle=a=>{const o=[];let i=0;while(i<a.length){let j=i;while(j<a.length&&a[j]===a[i])j++;o.push(a[i],j-i);i=j}return o};
  const lib=mlLibrary(cells,Q).slice(0,6).map(x=>({name:x.name,T:20+Math.exp(x.m),meas:x.meas,out:x.out}));
  const pack=o=>({nDead:nDead(mlPool(o.g.cav),o.head),fam:o.fam,from:o.from,head:o.head?1:0,cnt:o.cnt,iou:o.iou,T:20+Math.exp(o.m),T0:20+Math.exp(o.m0),g:{cav:rle(o.g.cav),gro:rle(o.g.gro),pin:o.g.pin,pout:o.g.pout}});
  return {key,cells:[...cells],w:cells.w,exact:cells.exact,hs:hsIn||null,Q,nCand:res.length,seeds:seeds.map(s=>[s.fam,s.name,+(20+Math.exp(s.m0)).toFixed(1)]),nSnap:snaps.length,best:out[0]?pack(out[0]):null,alts:out.slice(1).map(pack),lib};
}
var i_yield=0;`;

(async () => {
  const [out, ...hss] = process.argv.slice(2);
  const iters = +(process.env.ITERS || 700);
  // 계산 엔진은 v23 판이 있으면 그것(사용자가 쓰는 판), 없으면 v17. PAGE=hotspot_agent_v17_ml.html 로 바꿀 수 있음
  const v23 = path.resolve(__dirname, '../html_v23/hotspot_agent_v23_ml.html');
  const file = 'file://' + (process.env.PAGE ? path.resolve(__dirname, process.env.PAGE) : (fs.existsSync(v23) ? v23 : path.resolve(__dirname, 'hotspot_agent_v17_ml.html')));
  const browser = await chromium.launch();
  const res = fs.existsSync(out) ? JSON.parse(fs.readFileSync(out, 'utf8')) : {};
  for (const spec of hss) {
    // 'r_c+r_c' (칸 이름) 또는 '이름=x,y,lx,ly,q;x,y,lx,ly,q' (아무 배치: 중심 x·y, 크기 lx·ly [mm], 열유속 q [W/cm²])
    let hs = spec, free = null;
    if (spec.includes('=')) { const [lab, body] = spec.split('='); hs = lab; free = body.split(';').filter(Boolean).map(t => { const [x, y, lx, ly, q] = t.split(',').map(Number); return {x, y, lx, ly, q}; }); }
    const page = await browser.newPage();
    page.on('pageerror', e => console.log('  페이지 오류', hs, String(e).slice(0, 200)));
    await page.addInitScript(() => { try { localStorage.setItem('hs-agent-v14', JSON.stringify({hs: [], Q: 55})); } catch (e) {} });
    await page.goto(file);
    await page.waitForFunction(() => typeof S !== 'undefined' && typeof G !== 'undefined' && G && typeof mlEvolve === 'function');
    await page.addScriptTag({content: DEEP});
    const t0 = Date.now();
    let r;
    try { r = await page.evaluate(([k, it, q, f, dm]) => { if (dm != null) window.DEADMAX = dm; return deepDesign(k, q, it, f); }, [hs, iters, +(process.env.QML || 55), free, process.env.DEADMAX != null ? +process.env.DEADMAX : null]); }
    catch (e) { console.log('  실패', hs, String(e).slice(0, 300)); await page.close(); continue; }
    r.sec = Math.round((Date.now() - t0) / 1000);
    res[hs] = r; fs.writeFileSync(out, JSON.stringify(res));
    const b = r.best, L = r.lib[0];
    console.log(hs, r.sec + 's', b ? `1위 ${b.fam}에서 진화 ${b.T.toFixed(1)}℃ · 안 흐르는 채널 ${b.nDead}/22 (출발 ${b.T0.toFixed(1)}, 슬롯+${b.cnt.add} 홈+${b.cnt.gro})` : '새 설계 없음',
      '| 실측모양 최선', L ? `${L.name} ${L.T.toFixed(1)}${L.meas != null ? '(실측)' : ''}` : '-', '| 다른 후보', r.alts.map(a => `${a.fam} ${a.T.toFixed(1)}`).join(', '));
    await page.close();
  }
  await browser.close();
})();
