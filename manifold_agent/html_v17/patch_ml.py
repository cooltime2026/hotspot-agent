"""HTML v17 에 '머신러닝 매니폴드 선택'을 넣은 판 만들기.
  python html_v17/patch_ml.py      (manifold_agent 폴더에서)  → html_v17/hotspot_agent_v17_ml.html

바꾸는 것: 자동 최적 매니폴드의 '후보 모양 만들기'(autoSpecs 4+1종) → 머신러닝(family_model v2b)이 고른 띠 모양 하나.
그대로인 것: 계산 엔진 전부 (setup·evaluate·flowSolve·makeFlow·presetGeo, 유량 스윕, 순위, 미리 계산한 구조 10개).
머신러닝 코드·모델 숫자는 저장소 맨 위 manifold_designer.html 에서 그대로 가져옴 (모델을 재학습하면 그 파일을 먼저 갱신).
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
src = (HERE / "hotspot_agent_v17.html").read_text(encoding="utf-8")
des = (HERE.parents[1] / "manifold_designer.html").read_text(encoding="utf-8").split("\n")

i0 = next(i for i, l in enumerate(des) if l.startswith("const CORE = (() => {"))
i1 = next(i for i in range(i0, len(des)) if des[i].startswith("})();"))
core = "\n".join(des[i0:i1 + 1]).replace("return { design, mask, bandLayout,", "return { design, mask, squeeze, bandLayout,")
assert "squeeze, bandLayout" in core
model = next(l for l in des if l.startswith("const M = CORE.prepare(")).replace("const M = CORE.prepare(", "const ML_M = CORE.prepare(", 1)
sel = (HERE / "selfeat.js").read_text(encoding="utf-8").replace("if(typeof module!=='undefined')module.exports={selScore};", "")
sel += "const SEL_M=" + (HERE.parent / "ml" / "cell_model.json").read_text(encoding="utf-8").replace("\n", "") + ";   // ml/cell_model.py fit 결과 (칸별 온도 모델)\n"

ML = r'''<script id="mlManifold">
/* ============================== [ML] 머신러닝 매니폴드 선택 (2026-11-27 추가) ==============================
   매니폴드 '모양'만 머신러닝으로 정한다. 온도·압력 계산은 위 계산 엔진(evaluate·flowSolve)을 그대로 쓴다.
   모델: SimScale 227 Run 으로 학습한 family_model v2b (manifold_agent/ml/family_model.py, 띠 가족 A·B·C).
   모양: 띠(가로 빗살) 가족 — 숫자 6개(n 띠 수, yf·s 모으기, xf·b 휘기, wf 띠 폭). geometry/param_manifold.py 와 같은 식.
   층: 채널 y 1.5~10.5 + 헤더, 관통층 0.15 / 덮개 홈층 0.4 mm (M1·M3 프리셋과 같은 방식으로 계산 엔진에 넣음).
   입구 (9,1),(9,11) / 출구 (3,1),(3,11) — SimScale 학습 데이터와 같은 방향.
   ============================================================================================================== */
''' + core + "\n" + model + "\n" + sel + r'''
const ML_RES=0.1,ML_N=120;
// 핫스팟(위치·크기·열유속) → 4×4 칸 이름. 칸마다 받는 발열(겹친 면적×열유속)이 큰 순서로 최대 2칸
function mlCells(hs){
  const w=new Map();
  for(const h of hs)for(let r=1;r<=4;r++)for(let c=1;c<=4;c++){
    const ox=Math.min(h.x+h.lx/2,c*3)-Math.max(h.x-h.lx/2,(c-1)*3),oy=Math.min(h.y+h.ly/2,r*3)-Math.max(h.y-h.ly/2,(r-1)*3);
    if(ox>0&&oy>0)w.set(r+'_'+c,(w.get(r+'_'+c)||0)+ox*oy*h.q)}
  return [...w].sort((a,b)=>b[1]-a[1]).slice(0,2).map(x=>x[0]);
}
// 띠 모양 변수 → 관통층 P, 덮개 홈층 U (0.1 mm, 120×120). 우리 규칙: 1 = A망(출구), 2 = B망(입구)
function mlMasks(p){
  const L=CORE.bandLayout(p),P=new Uint8Array(ML_N*ML_N),U=new Uint8Array(ML_N*ML_N);
  for(let ix=0;ix<ML_N;ix++){const x=(ix+.5)*ML_RES,f=CORE.squeeze(p,x,L);
    L.centers.forEach((c,k)=>{const w=L.width[k]*f,yc=Math.min(Math.max(6+(c-6)*f,1.7+w/2),10.3-w/2);
      const i0=Math.round((yc-w/2)/ML_RES),i1=Math.round((yc+w/2)/ML_RES),v=k%2===0?1:2;
      for(let iy=i0;iy<i1;iy++){if(x>=1.6&&x<=10.4)P[iy*ML_N+ix]=v;if((v===1&&x>=.6&&x<=10.4)||(v===2&&x>=1.6&&x<=11.4))U[iy*ML_N+ix]=v}})}
  const g=a=>Math.round(a/ML_RES),fill=(y0,y1,x0,x1,v)=>{for(let iy=g(y0);iy<g(y1);iy++)for(let ix=g(x0);ix<g(x1);ix++)U[iy*ML_N+ix]=v};
  fill(.4,11.5,.6,1.4,1);fill(.4,11.5,10.6,11.4,2);                                        // 등뼈
  for(const [y0,y1] of [[.4,1.5],[10.5,11.5]]){fill(y0,y1,.6,3.6,1);fill(y0,y1,8.3,11.4,2)}   // 포트 받침
  return {P,U};
}
// 핫스팟·유량 → 머신러닝(SimScale 학습 모델)이 가장 시원할 것으로 본 띠 모양 후보 K개를 계산 엔진용 구조(d)·형상(g)으로
//   후보 1,671개를 모델 점수(같은 유량에서 예상 최고 온도)로 줄 세우고, 비슷한 모양(띠 수·폭·모으기·휨이 같은 것)은 하나만
//   g.ns: 3D 나비에–스토크스 격자 형상(관통층 0.15 = 3칸, 덮개 홈 0.4 = 8칸, 채널 y 1.5~10.5 + 헤더)
function mlCands(hs,Qml,K){
  const cells=mlCells(hs);if(!cells.length)return {why:'판 안에 핫스팟이 없음',list:[]};
  const Qd=Math.max(55,Math.min(100,Math.round(Qml))),M=ML_M,H=CORE.hsPos(cells);
  const hy=cells.reduce((a,c)=>a+(+c.split('_')[0]-.5)*3,0)/cells.length;
  const sc=M.cand.map((c,i)=>{const [n,yf,s,xf,b,wf,seff,logG]=c,dy=Math.abs(hy-yf)/12*Math.min(seff,1),lq=Math.log(Qd/55);
    const x=[...H,lq,...H.map(h=>h*lq),logG,wf,dy,...H.map(h=>h*logG)];let m=M.intercept;for(let j=0;j<x.length;j++)m+=M.coef[j]*x[j];return {i,m}}).sort((a,b)=>a.m-b.m);
  const seen=new Set(),out=[],M1=DESIGNS.find(x=>x.k==='M1'),sw=v=>v===1?2:v===2?1:0,bin=v=>v?1:0;
  for(const {i} of sc){if(out.length>=K)break;
    const c=M.cand[i],p={n:c[0],yf:c[1],s:c[2],xf:c[3],b:c[4],wf:c[5],s_eff:c[6]};
    const key=[p.n,p.wf.toFixed(1),p.s_eff>.05?Math.round(p.yf/1.5):'-',p.b>.15?'+':p.b<-.15?'-':'0'].join('|');if(seen.has(key))continue;seen.add(key);
    const {P,U}=mlMasks(p);
    const name=`띠형 (SimScale 학습 가족) · 띠 ${p.n}개 · 폭 ${p.wf.toFixed(2)}${p.s_eff>.05?` · y ${p.yf.toFixed(1)} 쪽 모음`:''}${Math.abs(p.b)>.05?` · 휨 ${p.b.toFixed(2)}`:''}`;
    const d={k:'A',name:'자동 최적 매니폴드',note:name,inl:'q',P:Uint8Array.from(P,sw),U:Uint8Array.from(U,sw),
      ports:[[9,1],[9,11],[3,1],[3,11]],head:1,T:M1.T,layers:[{h:.15,M:Uint8Array.from(P,bin),n:'관통 매니폴드층'},{h:.4,M:Uint8Array.from(U,bin),n:'덮개 홈층'}]};
    const g=presetGeo(d);if(!g||!port_ok(g)){out.push({name,why:'포트가 유로에 닿지 않음'});continue}
    g.ns={kCav:11,kGro:19,kSolidTop:11,kEval:29,nz:49,CY:[1.5,10.5],head:1};
    d.flow=makeFlow(g,null,null);out.push({name,d,g,p})}
  return {cells,Qd,list:out};
}

// 띠 모양 변수 p → 계산 엔진용 후보 {name,d,g}
function mlStripCand(p,prefix){
  const M1=DESIGNS.find(x=>x.k==='M1'),sw=v=>v===1?2:v===2?1:0,bin=v=>v?1:0,{P,U}=mlMasks(p);
  const name=`${prefix||''}띠형 (SimScale 학습 가족) · 띠 ${p.n}개 · 폭 ${p.wf.toFixed(2)}${p.s_eff>.05?` · y ${p.yf.toFixed(1)} 쪽 모음`:''}${Math.abs(p.b)>.05?` · 휨 ${p.b.toFixed(2)}`:''}`;
  const d={k:'A',name:'자동 최적 매니폴드',note:name,inl:'q',P:Uint8Array.from(P,sw),U:Uint8Array.from(U,sw),
    ports:[[9,1],[9,11],[3,1],[3,11]],head:1,T:M1.T,layers:[{h:.15,M:Uint8Array.from(P,bin),n:'관통 매니폴드층'},{h:.4,M:Uint8Array.from(U,bin),n:'덮개 홈층'}]};
  const g=presetGeo(d);if(!g||!port_ok(g))return {name,why:'포트가 유로에 닿지 않음'};
  g.ns={kCav:11,kGro:19,kSolidTop:11,kEval:29,nz:49,CY:[1.5,10.5],head:1};d.flow=makeFlow(g,null,null);return {name,d,g,p};
}
// 0.05 mm 격자(240) → 0.1 mm(120), 2×2 칸 중 큰 값 (aDesign 의 pool 과 같음)
function mlPool(L){const o=new Uint8Array(120*120);for(let iy=0;iy<120;iy++)for(let ix=0;ix<120;ix++){const k=2*iy*AG+2*ix;o[iy*120+ix]=Math.max(L[k],L[k+1],L[k+AG],L[k+AG+1])}return o}
// ★ 머신러닝 최적 매니폴드 설계: 모양 종류별 숫자를 촘촘하게 바꿔 그려 보고(v17 규칙 + 띠 가족), SimScale 학습 모델 점수가 가장 좋은 모양을 만든다.
//   학습 범위 밖 모양(특징이 학습 데이터 범위를 10 % 넘게 벗어남)은 고르지 않는다. 계산(유량장·온도)은 하지 않음 — 모양 그림만으로 점수.
async function mlOptimize(hs,Qml,direct,alive,prog){
  const cells=mlCells(hs);if(!cells.length)return null;let n=0;const jobs=[],res=[];
  const mm=m=>m==='full'?'전폭 슬롯':`좌우 여유 ${m} mm`;
  const tryG=(fam,name,make)=>jobs.push([fam,name,make]),run=(fam,name,make)=>{let g;try{g=make()}catch(e){return}if(!g||aCheck(g))return;n++;
    const P=mlPool(g.cav),r=cellScore(SEL_M,P,false,cells,Qml);if(r.out)return;const c=mlCorrect(SEL_M,r.m,fam,P,cells);res.push({m:c.m,fam,name,make})};
  const R=(a,b,st)=>{const o=[];for(let v=a;v<=b+1e-9;v+=st)o.push(+v.toFixed(2));return o};
  for(const gg of [0,1])for(const m of [...R(0,3,.5),'full'])for(const s of R(.4,1.2,.2)){
    tryG('흡입형',`흡입형 (양끝 공급, 핫스팟 위 배출) · 슬롯 ${s} mm · ${mm(m)}${gg?' · 가운데 한 줄':''}`,()=>aSwap(famDirect(hs,s,m,gg)));
    if(direct)tryG('직상부 공급형',`직상부 공급형 · 슬롯 ${s} mm · ${mm(m)}${gg?' · 가운데 한 줄':''}`,()=>famDirect(hs,s,m,gg))}
  for(const w of R(.4,1.0,.2))for(const pp of R(1.0,3.0,.2))tryG('V자 빗살형',`V자 빗살형 · 빗살 폭 ${w} mm · 간격 ${pp} mm`,()=>famV(hs,w,pp));
  for(const f of [0,1])tryG('대역 대향류형',`대역 대향류형${f?' · 방향 반대':''}`,()=>famBand(hs,f));
  for(const m of [...R(.5,2.5,.5),'vor'])for(const s of R(.4,1.0,.2))for(const gp of R(-.6,.4,.2))for(const r of [0,1])
    tryG('바람개비형',`바람개비형 · 슬롯 ${s} mm · ${m==='vor'?'이웃 핫스팟 중간까지':mm(m)} · 슬롯 간격 ${gp} mm${r?' · 좌우 반전':''}`,()=>famPin(hs,m,r,s,gp));
  const tk=()=>new Promise(r=>setTimeout(r));
  for(let j=0;j<jobs.length;j++){run(...jobs[j]);if(j%25===24){if(prog)prog(j+1,jobs.length+ML_M.cand.length);await tk();if(alive&&!alive())return null}}
  // 띠 가족: 1,671개 전부 점수 (마스크만 그림)
  const C=ML_M.cand;let bs=null;
  for(let i=0;i<C.length;i++){if(i%100===99){if(prog)prog(jobs.length+i+1,jobs.length+C.length);await tk();if(alive&&!alive())return null}const c=C[i],p={n:c[0],yf:c[1],s:c[2],xf:c[3],b:c[4],wf:c[5],s_eff:c[6]},{P}=mlMasks(p),Ph=P.map(v=>v===1?2:v===2?1:0);
    const r=cellScore(SEL_M,Ph,true,cells,Qml);n++;if(r.out)continue;const cm=mlCorrect(SEL_M,r.m,'띠형',Ph,cells).m;if(!bs||cm<bs.m)bs={m:cm,p}}
  res.sort((a,b)=>a.m-b.m);const specs=[],seenF={};
  for(const r of res){if(specs.length>=5)break;if((seenF[r.fam]=(seenF[r.fam]||0)+1)>2)continue;specs.push({fam:r.fam,name:'머신러닝 설계 · '+r.name,make:r.make,mlopt:true})}   // 종류마다 2개까지, 모두 5개
  const top=res[0];return {specs,strip:bs&&bs.p,stripM:bs&&bs.m,m:Math.min(top?top.m:Infinity,bs?bs.m:Infinity),n};
}
</script>
'''

def rep(s, old, new):
    assert s.count(old) == 1, old[:60]
    return s.replace(old, new)

# 1) 계산 엔진(calcB) 블록 바로 다음에 삽입
cb = src.index('<script id="calcB">'); ce = src.index('</script>', cb) + len('</script>')
src = src[:ce] + '\n' + ML.rstrip('\n') + src[ce:]
# 2) autoDesign: 원래 후보(바람개비·대역·V자·직상부 등)는 그대로 두고, 그 뒤에 머신러닝 띠 후보 6개를 더함
a = src.index("    AUTO.key=key;AUTO.cands=list;")
src = src[:a] + (
    "    // ← ML: 머신러닝(SimScale 학습)이 고른 띠 모양 후보를 더함. 그 뒤 간이 계산 → 3D NS 는 원래 그대로\n"
    "    st('머신러닝 띠 모양 후보를 더하는 중입니다');await tick();if(my!==token)return false;\n"
    "    let mr;try{mr=mlCands(HSN,S.Q,6)}catch(e){mr={why:'머신러닝 후보를 만들지 못함: '+(e.message||e),list:[]}}\n"
    "    if(AUTO.mlopt&&AUTO.mlopt.strip){const c=mlStripCand(AUTO.mlopt.strip,'머신러닝 설계 · ');if(c.d)list.unshift({name:c.name,g:c.g,d:c.d})}\n"
    "    AUTO.ml=mr;if(mr.why)list.push({name:'머신러닝 후보',why:mr.why});for(const c of mr.list)list.push(c.why?{name:c.name,why:c.why}:{name:c.name,g:c.g,d:c.d});\n") + src[a:]
# 2b) 머신러닝 최적 매니폴드를 먼저 설계해서 후보 맨 앞에 넣음
src = rep(src, "const hs=HSN.map(h=>({...h})),specs=autoSpecs(hs).filter(q=>S.direct||q.fam!=='직상부 공급형'),list=[],seen=new Set();",
          "const hs=HSN.map(h=>({...h})),specs=autoSpecs(hs).filter(q=>S.direct||q.fam!=='직상부 공급형'),list=[],seen=new Set();\n    st('머신러닝이 이 핫스팟에 맞는 최적 매니폴드를 설계하는 중입니다 (모양 수천 개 시험)');await tick();if(my!==token)return false;\n    let mo=null;try{mo=await mlOptimize(hs,S.Q,!!S.direct,()=>my===token,(i,n)=>st(`머신러닝이 이 핫스팟에 맞는 최적 매니폴드를 설계하는 중입니다 (모양 ${i}/${n}개 시험)`))}catch(e){mo=null}if(my!==token)return false;AUTO.mlopt=mo;if(mo&&mo.specs)specs.unshift(...mo.specs);   // ← ML 최적 설계")
# 4) 헤더형 그대로 전달
_o = "Object.assign(AUTOD,{T:d.T,U:d.U,P:d.P,ports:d.ports,head:0,"
assert src.count(_o) == 2          # autoDesign 과 nsStage 두 곳
src = src.replace(_o, "Object.assign(AUTOD,{T:d.T,U:d.U,P:d.P,ports:d.ports,head:d.head||0,   /* ← ML: 머신러닝 모양은 헤더형 */")
# 7) 계산식이 '유효하지 않음'(예: 물 95 °C 초과)이라고 해도 머신러닝 모양은 버리지 않고 표시 (경고는 원래 문구 그대로)
src = rep(src, "  const okv=ok.filter(c=>validR(c.r));\n",
          "  const okv=ok.filter(c=>validR(c.r));\n  if(!okv.length&&AUTO.ml&&ok.length)okv.push(...ok.filter(c=>c.r));   // ← ML: 모양은 머신러닝이 정함 → 계산식 판정과 상관없이 표시\n")
# 8) 상태 문장: 선택은 머신러닝 1위 (머신러닝 예상 온도는 표시 안 함)
src = rep(src, "st(AUTO.pick!=null?'직접 고른 모양입니다. 핫스팟을 옮기면 다시 자동으로 고릅니다.':`${S.direct?'':'직상부 공급형을 뺀 '}후보 ${ok.length}개를 계산해 전체 최고 온도가 가장 낮은 모양을 골랐습니다. 차이가 0.5 °C 이내면 압력강하가 작은 쪽입니다.`);",
          "st(AUTO.pick!=null?'직접 고른 모양입니다. 핫스팟을 옮기면 다시 자동으로 고릅니다.':(best&&best.ml?`머신러닝(SimScale 227 Run 학습)이 이 핫스팟에 맞춰 모양 ${AUTO.mlopt&&AUTO.mlopt.n||0}개를 그려 보고 최적 매니폴드를 설계했습니다(1위). 나머지 후보 ${ok.length-1}개는 머신러닝 순위대로 보여 줍니다. 온도·압력은 이 에이전트 계산식 값입니다. ⚠ 바람개비·대역처럼 헤더 없는 원래 모양은 비슷한 실측이 D0·D1 두 개뿐이라 머신러닝 순위가 부정확할 수 있습니다.`:`${S.direct?'':'직상부 공급형을 뺀 '}후보 ${ok.length}개를 계산해 전체 최고 온도가 가장 낮은 모양을 골랐습니다. 차이가 0.5 °C 이내면 압력강하가 작은 쪽입니다.`));   // ← ML")
# 9) 3D NS: 모양마다 격자 형상(층 두께·채널 범위·헤더)을 받게 함 — 식은 그대로
src = rep(src, "function nsGrid(){const G=NSGEO,", "const nsGeoOf=g=>g&&g.ns?Object.assign({},NSGEO,g.ns):NSGEO;   // ← ML: 모양별 격자 형상\nfunction nsGrid(GG){const G=GG||NSGEO,")
src = rep(src, "function nsMakeSpec(g,Qt,fl){const G=NSGEO,n=G.n,R=nsGrid(),", "function nsMakeSpec(g,Qt,fl){const G=nsGeoOf(g),n=G.n,R=nsGrid(G),")
src = rep(src, "if(inY&&chMask[i]>=0)for(let k=0;k<R.kCh;k++)fluid[o+nxy*k]=1;",
          "const inH=G.head&&X>0.625&&X<11.375&&((Y>0.5&&Y<1.5)||(Y>10.5&&Y<11.5));   // ← ML: 헤더형(채널층 헤더)\n      if((inY&&chMask[i]>=0)||inH)for(let k=0;k<R.kCh;k++)fluid[o+nxy*k]=1;")
src = rep(src, "g:{cav:c.g.cav,gro:c.g.gro,pin:c.g.pin,pout:c.g.pout}}", "g:{cav:c.g.cav,gro:c.g.gro,pin:c.g.pin,pout:c.g.pout,ns:c.g.ns}}")
# 10) 간이 계산이 모두 '유효하지 않음'이어도 3D NS 는 머신러닝 후보로 돌림
src = rep(src, "  const okv=AUTO.cands.filter(c=>c.d&&c.g&&validR(c.r));\n",
          "  let okv=AUTO.cands.filter(c=>c.d&&c.g&&validR(c.r));if(!okv.length&&AUTO.ml)okv=AUTO.cands.filter(c=>c.d&&c.g&&c.r);   // ← ML\n")
# 11) 선택: 머신러닝 1위 (간이 계산 순위로 바꾸지 않음)
src = rep(src, "if(!best){const lam=okv.filter(c=>feas(c.r))", "if(!best&&AUTO.ml){best=ok.find(c=>c.ml===1&&c.r)||null}   // ← ML: 선택은 머신러닝 1위\n  if(!best){const lam=okv.filter(c=>feas(c.r))")
# 12) 3D NS 대상: 머신러닝 1·2위
src = rep(src, "let top=top0.slice(0,NS_K);", "let top=AUTO.ml&&AUTO.cands.some(c=>c.ml)?AUTO.cands.filter(c=>c.ml&&c.d&&c.g&&c.r).sort((a,b)=>a.ml-b.ml).slice(0,NS_K):top0.slice(0,NS_K);   // ← ML: 머신러닝 1·2위")
src = rep(src, "간이 모델 상위 후보 ${top.length}개", "${top.some(c=>c.ml)?'머신러닝':'간이 모델'} 상위 후보 ${top.length}개")
# 13) 3D 뒤 최종 선택도 머신러닝 1위 (3D 결과가 유효하면)
src = rep(src, "const b=pl.filter(x=>x.ns.Tmax<=tm+.5).reduce((p,q)=>p.ns.dp<=q.ns.dp?p:q),d=b.c.d;",
          "const b=cand.find(x=>x.c.ml===1)||pl.filter(x=>x.ns.Tmax<=tm+.5).reduce((p,q)=>p.ns.dp<=q.ns.dp?p:q),d=b.c.d;   // ← ML: 머신러닝 1위")
src = rep(src, "st(`3D 나비에–스토크스 + 열전달로 상위 후보 ${cand.length}개를 다시 풀어 최고 온도가 가장 낮은 모양을 골랐습니다(0.5 °C 이내면 압력강하가 작은 쪽). [${tbl}]",
          "st((b.c.ml?`3D 나비에–스토크스 + 열전달로 머신러닝 상위 후보 ${cand.length}개를 계산했습니다. 선택은 머신러닝 ${b.c.ml}위입니다.`:`3D 나비에–스토크스 + 열전달로 상위 후보 ${cand.length}개를 다시 풀어 최고 온도가 가장 낮은 모양을 골랐습니다(0.5 °C 이내면 압력강하가 작은 쪽).`)+` [${tbl}]")
# 14) 모든 후보(원래 모양 + 띠 모양)를 머신러닝 고르기 모델로 줄 세움
src = rep(src, "  const ok=AUTO.cands.filter(c=>c.d);\n",
          "  const ok=AUTO.cands.filter(c=>c.d);\n  {const cells=mlCells(HSN);const sc=ok.filter(c=>c.d.P).map(c=>{if(!c.base)c.base=c.name;try{const r=cellScore(SEL_M,c.d.P,!!c.d.head,cells,S.Q),fam=c.d.head?'띠형':mlFamOf(c.base),k=mlCorrect(SEL_M,r.m,fam,c.d.P,cells);c.mls=k.m;c.mlOut=r.out;c.mlRef=k.w>.5&&k.ref&&k.ref!=='띠 가족'?k.ref:null}catch(e){c.mls=Infinity}return c}).sort((a,b)=>((a.mlOut>0)-(b.mlOut>0))||(a.mls-b.mls));sc.forEach((c,i)=>{c.ml=i+1;c.name=i===0&&!c.mlOut?`1위 머신러닝 최적${c.mlRef?` (실측 ${c.mlRef} 반영)`:''} · ${c.base.replace(/^머신러닝 설계 · /,'')}`:`머신러닝 ${i+1}위${c.mlOut?' (학습 범위 밖)':''}${c.mlRef?` (실측 ${c.mlRef} 반영)`:''} · ${c.base}`})}   // ← ML\n")
src = rep(src, "const ok=AUTO.cands.map((c,i)=>({c,i})).filter(x=>x.c.d&&x.c.r).sort((p,q)=>p.c.r.Tmax-q.c.r.Tmax)",
          "const ok=AUTO.cands.map((c,i)=>({c,i})).filter(x=>x.c.d&&x.c.r).sort((p,q)=>(p.c.ml&&q.c.ml)?p.c.ml-q.c.ml:p.c.r.Tmax-q.c.r.Tmax)   /* ← ML: 머신러닝 순위 */")
# 6) 제목
src = rep(src, "<title>핫스팟 에이전트</title>", "<title>핫스팟 에이전트 (ML 매니폴드)</title>")

(HERE / "hotspot_agent_v17_ml.html").write_text(src, encoding="utf-8")
print("저장:", HERE / "hotspot_agent_v17_ml.html", len(src))
