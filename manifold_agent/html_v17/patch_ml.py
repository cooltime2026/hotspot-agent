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

ML = r'''<script id="mlManifold">
/* ============================== [ML] 머신러닝 매니폴드 선택 (2026-11-27 추가) ==============================
   매니폴드 '모양'만 머신러닝으로 정한다. 온도·압력 계산은 위 계산 엔진(evaluate·flowSolve)을 그대로 쓴다.
   모델: SimScale 227 Run 으로 학습한 family_model v2b (manifold_agent/ml/family_model.py, 띠 가족 A·B·C).
   모양: 띠(가로 빗살) 가족 — 숫자 6개(n 띠 수, yf·s 모으기, xf·b 휘기, wf 띠 폭). geometry/param_manifold.py 와 같은 식.
   층: 채널 y 1.5~10.5 + 헤더, 관통층 0.15 / 덮개 홈층 0.4 mm (M1·M3 프리셋과 같은 방식으로 계산 엔진에 넣음).
   입구 (9,1),(9,11) / 출구 (3,1),(3,11) — SimScale 학습 데이터와 같은 방향.
   ============================================================================================================== */
''' + core + "\n" + model + r'''
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
    const name=`머신러닝 띠 ${p.n}개 · 폭 ${p.wf.toFixed(2)}${p.s_eff>.05?` · y ${p.yf.toFixed(1)} 쪽 모음`:''}${Math.abs(p.b)>.05?` · 휨 ${p.b.toFixed(2)}`:''}`;
    const d={k:'A',name:'자동 최적 매니폴드',note:name,inl:'q',P:Uint8Array.from(P,sw),U:Uint8Array.from(U,sw),
      ports:[[9,1],[9,11],[3,1],[3,11]],head:1,T:M1.T,layers:[{h:.15,M:Uint8Array.from(P,bin),n:'관통 매니폴드층'},{h:.4,M:Uint8Array.from(U,bin),n:'덮개 홈층'}]};
    const g=presetGeo(d);if(!g||!port_ok(g)){out.push({name,why:'포트가 유로에 닿지 않음'});continue}
    g.ns={kCav:11,kGro:19,kSolidTop:11,kEval:29,nz:49,CY:[1.5,10.5],head:1};
    d.flow=makeFlow(g,null,null);out.push({name,d,g,p})}
  return {cells,Qd,list:out};
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
    "    AUTO.ml=mr;if(mr.why)list.push({name:'머신러닝 후보',why:mr.why});for(const c of mr.list)list.push(c.why?{name:c.name,why:c.why}:{name:c.name,g:c.g,d:c.d});\n") + src[a:]
# 3) 다시 고를 조건에 유량·목표 온도 추가
src = rep(src, "const key=JSON.stringify([S.inl,!!S.direct,HSN.map(h=>[h.x,h.y,h.lx,h.ly,h.q])]);",
          "const key=JSON.stringify([S.inl,!!S.direct,HSN.map(h=>[h.x,h.y,h.lx,h.ly,h.q]),Math.max(55,Math.min(100,Math.round(S.Q))),S.Tlim]);   // ← ML: 유량·목표 온도 추가")
# 4) 헤더형 그대로 전달
_o = "Object.assign(AUTOD,{T:d.T,U:d.U,P:d.P,ports:d.ports,head:0,"
assert src.count(_o) == 2          # autoDesign 과 nsStage 두 곳
src = src.replace(_o, "Object.assign(AUTOD,{T:d.T,U:d.U,P:d.P,ports:d.ports,head:d.head||0,   /* ← ML: 머신러닝 모양은 헤더형 */")
# 7) 계산식이 '유효하지 않음'(예: 물 95 °C 초과)이라고 해도 머신러닝 모양은 버리지 않고 표시 (경고는 원래 문구 그대로)
src = rep(src, "  const okv=ok.filter(c=>validR(c.r));\n",
          "  const okv=ok.filter(c=>validR(c.r));\n  if(!okv.length&&AUTO.ml&&ok.length)okv.push(...ok.filter(c=>c.r));   // ← ML: 모양은 머신러닝이 정함 → 계산식 판정과 상관없이 표시\n")
# 8) 원래 '후보 N개를 계산해 골랐습니다' 문장 → '머신러닝 후보 N개'로 (머신러닝 예상 온도는 표시 안 함)
src = rep(src, "`${S.direct?'':'직상부 공급형을 뺀 '}후보 ${ok.length}개를 계산해 전체 최고 온도가 가장 낮은 모양을 골랐습니다.",
          "`${S.direct?'':'직상부 공급형을 뺀 '}후보 ${ok.length}개(핫스팟 맞춤 모양 ${ok.length-ok.filter(c=>/^머신러닝/.test(c.name)).length}개 + 머신러닝 띠 모양 ${ok.filter(c=>/^머신러닝/.test(c.name)).length}개)를 계산해 전체 최고 온도가 가장 낮은 모양을 골랐습니다.")
# 9) 3D NS: 모양마다 격자 형상(층 두께·채널 범위·헤더)을 받게 함 — 식은 그대로
src = rep(src, "function nsGrid(){const G=NSGEO,", "const nsGeoOf=g=>g&&g.ns?Object.assign({},NSGEO,g.ns):NSGEO;   // ← ML: 모양별 격자 형상\nfunction nsGrid(GG){const G=GG||NSGEO,")
src = rep(src, "function nsMakeSpec(g,Qt,fl){const G=NSGEO,n=G.n,R=nsGrid(),", "function nsMakeSpec(g,Qt,fl){const G=nsGeoOf(g),n=G.n,R=nsGrid(G),")
src = rep(src, "if(inY&&chMask[i]>=0)for(let k=0;k<R.kCh;k++)fluid[o+nxy*k]=1;",
          "const inH=G.head&&X>0.625&&X<11.375&&((Y>0.5&&Y<1.5)||(Y>10.5&&Y<11.5));   // ← ML: 헤더형(채널층 헤더)\n      if((inY&&chMask[i]>=0)||inH)for(let k=0;k<R.kCh;k++)fluid[o+nxy*k]=1;")
src = rep(src, "g:{cav:c.g.cav,gro:c.g.gro,pin:c.g.pin,pout:c.g.pout}}", "g:{cav:c.g.cav,gro:c.g.gro,pin:c.g.pin,pout:c.g.pout,ns:c.g.ns}}")
# 10) 간이 계산이 모두 '유효하지 않음'이어도 3D NS 는 머신러닝 후보로 돌림
src = rep(src, "  const okv=AUTO.cands.filter(c=>c.d&&c.g&&validR(c.r));\n",
          "  let okv=AUTO.cands.filter(c=>c.d&&c.g&&validR(c.r));if(!okv.length&&AUTO.ml)okv=AUTO.cands.filter(c=>c.d&&c.g&&c.r);   // ← ML\n")
# 6) 제목
src = rep(src, "<title>핫스팟 에이전트</title>", "<title>핫스팟 에이전트 (ML 매니폴드)</title>")

(HERE / "hotspot_agent_v17_ml.html").write_text(src, encoding="utf-8")
print("저장:", HERE / "hotspot_agent_v17_ml.html", len(src))
