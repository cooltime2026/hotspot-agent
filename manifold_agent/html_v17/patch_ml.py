"""HTML v17 에 '머신러닝 매니폴드 선택'을 넣은 판 만들기.
  python html_v17/patch_ml.py      (manifold_agent 폴더에서)  → html_v17/hotspot_agent_v17_ml.html

바꾸는 것: 자동 최적 매니폴드의 '후보 모양 만들기'(autoSpecs 4+1종) → 머신러닝(family_model v2b)이 고른 띠 모양 하나.
그대로인 것: 계산 엔진 전부 (setup·evaluate·flowSolve·makeFlow·presetGeo, 유량 스윕, 순위, 미리 계산한 구조 10개).
머신러닝 코드·모델 숫자는 저장소 맨 위 manifold_designer.html 에서 그대로 가져옴 (모델을 재학습하면 그 파일을 먼저 갱신).
"""
from pathlib import Path
import json

import sys
HERE = Path(__file__).resolve().parent
# 판 고르기 (2026-11-28): 인자 없으면 v17 을 만들고, 이어서 html_v23 이 있으면 v23 도 만듦. `python html_v17/patch_ml.py v23` = v23 만.
#   원본은 html_<판>/hotspot_agent_<판>.html (수정 안 함), 결과는 같은 폴더의 hotspot_agent_<판>_ml.html · artifact_body.html. 머신러닝 코드(selfeat.js 등)는 두 판이 같이 씀.
VER = sys.argv[1] if len(sys.argv) > 1 else "v17"
VDIR = HERE.parent / f"html_{VER}"
src = (VDIR / f"hotspot_agent_{VER}.html").read_text(encoding="utf-8")
des = (HERE.parents[1] / "manifold_designer.html").read_text(encoding="utf-8").split("\n")

i0 = next(i for i, l in enumerate(des) if l.startswith("const CORE = (() => {"))
i1 = next(i for i in range(i0, len(des)) if des[i].startswith("})();"))
core = "\n".join(des[i0:i1 + 1]).replace("return { design, mask, bandLayout,", "return { design, mask, squeeze, bandLayout,")
assert "squeeze, bandLayout" in core
model = next(l for l in des if l.startswith("const M = CORE.prepare(")).replace("const M = CORE.prepare(", "const ML_M = CORE.prepare(", 1)
sel = (HERE / "selfeat.js").read_text(encoding="utf-8").replace("if(typeof module!=='undefined')module.exports={selScore};", "")
sel += "const SEL_M=" + (HERE.parent / "ml" / "cell_model.json").read_text(encoding="utf-8").replace("\n", "") + ";   // ml/cell_model.py fit 결과 (칸별 온도 모델)\n"

# 실측 모양 목록 (2~5위 후보): SimScale 로 돌려 본 매니폴드 형상 + 핫스팟별 실측 최고온도
def _lib():
    import csv, sys as _s
    _s.path.insert(0, str(HERE.parent)); _s.path.insert(0, str(HERE.parent / "ml"))
    from geometry import param_manifold as _PM, split_feed as _SF
    runs = list(csv.DictReader(open(HERE.parent / "data/direct_runs.csv", encoding="utf-8")))
    meas = {}
    def _free_sig(k):      # 아무 배치 설계의 실측은 '그 배치' 이름표로만 (칸 이름표로 넣으면 다른 핫스팟에서 잘못 쓰임)
        f = HERE.parent / f"out/new_designs/{k}_mask.json"
        h = json.loads(f.read_text()).get("hs") if re.match(r"^N\d", k) and f.exists() else None
        return "free:" + ";".join(sorted(f"{x['x']:.2f},{x['y']:.2f},{x['lx']:.2f},{x['ly']:.2f},{x['q']:.2f}" for x in h)) if h else None
    for r in runs:
        hs = _free_sig(r["design"]) or "+".join(sorted(r["heat"].split("at ")[1].split(",")))
        meas.setdefault(r["design"], []).append([hs, float(r["total_flow_mL_min"]), float(r["Tmax_bottom_C"])])
    def rle(a):
        o, prev, n = [], a[0], 0
        for v in a:
            if v == prev: n += 1
            else: o += [int(prev), n]; prev, n = v, 1
        return o + [int(prev), n]
    strip = {}
    for k in [f"{a}{i}" for a in "ABC" for i in range(1, 9)]:
        f = HERE.parent / f"out/step_param_v3/{k}.json"
        if f.exists() and k in meas:
            q = json.loads(f.read_text())["params"]
            strip[k] = {kk: q[kk] for kk in ["n", "yf", "s", "xf", "b", "wf", "s_eff"]}
    F = {}
    for k, q in _SF.F.items():
        if k in meas:
            r_ = _PM.resolve(q); F[k] = {kk: r_[kk] for kk in ["n", "yf", "s", "xf", "b", "wf", "s_eff"]}
    S = []
    for f in sorted((HERE.parent / "out/step_v17").glob("S*_mask.json"), key=lambda x: int(x.stem.split("_")[0][1:])):
        k = f.stem.split("_")[0]
        if k not in meas: continue
        m = json.loads(f.read_text()); base = (m.get("base") or "").replace("머신러닝 설계 · ", "").replace("1위 머신러닝 최적 · ", "")
        base = re.sub(r"^(머신러닝 \d+위( \([^)]*\))? · )", "", base)
        S.append(dict(name=k, base=base, fam=base.split(" · ")[0].split(" (")[0], pin=m["pin"], pout=m["pout"], cav=rle(m["cav"]), gro=rle(m["gro"])))
    for f in sorted((HERE.parent / "out/new_designs").glob("N*_mask.json"), key=lambda x: int(x.stem.split("_")[0][1:])):   # 머신러닝 새 설계 중 돌려 본 것
        k = f.stem.split("_")[0]
        if k not in meas: continue
        m = json.loads(f.read_text())
        S.append(dict(name=k, base=f"{m['fam']} · 머신러닝 새 설계(진화)", fam=m["fam"], head=int(m.get("head", 0)), pin=m["pin"], pout=m["pout"], cav=rle(m["cav"]), gro=rle(m["gro"])))
    P_ = [k for k in ["D1", "M1", "M3"] if k in meas]      # 실측 프리셋(페이지 DESIGNS 에 있음): 그 핫스팟에서 돌려 본 경우만 2~5위 후보, D1 은 진화 출발점
    return dict(strip=strip, F=F, S=S, P=P_, meas=meas)
import re
def _new():
    """머신러닝 새 설계 N* (ml/build_new.py, out/new_designs) → 핫스팟별 1위 설계 (페이지가 진화를 다시 돌리지 않고 이 모양을 씀 = 보낸 STEP 과 같은 모양)"""
    out = {}
    for f in sorted((HERE.parent / "out/new_designs").glob("N*_mask.json"), key=lambda x: int(x.stem.split("_")[0][1:])):
        m = json.loads(f.read_text()); k = "+".join(sorted(m["hotspot"].split("+")))
        def rle(a):
            o, prev, n = [], a[0], 0
            for v in a:
                if v == prev: n += 1
                else: o += [int(prev), n]; prev, n = v, 1
            return o + [int(prev), n]
        if m.get("hs"):      # 아무 배치 설계: 핫스팟 목록(위치·크기·열유속)이 똑같을 때만 씀 → 이름표 = 핫스팟 서명
            k = "free:" + ";".join(sorted(f"{h['x']:.2f},{h['y']:.2f},{h['lx']:.2f},{h['ly']:.2f},{h['q']:.2f}" for h in m["hs"])); out.setdefault("_Q", {})[k] = m.get("Q", 55)
        out[k] = dict(name=m["name"], fam=m["fam"], seed=m.get("seed"), head=int(m.get("head", 0)), cnt=m["cnt"], pin=m["pin"], pout=m["pout"], cav=rle(m["cav"]), gro=rle(m["gro"]))
    return out
sel += "const ML_NEW=" + json.dumps(_new(), ensure_ascii=False, separators=(",", ":")) + ";   // 핫스팟별 머신러닝 새 설계 (out/new_designs/N*_mask.json, STEP 과 같은 모양)\n"
sel += "const ML_LIB=" + json.dumps(_lib(), ensure_ascii=False, separators=(",", ":")) + ";   // 실측 모양 목록 (patch_ml.py 가 data/direct_runs.csv·out/ 에서 만듦)\n"

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
  // 핫스팟(위치·크기·열유속) → 4×4 칸. 반환 = 발열이 큰 두 칸(이름표: 실측·미리 만든 설계 찾기용) + w(칸마다 기본보다 더 나는 열의 몫, 300 W/cm²가 칸 전체(9 mm²)를 덮으면 1 — 핫스팟 위치·크기·열유속이 모두 들어감)
  // 2026-11-28: 예전에는 두 칸만 보고 나머지 핫스팟을 무시함(떨어진 두 곳·세 곳·칸 경계에 걸친 핫스팟). 이제 칸 모델은 모든 칸의 발열 몫(w)을 씀.
  //   exact = 핫스팟이 칸에 딱 맞는 300 W/cm² 두 칸 이하 → 그때만 실측값·미리 만든 설계(N)를 씀
  const w=new Map(),q0=(typeof S!=='undefined'&&S&&isFinite(S.q0))?Math.min(S.q0,299):50;
  for(const h of hs)for(let r=1;r<=4;r++)for(let c=1;c<=4;c++){
    const ox=Math.min(h.x+h.lx/2,c*3)-Math.max(h.x-h.lx/2,(c-1)*3),oy=Math.min(h.y+h.ly/2,r*3)-Math.max(h.y-h.ly/2,(r-1)*3);
    if(ox>0&&oy>0)w.set(r+'_'+c,(w.get(r+'_'+c)||0)+ox*oy*Math.max(0,h.q-q0)/(9*(300-q0)))}   // 기본 열유속보다 더 나는 열 (학습: 300 W/cm² 칸 = 1)
  const all=[...w].filter(x=>x[1]>.02).sort((a,b)=>b[1]-a[1]),out=all.slice(0,2).map(x=>x[0]),mx=all.length?all[0][1]:1,sc=mx>1?1/mx:1;   // 학습 범위(1)를 넘으면 모든 칸을 같은 비율로 줄임 → 칸 사이 비율(어디가 더 뜨거운지)은 유지
  out.sig='free:'+hs.map(h=>[h.x,h.y,h.lx,h.ly,h.q].map(v=>(+v).toFixed(2)).join(',')).sort().join(';');   // 배치 이름표 (아무 배치의 실측·미리 만든 설계 찾기)
  out.w=Object.fromEntries(all.map(([k,v])=>[k,v*sc]));out.exact=all.length<=2&&all.every(x=>Math.abs(x[1]-1)<.02)&&Math.abs(q0-50)<1;
  return out;
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
// F형(핫스팟 줄 전용 입구, 실측 F1 111.6 ℃ @ 1_3+1_4): 띠 모양 + 헤더 위 구멍 + 첫 띠 연장 + 오른쪽 등뼈 아래 끝 자름. ml/f_family.py 와 같은 규칙
function mlMasksF(p,side){const N=120,{P,U}=mlMasks(p);let r0=-1;for(let iy=0;iy<N;iy++)if(P[iy*N+60]===1){r0=iy;break}if(r0<0)return null;let r1=r0;while(r1+1<N&&P[(r1+1)*N+60]===1)r1++;
  for(let iy=r0;iy<=r1;iy++)for(let ix=104;ix<114;ix++)P[iy*N+ix]=1;
  for(let iy=6;iy<14;iy++)for(let ix=86;ix<111;ix++)P[iy*N+ix]=2;
  const yc=Math.round(((r1+1)*.1+.2)/.1);for(let iy=15;iy<yc;iy++)for(let ix=104;ix<115;ix++)if(U[iy*N+ix]===2)U[iy*N+ix]=0;
  if(side==='top'){const f=A=>{const B=new Uint8Array(N*N);for(let iy=0;iy<N;iy++)B.set(A.subarray((N-1-iy)*N,(N-iy)*N),iy*N);return B};return {P:f(P),U:f(U)}}
  return {P,U}}
function mlStripCand(p,prefix,masks,side){
  const M1=DESIGNS.find(x=>x.k==='M1'),sw=v=>v===1?2:v===2?1:0,bin=v=>v?1:0,{P,U}=masks||mlMasks(p);
  const name=`${prefix||''}${masks?`F형 (핫스팟 줄 전용 입구${side==='top'?' · 위':' · 아래'}) · `:''}띠형 (SimScale 학습 가족) · 띠 ${p.n}개 · 폭 ${p.wf.toFixed(2)}${p.s_eff>.05?` · y ${p.yf.toFixed(1)} 쪽 모음`:''}${Math.abs(p.b)>.05?` · 휨 ${p.b.toFixed(2)}`:''}`;
  const d={k:'A',name:'자동 최적 매니폴드',note:name,inl:'q',P:Uint8Array.from(P,sw),U:Uint8Array.from(U,sw),
    ports:[[9,1],[9,11],[3,1],[3,11]],head:1,T:M1.T,layers:[{h:.15,M:Uint8Array.from(P,bin),n:'관통 매니폴드층'},{h:.4,M:Uint8Array.from(U,bin),n:'덮개 홈층'}]};
  const g=presetGeo(d);if(!g||!port_ok(g))return {name,why:'포트가 유로에 닿지 않음'};
  g.ns={kCav:11,kGro:19,kSolidTop:11,kEval:29,nz:49,CY:[1.5,10.5],head:1};d.flow=makeFlow(g,null,null);return {name,d,g,p};
}
// 헤더형 진화 모양(g, 0.05 mm) → 계산 엔진 구조 d (M1·M3 프리셋과 같은 방식)
function mlDFromG(g,name){const M1=DESIGNS.find(x=>x.k==='M1'),bin=v=>v?1:0,P=mlPool(g.cav),U=mlPool(g.gro);
  const d={k:'A',name:'자동 최적 매니폴드',note:name,inl:'q',P,U,ports:[...g.pin,...g.pout],head:1,T:M1.T,layers:[{h:.15,M:Uint8Array.from(P,bin),n:'관통 매니폴드층'},{h:.4,M:Uint8Array.from(U,bin),n:'덮개 홈층'}]};
  const g2=presetGeo(d);if(!g2||!port_ok(g2)||aCheck(g2))return null;g2.ns={kCav:11,kGro:19,kSolidTop:11,kEval:29,nz:49,CY:[1.5,10.5],head:1};d.flow=makeFlow(g2,null,null);return {d,g:g2}}
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
  const C=ML_M.cand;let bs=null;const stripAll=[];
  for(let i=0;i<C.length;i++){if(i%100===99){if(prog)prog(jobs.length+i+1,jobs.length+C.length);await tk();if(alive&&!alive())return null}const c=C[i],p={n:c[0],yf:c[1],s:c[2],xf:c[3],b:c[4],wf:c[5],s_eff:c[6]},{P}=mlMasks(p),Ph=P.map(v=>v===1?2:v===2?1:0);
    const r=cellScore(SEL_M,Ph,true,cells,Qml);n++;if(r.out)continue;const cm=mlCorrect(SEL_M,r.m,'띠형',Ph,cells).m;stripAll.push({m:cm,p});if(!bs||cm<bs.m)bs={m:cm,p}}
  res.sort((a,b)=>a.m-b.m);const specs=[],seenF={};
  for(const r of res){if(specs.length>=5)break;if((seenF[r.fam]=(seenF[r.fam]||0)+1)>2)continue;specs.push({fam:r.fam,name:'머신러닝 설계 · '+r.name,make:r.make,mlopt:true})}   // 종류마다 2개까지, 모두 5개
  stripAll.sort((a,b)=>a.m-b.m);const stripTop=[];for(const x of stripAll){if(stripTop.length>=3)break;if(!stripTop.some(q=>q.n===x.p.n&&Math.abs(q.wf-x.p.wf)<.08))stripTop.push(x.p)}
  // F형: 띠 상위 3개 + 실측 F 설정, 핫스팟이 1행이면 아래·4행이면 위
  const Fall=[];{const rows=cells.map(c=>+c.split('_')[0]),sides=[];if(rows.includes(1))sides.push('bottom');if(rows.includes(4))sides.push('top');
    for(const side of sides)for(const p of [...stripTop,...Object.values(ML_LIB.F)]){const mk=mlMasksF(p,side);if(!mk)continue;const Ph=mk.P.map(v=>v===1?2:v===2?1:0),r=cellScore(SEL_M,Ph,true,cells,Qml);n++;if(r.out)continue;Fall.push({m:mlCorrect(SEL_M,r.m,'F형',Ph,cells).m,p,side})}}
  Fall.sort((a,b)=>a.m-b.m);
  // 실측 모양(2~5위 후보) 점수: 이 핫스팟·유량에서 돌려 본 적 있으면 실측값
  const lib=mlLibrary(cells,Qml);
  // 1위 후보들(점수 순): v17 규칙 설계 · 띠 · F형 · (실측 모양이 더 좋으면 그 모양 그대로)
  // 종류별로 섞어서 (v17 규칙은 종류마다 1개씩 최대 3종류, 띠 1, F 1) → 유량 계산이 안 되는 설계가 있어도 다음 설계가 1위
  const v17=[],famSeen=new Set();for(const r of res){if(v17.length>=3)break;if(famSeen.has(r.fam))continue;famSeen.add(r.fam);v17.push(r)}
  const opts=[...v17.map(r=>({kind:'v17',m:r.m,spec:{fam:r.fam,name:'머신러닝 설계 · '+r.name,make:r.make,mlopt:true}})),
    ...stripAll.slice(0,1).map(x=>({kind:'strip',m:x.m,p:x.p})),...Fall.slice(0,1).map(x=>({kind:'F',m:x.m,p:x.p,side:x.side}))].sort((a,b)=>a.m-b.m);
  // 핫스팟별로 미리 깊게 찾아 둔 새 설계(ML_NEW, STEP 으로 보낸 모양)가 있으면 그것을 씀 (유량 55±3 mL/min, 아직 실측 안 된 것). 없으면 여기서 진화
  let evo=null;{const fk='free:'+hs.map(h=>[h.x,h.y,h.lx,h.ly,h.q].map(v=>(+v).toFixed(2)).join(',')).sort().join(';'),q0ok=Math.abs((S.q0??50)-50)<1;   // 아무 배치로 미리 만든 설계(ml/design_any.py): 핫스팟 목록이 똑같고 유량 ±3 일 때
    const pre=(q0ok&&ML_NEW[fk])||(cells.exact!==false&&ML_NEW[cells.slice().sort().join('+')]),Qpre=(pre&&ML_NEW._Q&&ML_NEW._Q[fk]&&pre===ML_NEW[fk])?ML_NEW._Q[fk]:55;if(pre&&Math.abs(Qml-Qpre)<=3&&!ML_LIB.meas[pre.name]){const g=aGeo();g.cav.set(mlRLE(pre.cav,AG*AG));g.gro.set(mlRLE(pre.gro,AG*AG));g.pin=pre.pin.map(p=>p.slice());g.pout=pre.pout.map(p=>p.slice());if(pre.head)g.head=1;
    const P=mlPool(g.cav),r=cellScore(SEL_M,P,!!pre.head,cells,Qml);evo={m:mlCorrect(SEL_M,r.m,pre.fam,P,cells).m,g,fam:pre.fam,from:pre.seed,cnt:pre.cnt,nch:pre.cnt.add+pre.cnt.gro,head:!!pre.head,pre:pre.name}}}
  // (속도, 2026-11-28) 미리 만든 설계가 있으면 아래 출발점 찾기(유량 계산 여러 번, 4~6초)를 건너뜀
  // 진화: 점수 상위 v17 설계(종류별) 3개에서 출발, 각 500번
  // 진화 출발점: 점수 상위 v17 설계 중 실측 모양과 겹침 85 % 미만인 것(종류별 1개, 최대 3개) — 이미 돌려 본 모양에서 출발하면 새 모양이 안 나옴
  const libS=ML_LIB.S.filter(s=>!s.head).map(s=>mlPool(mlRLE(s.cav,AG*AG))),evoStarts=[],famE=new Set();
  if(!evo){const fl=G&&G.fQ?G.fQ(Qml):(G&&G.f),Qt=Qml*1e-6/60;let tested=0;   // 출발 모양은 v17 유량 계산(quick)이 되는 것만 — 안 되는 모양에서 진화하면 결과도 안 됨
    for(const r of res){if(evoStarts.length>=3||tested>=10)break;if(famE.has(r.fam))continue;let g=null;try{g=r.make()}catch(e){}if(!g)continue;const P=mlPool(g.cav);if(libS.some(L=>mlIoU(P,L)>=.85))continue;
      tested++;let sol=null;try{sol=flowSolve(mlCloneG(g),S.inl,Qt,fl,true)}catch(e){}if(!(sol&&isFinite(sol.Rl)&&sol.conv)){try{sol=flowSolve(mlCloneG(g),S.inl,Qt,fl,false)}catch(e){}}   /* quick 실패 → 정식 */if(prog)prog(jobs.length+C.length,jobs.length+C.length,'출발');await new Promise(r=>setTimeout(r));if(alive&&!alive())return null;
      if(!(sol&&isFinite(sol.Rl)&&sol.conv))continue;famE.add(r.fam);evoStarts.push({fam:r.fam,name:r.name,make:r.make})}}
  if(!evo){const sw=v=>v===1?2:v===2?1:0,libH=[...Object.values(ML_LIB.strip).map(p=>mlMasks(p).P.map(sw)),...ML_LIB.S.filter(s=>s.head).map(s=>mlPool(mlRLE(s.cav,AG*AG)))];let k=0;   // 띠형 출발: 제작 검사 통과 + 실측 띠와 85 % 미만으로 겹치는 상위 모양 1개
    for(const x of stripAll.slice(0,40)){const c=mlStripCand(x.p,'');if(!c.g||aCheck(c.g))continue;const P=mlPool(c.g.cav);if(libH.some(L=>mlIoU(P,L)>=.85))continue;const p=x.p;evoStarts.push({fam:'띠형',head:true,name:'띠형',make:()=>mlStripCand(p,'').g});break}}
  if(!evo&&Fall[0]){const x=Fall[0];evoStarts.push({fam:'F형',head:true,name:'F형',make:()=>mlStripCand(x.p,'',mlMasksF(x.p,x.side),x.side).g})}
  if(!evo)evo=await mlEvolve(evoStarts,cells,Qml,400,alive,prog?(i,t)=>prog(jobs.length+C.length+i,jobs.length+C.length+t,'진화'):null);
  if(alive&&!alive())return null;
  const out=[];if(evo){const G=evo.g,c=evo.cnt,nm=`머신러닝 새 설계 ${evo.pre?evo.pre+' ':''}(${evo.fam}에서 진화 · 슬롯 +${c.add} · 홈 +${c.gro})`;out.push(evo.head?{kind:'hdr',evo:true,m:evo.m,g:G,name:nm}:{kind:'v17',evo:true,m:evo.m,spec:{fam:evo.fam,name:nm,make:()=>mlCloneG(G),mlopt:true}})}
  const libP=ML_LIB.S.filter(s=>!s.head).map(s=>mlPool(mlRLE(s.cav,AG*AG)));
  for(const o of opts){if(o.kind==='v17'){let g=null;try{g=o.spec.make()}catch(e){}if(g&&libP.some(L=>mlIoU(mlPool(g.cav),L)>=.85))continue}out.push(o)}   // 실측 모양과 거의 같은 설계는 1위 후보에서 뺌
  return {opts:out.slice(0,5),lib:lib.slice(0,5),n:n+(evo?1500:0),m:out.length?out[0].m:Infinity,evo};
}
// ★ 머신러닝 새 설계(진화): 좋은 설계에서 출발해 슬롯 더하기·지우기·홈 늘리기를 수백 번 시도.
//   매번 v17 제작 검사(aCheck: 벽 0.2 mm·물길 연결·포트)를 통과하고 머신러닝 점수(칸 모델+실측 보정)가 좋아지면 받아들임(담금질).
//   지금까지 돌려 본 모양과 겹침이 85 % 이상이면 '새 모양'이 아니므로 1위로 쓰지 않음.
function mlRng(seed){let a=seed>>>0;return ()=>{a=(a+0x6D2B79F5)>>>0;let t=a;t=Math.imul(t^(t>>>15),t|1);t^=t+Math.imul(t^(t>>>7),t|61);return ((t^(t>>>14))>>>0)/4294967296}}
function mlCloneG(g){const h=aGeo();h.cav.set(g.cav);h.gro.set(g.gro);h.pin=g.pin.map(p=>p.slice());h.pout=g.pout.map(p=>p.slice());for(const k of ['ts','head','chy','ns'])if(g[k]!==undefined)h[k]=Array.isArray(g[k])?g[k].slice():(typeof g[k]==='object'?{...g[k]}:g[k]);return h}
function mlIoU(A,B){let a=0,u=0;for(let i=0;i<A.length;i++){const p=A[i]>0,q=B[i]>0;if(p&&q)a++;if(p||q)u++}return u?a/u:0}
async function mlEvolve(starts,cells,Q,iters,alive,prog){
  const rnd=mlRng([...cells.join('')].reduce((a,c)=>a*31+c.charCodeAt(0),7)),libP=[];
  {const seen=new Set();for(const s of ML_LIB.S){if(s.head)continue;const k=JSON.stringify(s.cav);if(seen.has(k))continue;seen.add(k);libP.push(mlPool(mlRLE(s.cav,AG*AG)))}}
  const libH=[];{const sw=v=>v===1?2:v===2?1:0;for(const p of Object.values(ML_LIB.strip))libH.push(mlMasks(p).P.map(sw));for(const p of Object.values(ML_LIB.F))for(const sd of ['bottom','top']){const mk=mlMasksF(p,sd);if(mk)libH.push(mk.P.map(sw))}for(const s of ML_LIB.S)if(s.head)libH.push(mlPool(mlRLE(s.cav,AG*AG)))}
  let curHead=false;const novel=P=>(curHead?libH:libP).every(L=>mlIoU(P,L)<.85);
  const score=g=>{const P=mlPool(g.cav),r=cellScore(SEL_M,P,!!g.head,cells,Q);if(r.out)return null;return {m:mlCorrect(SEL_M,r.m,starts.fam||'',P,cells).m,P}};
  const pick=(L,n)=>{for(let t=0;t<80;t++){const ix=(rnd()*AG)|0,iy=(rnd()*AG)|0;if(L[iy*AG+ix]===n)return [(ix+.5)*AR,(iy+.5)*AR]}return null};
  const ops=[
    (h,c)=>{const n=rnd()<.5?1:2,a=pick(rnd()<.5?h.gro:h.cav,n);if(!a)return false;const w=[.3,.4,.6][(rnd()*3)|0],L=.8+rnd()*3.2;aRect(h,h.cav,Math.max(XL,a[0]-L/2),Math.max(.6,a[1]-w/2),Math.min(XR,a[0]+L/2),Math.min(11.4,a[1]+w/2),n);c.add++;return true},   // 가로 슬롯 더하기(채널을 가로지름)
    (h,c)=>{const n=rnd()<.5?1:2,a=pick(h.cav,n);if(!a)return false;const r=.25+rnd()*.6;for(let iy=aC0(a[1]-r);iy<=aC1(a[1]+r);iy++)for(let ix=aC0(a[0]-r);ix<=aC1(a[0]+r);ix++){const k=iy*AG+ix;if(h.cav[k]===n)h.cav[k]=0}c.cut++;return true},   // 슬롯 일부 지우기
    (h,c)=>{const n=rnd()<.5?1:2,a=pick(h.gro,n);if(!a)return false;const L=1+rnd()*2.5,hz=rnd()<.5;const cl=v=>Math.max(.6,Math.min(11.4,v));hz?aRect(h,h.gro,cl(a[0]-L/2),cl(a[1]-.4),cl(a[0]+L/2),cl(a[1]+.4),n):aRect(h,h.gro,cl(a[0]-.4),cl(a[1]-L/2),cl(a[0]+.4),cl(a[1]+L/2),n);   /* 판 가장자리에서 0.6 mm 안쪽만 (바깥벽 두께) */c.gro++;return true}];   // 덮개 홈 늘리기
  let best=null,k=0;const tot=starts.length*iters,snaps=[];const D=window.ML_DBG={starts:[],tries:0,opok:0,chk:0,acc:0,snaps:0,solves:[]};
  for(const st of starts){starts.fam=st.fam;curHead=!!st.head;let g;try{g=st.make()}catch(e){D.starts.push([st.fam,'make 실패']);continue}if(!g||aCheck(g)){D.starts.push([st.fam,'검사 실패 '+(g&&aCheck(g))]);continue}let cur=score(g);D.starts.push([st.fam,cur?'점수 '+cur.m.toFixed(3):'범위 밖']);if(!cur)continue;let cnt={add:0,cut:0,gro:0};
    for(let i=0;i<iters;i++,k++){if(k%60===59){if(prog)prog(k+1,tot);await new Promise(r=>setTimeout(r));if(alive&&!alive())return null}
      if(cnt.add+cnt.cut+cnt.gro>=(st.head?20:12))break;   // v17 형은 12번, 헤더형(띠·F)은 20번 바꾸면 멈춤: 너무 복잡하면 v17 유량 계산이 수렴하지 않음
      const h=mlCloneG(g),c={...cnt};h.bad=null;D.tries++;const op=ops[rnd()<.6?0:2];if(!op(h,c)||h.bad)continue;D.opok++;if(aCheck(h))continue;D.chk++;   // 지우기(ops[1])는 얇은 조각을 남겨 유량 계산이 깨져서 안 씀
     const sc=score(h);if(!sc)continue;
      const T=.03*Math.pow(.02,i/iters);if(sc.m<cur.m||rnd()<Math.exp(-(sc.m-cur.m)/T)){g=h;cur=sc;cnt=c;D.acc++;
        if((cnt.add+cnt.cut+cnt.gro)>=3&&novel(sc.P)){best={m:sc.m,g:mlCloneG(h),fam:st.fam,from:st.name,cnt:{...cnt},nch:cnt.add+cnt.cut+cnt.gro,head:!!st.head};snaps.push(best);D.snaps++}}}}
  // 유량 계산(v17 flowSolve, quick)이 되는 것 중 가장 좋은 것 — 복잡한 모양은 수렴 안 할 수 있어 좋은 순으로 최대 10개 시험
  snaps.sort((a,b)=>((b.nch>=5)-(a.nch>=5))||a.m-b.m);const fl=G&&G.fQ?G.fQ(Q):(G&&G.f),Qt=Q*1e-6/60;   // 5번 이상 바뀐(더 새로운) 모양 먼저, 그다음 3~4번
  for(const sn of snaps.slice(0,16)){let sol=null;try{sol=flowSolve(mlCloneG(sn.g),S.inl,Qt,fl,true)}catch(e){}if(!(sol&&isFinite(sol.Rl)&&sol.conv)){try{sol=flowSolve(mlCloneG(sn.g),S.inl,Qt,fl,false)}catch(e){}}   /* quick 이 수렴 못 하면 정식 계산 (바람개비형 등) */D.solves.push(sol?[sol.conv,isFinite(sol.Rl)]:null);if(sol&&isFinite(sol.Rl)&&(sol.conv||sn.head))return sn;   /* 헤더형은 기존 띠형 후보와 같은 기준(값이 유한하면 사용) */await new Promise(r=>setTimeout(r));if(alive&&!alive())return null}
  return null}
// 실측 모양 목록 → 점수 (낮을수록 시원할 것). 그 핫스팟·유량(±3 mL/min)에서 돌려 본 적 있으면 실측값을 씀
function mlRLE(a,n){const o=new Uint8Array(n);let k=0;for(let i=0;i<a.length;i+=2){o.fill(a[i],k,k+a[i+1]);k+=a[i+1]}return o}
function mlMeasured(name,cells,Q){const t=ML_LIB.meas[name];if(!t)return null;const k=cells.exact===false?cells.sig:cells.slice().sort().join('+');   /* 칸에 안 맞는 배치는 똑같은 배치의 실측만 */let b=null;for(const [h,q,T] of t)if(h===k&&Math.abs(q-Q)<=3)b=T;return b}
function mlLibrary(cells,Q){const out=[],sw=v=>v===1?2:v===2?1:0,sc=(name,P,head,fam,extra)=>{const r=cellScore(SEL_M,P,head,cells,Q),meas=mlMeasured(name,cells,Q);
    out.push({name,meas,out:r.out,m:meas!=null?Math.log(meas-20):mlCorrect(SEL_M,r.m,fam,P,cells).m,...extra})};
  const seenS=new Set();for(const s of ML_LIB.S){const key=JSON.stringify([s.cav,s.gro]);if(seenS.has(key))continue;seenS.add(key);sc(s.name,mlPool(mlRLE(s.cav,AG*AG)),!!s.head,s.fam,{kind:s.head?'H':'S',s})}   // 같은 모양(S6=S7)은 하나만 — 그 핫스팟 실측이 있는 쪽은 mlMeasured 가 이름으로 찾음
  for(const [k,p] of Object.entries(ML_LIB.strip))sc(k,mlMasks(p).P.map(sw),true,'띠형',{kind:'strip',p});
  for(const k of ML_LIB.P||[]){const d=DESIGNS.find(q=>q.k===k);if(!d||mlMeasured(k,cells,Q)==null)continue;let P=null;try{P=d.head?Uint8Array.from(d.P):mlPool(presetGeo(d).cav)}catch(e){}if(P)sc(k,P,!!d.head,k,{kind:'P',head:!!d.head,pname:d.name})}   // 실측 프리셋 (돌려 본 핫스팟만, 실측값으로 순위)
  const rows=cells.map(c=>+c.split('_')[0]),side=rows.every(r=>r===4)?'top':'bottom';
  for(const [k,p] of Object.entries(ML_LIB.F)){const mk=mlMasksF(p,side);if(mk)sc(k,mk.P.map(sw),true,'F형',{kind:'F',p,side})}
  return out.sort((a,b)=>((a.out>0)-(b.out>0))||a.m-b.m)}
// 실측 헤더형 프리셋(M1·M3) → 계산 엔진 후보 (mlStripCand 와 같은 방식)
function mlPresetCand(k,name){const d0=DESIGNS.find(q=>q.k===k);if(!d0)return null;const d={...d0,k:'A',name:'자동 최적 매니폴드',note:name};const g=presetGeo(d);if(!g||!port_ok(g))return null;
  g.ns={kCav:11,kGro:19,kSolidTop:11,kEval:29,nz:49,CY:[1.5,10.5],head:1};d.flow=makeFlow(g,null,null);return {name,d,g}}
// 실측 헤더형 새 설계(N, head) → 계산 엔진 후보
function mlLibH(s,name){const g=aGeo();g.cav.set(mlRLE(s.cav,AG*AG));g.gro.set(mlRLE(s.gro,AG*AG));g.pin=s.pin.map(p=>p.slice());g.pout=s.pout.map(p=>p.slice());g.head=1;return mlDFromG(g,name)}
// (속도) 1위 새 설계가 계산까지 됐는지 — 됐으면 예비 설계(새 설계가 실패할 때만 쓰는 것)는 유량장을 풀지 않음
function mlEvoOK(list,mo){return !!(mo&&mo.evo&&(mo.evo.head||list.some(c=>c.d&&/^머신러닝 새 설계/.test(c.name))))}
// 실측 S 모양 → 계산 엔진 형상(g)
function mlLibSpec(s,name){return {fam:s.fam,name,make:()=>{const g=aGeo();g.cav.set(mlRLE(s.cav,AG*AG));g.gro.set(mlRLE(s.gro,AG*AG));g.pin=s.pin.map(p=>p.slice());g.pout=s.pout.map(p=>p.slice());return g}}}
function mlLibName(x){if(x.kind==='P')return `실측 모양 ${x.name} · ${x.pname} (프리셋)`;const fam=(x.kind==='S'||x.kind==='H')?x.s.base:x.kind==='F'?`F형 (핫스팟 줄 전용 입구${x.side==='top'?' · 위':' · 아래'}) · 띠 ${x.p.n}개`:`띠형 · 띠 ${x.p.n}개 · 폭 ${x.p.wf.toFixed(2)}`;return `실측 모양 ${x.name} · ${fam}`}
// 화면용 이름 (2026-11-28, 사용자: "머신러닝 새 설계·실측 모양 말고 매니폴드 형상에 맞는 이름, 새 설계는 '자동 최적화 모양'"). ML_NICE 가 켜진 판(v23)만 c.name 을 바꿈. c.base(안쪽 이름)는 그대로.
var ML_NICE=false,ML_CALC=false;
// 모양 설명(규칙·띠·F 이름) → [형상 이름, 나머지 설명]
function mlShapeOf(all){all=(all||'').replace(/ ?\(이 핫스팟 실측 [^)]*\)/,'');const fam=all.split(' · ')[0].split(' (')[0],g=re=>{const x=all.match(re);return x?x[1]:null},rest=()=>all.split(' · ').slice(1).filter(x=>!/^[^()]*\)$/.test(x)&&!/SimScale 학습 가족/.test(x));
  if(/^F형/.test(all)){const n=g(/띠 (\d+)개/);return ['F형 (핫스팟 줄 전용 입구)',n?[`띠 ${n}개`]:[]]}
  if(fam==='띠형'){const n=g(/띠 (\d+)개/),w=g(/폭 ([\d.]+)/);return [`가로 띠형 ${n}줄`,[...(w?[`띠 폭 비율 ${w}`]:[]),...rest().filter(x=>!/^띠 \d+개$|^폭 [\d.]+$/.test(x))]]}
  if(fam==='V자 빗살형'){const w=g(/빗살 폭 ([\d.]+)/),q=g(/간격 ([\d.]+)/);return w?[`V자 빗살형 (폭 ${w} · 간격 ${q})`,[`빗살 폭 ${w} mm`,`간격 ${q} mm`]]:[fam,rest()]}
  if(fam==='바람개비형'){const w=g(/슬롯 ([\d.]+) mm/);return [w?`바람개비형 (슬롯 ${w})`:fam,rest()]}
  if(fam==='흡입형')return ['흡입형 (핫스팟 위 배출)',rest()];
  if(fam==='직상부 공급형')return ['직상부 공급형',rest()];
  return [fam,rest()]}
function mlNiceOf(c){const b=c.base||c.name||'';let m;
  if((m=b.match(/^머신러닝 새 설계(?: (N\d+))? ?\((.*?)에서 진화(?: · (.*))?\)$/)))return [({D1:'말굽형'}[m[2]]||m[2].replace(/형$/,'')+'형')+' 진화형',[m[3],m[1]?`설계 번호 ${m[1]}`:''].filter(Boolean).join(' · ')];
  if((m=b.match(/^실측 모양 (\S+) · (.*)$/))){const id=m[1],all=m[2];let t,det;
    if(/머신러닝 새 설계/.test(all)){const f=all.split(' · ')[0];t=({D1:'말굽형'}[f]||f)+' 진화형';det=[]}
    else if(/\(프리셋\)/.test(all)){t=all.split(' (')[0]+(id==='M1'||id==='M3'?' (헤더형)':'');det=[]}
    else [t,det]=mlShapeOf(all);
    return [t,[...det,`SimScale 실행 ${id}`].join(' · ')]}
  const [t,det]=mlShapeOf(b.replace(/^머신러닝 설계 · /,'').replace(/^실측 \S+ · /,''));return [t,det.join(' · ')]}
// 순위대로 이름 붙이기: 1위 = '자동 최적화 모양'(설명 줄에 형상 이름), 2위부터 = 형상 이름. 같은 이름이 겹치면 ①②
function mlNiceApply(order){if(!ML_NICE)return;const N=order.map(mlNiceOf),cnt={};N.forEach((x,i)=>{if(i)cnt[x[0]]=(cnt[x[0]]||0)+1});const k={};
  order.forEach((c,i)=>{let [t,sub]=N[i];if(i===0){sub=[t,sub].filter(Boolean).join(' · ');t='자동 최적화 모양'}else if(cnt[t]>1){k[t]=(k[t]||0)+1;t+=' '+'①②③④⑤'[k[t]-1]}
    if(c.sameAs&&i===0)sub+=` · SimScale 실행 ${c.sameAs}와 같은 모양`;if(c.meas!=null)sub+=` · 이 핫스팟 실측 ${c.meas.toFixed(1)} °C`;c.nice=[t,sub];c.name=`${i+1}위 ${t}${sub?' · '+sub:''}`})}
// ★ 계산 순위 (v23 판, 2026-11-28 사용자: "자동 최적화가 무조건 냉각이 제일 잘 돼야 한다"). 머신러닝 점수만으로 1위를 정하면 앱 계산으로 더 뜨거운 모양이 1위가 될 수 있었음
//   (예: 원본 v23 이 80.7 °C 를 고르는 배치에서 86.4 °C 가 1위). 그래서: 후보 = 머신러닝이 만든 모양 + 실측 모양 + 원본 v23 규칙 모양,
//   1위 = 그중 간단 계산 최고 온도가 가장 낮은 것(원본 v23 의 선택 규칙: 한도 만족 우선 → 최저 온도 → 0.5 °C 이내면 압력강하 작은 쪽) → 원본보다 나빠질 수 없음.
//   2~5위 = 실측 모양만(머신러닝이 고른 5개 중 계산이 유효한 것, 계산 온도 순). 모자라면 그만큼 적게 보임.
function mlRankCalc(ok){const val=ok.filter(c=>c.r&&validR(c.r)),pool=val.length?val:ok.filter(c=>c.r);if(!pool.length)return;
  const fe=pool.filter(c=>feas(c.r)),pl=fe.length?fe:pool,tm=Math.min(...pl.map(c=>c.r.Tmax)),first=pl.filter(c=>c.r.Tmax<=tm+.5).reduce((a,b)=>a.r.dp<=b.r.dp?a:b);
  const byT=(a,b)=>a.r.Tmax-b.r.Tmax,isLib=c=>/^실측 모양/.test(c.base),rest=pool.filter(c=>c!==first);
  const more=ok.filter(c=>c.r&&c!==first&&isLib(c)).sort((a,b)=>(validR(b.r)-validR(a.r))||byT(a,b)).slice(0,4),order=[first,...more];   // 계산이 '유효하지 않음'(예: 물 95 °C 초과로 계산 범위 밖)으로 나온 실측 모양도 뒤쪽에 보여 줌(카드에 한도 경고)   // 2~5위는 실측 모양만. 유효한 실측 모양이 모자라도 자동 설계 모양으로 채우지 않음(사용자: "이거 자동설계 아냐?")
  for(const c of ok){c.hide=true;c.ml=undefined}order.forEach((c,i)=>{c.hide=false;c.ml=i+1});mlNiceApply(order);
  if(!ML_NICE)order.forEach((c,i)=>{c.name=`${i+1}위 ${c.base}`});
  AUTO.calcKey=AUTO.key;AUTO.calcN=pool.length}
// 3D 계산 뒤 더 시원한 후보가 1위가 아니면 1위로 올림
function mlPromote(c){const order=AUTO.cands.filter(x=>x.ml&&!x.hide).sort((a,b)=>a.ml-b.ml);if(!order.includes(c)||order[0]===c)return;const o2=[c,...order.filter(x=>x!==c)];o2.forEach((x,i)=>{x.ml=i+1});mlNiceApply(o2)}
// 순위: 1위 = 머신러닝 설계(계산된 것 중 점수 최고), 2~5위 = 실측 모양. 나머지는 숨김
function mlRank(ok,hs,Q){const cells=mlCells(hs);
  for(const c of ok){if(!c.base)c.base=c.name;if(!ML_CALC){c.hide=false;c.ml=undefined}
    const nm=(c.base.match(/실측 (?:모양 )?(\S+) · /)||[])[1];c.meas=nm?mlMeasured(nm,cells,Q):null;
    try{const r=cellScore(SEL_M,c.d.P,!!c.d.head,cells,Q),f0=mlFamOf(c.base.replace(/^(머신러닝 설계 · )?실측 (모양 )?\S+ · /,'')),fam=f0==='F형'?'F형':(c.d.head?'띠형':f0),k=mlCorrect(SEL_M,r.m,fam,c.d.P,cells);
      c.mls=c.meas!=null?Math.log(c.meas-20):k.m;c.mlOut=r.out}catch(e){c.mls=Infinity}}
  if(ML_CALC)return;   // 계산 순위 판(v23): 순위는 간단 계산 뒤 mlRankCalc 가 정함
  const by=(a,b)=>((a.mlOut>0)-(b.mlOut>0))||a.mls-b.mls;
  const opt=ok.filter(c=>/^머신러닝 (설계|새 설계)/.test(c.base)).sort((a,b)=>(/^머신러닝 새 설계/.test(b.base)-/^머신러닝 새 설계/.test(a.base))||by(a,b)),lib=ok.filter(c=>/^실측 모양/.test(c.base)).sort(by);
  const first=opt[0];opt.slice(1).forEach(c=>c.hide=true);
  // 1위 설계가 실측 모양과 똑같으면: 그 실측 모양은 목록에서 빼고 1위 이름에 표시
  let lib2=lib;if(first){const key=c=>c.d.P.join(''),fk=key(first),same=lib.find(c=>key(c)===fk);if(same){first.sameAs=(same.base.match(/실측 모양 (\S+)/)||[])[1];if(first.meas==null)first.meas=same.meas;same.hide=true;lib2=lib.filter(c=>c!==same)}}
  const order=[...(first?[first]:[]),...lib2.slice(0,first?4:5)];lib2.slice(first?4:5).forEach(c=>c.hide=true);
  ok.filter(c=>!/^(머신러닝 설계|머신러닝 새 설계|실측 모양)/.test(c.base)).forEach(c=>c.hide=true);
  order.forEach((c,i)=>{c.ml=i+1;c.name=c===first?`1위 ${/^머신러닝 새 설계/.test(c.base)?c.base:'머신러닝 최적 · '+c.base.replace(/^머신러닝 설계 · /,'')}${c.sameAs&&!/실측 /.test(c.base)?` (= 실측 ${c.sameAs}와 같은 모양)`:''}${c.meas!=null?` (이 핫스팟 실측 ${c.meas.toFixed(1)} °C)`:''}`:`${i+1}위 ${c.base}${c.meas!=null?` (이 핫스팟 실측 ${c.meas.toFixed(1)} °C)`:''}`});mlNiceApply(order)}
</script>
'''

def rep(s, old, new):
    assert s.count(old) == 1, old[:60]
    return s.replace(old, new)

# 1) 계산 엔진(calcB) 블록 바로 다음에 삽입
cb = src.index('<script id="calcB">'); ce = src.index('</script>', cb) + len('</script>')
src = src[:ce] + '\n' + ML.rstrip('\n') + src[ce:]
# 2) autoDesign: 띠·F 형 설계안과 실측 띠·F 모양을 후보에 넣음 (v17·S 모양은 2b 에서 specs 로)
a = src.index("    AUTO.key=key;AUTO.cands=list;")
src = src[:a] + (
    "    // ← ML: 1위 후보(띠·F 설계)와 2~5위 후보(실측 띠·F 모양)\n"
    "    AUTO.ml={list:[]};{const mo=AUTO.mlopt||{opts:[],lib:[]};\n"
    "      for(const o of mo.opts){if((o.kind==='strip'||o.kind==='F')&&!ML_CALC&&mlEvoOK(list,mo))continue;if(o.kind==='hdr'){const c=mlDFromG(o.g,o.name);if(c)list.push({name:o.name,g:c.g,d:c.d})}if(o.kind==='strip'||o.kind==='F'){const c=o.kind==='F'?mlStripCand(o.p,'머신러닝 설계 · ',mlMasksF(o.p,o.side),o.side):mlStripCand(o.p,'머신러닝 설계 · ');if(c.d)list.push({name:o.same?'머신러닝 설계 · '+mlLibName(o).replace(/^실측 모양 /,'실측 '):c.name,g:c.g,d:c.d,p:c.p})}}\n"
    "      for(const x of mo.lib){if(x.kind==='P'&&x.head){const c=mlPresetCand(x.name,mlLibName(x));if(c)list.push(c)}if(x.kind==='H'){const c=mlLibH(x.s,mlLibName(x));if(c)list.push({name:mlLibName(x),g:c.g,d:c.d})}if(x.kind==='strip'||x.kind==='F'){const c=x.kind==='F'?mlStripCand(x.p,'',mlMasksF(x.p,x.side),x.side):mlStripCand(x.p,'');if(c.d)list.push({name:mlLibName(x),g:c.g,d:c.d,p:c.p})}}}\n") + src[a:]
# 2b) 머신러닝 최적 매니폴드를 먼저 설계해서 후보 맨 앞에 넣음
src = rep(src, "const hs=HSN.map(h=>({...h})),specs=autoSpecs(hs).filter(q=>S.direct||q.fam!=='직상부 공급형'),list=[],seen=new Set();",
          "const hs=HSN.map(h=>({...h})),specs=autoSpecs(hs).filter(q=>S.direct||q.fam!=='직상부 공급형'),list=[],seen=new Set();\n    st('머신러닝이 이 핫스팟에 맞는 최적 매니폴드를 설계하는 중입니다 (모양 수천 개 시험)');await tick();if(my!==token)return false;\n    let mo=null;try{mo=await mlOptimize(hs,S.Q,!!S.direct,()=>my===token,(i,n,ph)=>st(ph?`머신러닝이 새 모양을 진화시키는 중입니다 (시도 ${i}/${n})`:`머신러닝이 이 핫스팟에 맞는 최적 매니폴드를 설계하는 중입니다 (모양 ${i}/${n}개 시험)`))}catch(e){mo=null}if(my!==token)return false;AUTO.mlopt=mo;const origS=ML_CALC?specs.slice():[];specs.length=0;if(mo){const fbS=[];for(const o of mo.opts){const sp=o.kind==='v17'?o.spec:o.kind==='S'?mlLibSpec(o.s,'머신러닝 설계 · '+mlLibName(o).replace(/^실측 모양 /,'실측 ')):null;if(!sp)continue;if(mo.evo&&!o.evo){sp.fb=!ML_CALC;fbS.push(sp)}else specs.push(sp)}for(const x of mo.lib){if(x.kind==='S')specs.push(mlLibSpec(x.s,mlLibName(x)));if(x.kind==='P'&&!x.head){const k=x.name;specs.push({fam:k,name:mlLibName(x),make:()=>presetGeo(DESIGNS.find(q=>q.k===k))})}}specs.push(...fbS)}specs.push(...origS);   /* 순서: 새 설계 → 실측 모양 → 머신러닝 다른 설계 → (계산 순위 판) 원본 v23 규칙 모양. fb 는 새 설계가 실패했을 때만 계산 */   // ← ML: 후보 = 머신러닝 설계 + 실측 모양 (원래 v17 후보는 뺌)")
# 4) 헤더형 그대로 전달
_o = "Object.assign(AUTOD,{T:d.T,U:d.U,P:d.P,ports:d.ports,head:0,"
assert src.count(_o) == 2          # autoDesign 과 nsStage 두 곳
src = src.replace(_o, "Object.assign(AUTOD,{T:d.T,U:d.U,P:d.P,ports:d.ports,head:d.head||0,   /* ← ML: 머신러닝 모양은 헤더형 */")
# 7) 계산식이 '유효하지 않음'(예: 물 95 °C 초과)이라고 해도 머신러닝 모양은 버리지 않고 표시 (경고는 원래 문구 그대로)
src = rep(src, "  const okv=ok.filter(c=>validR(c.r));\n",
          "  const okv=ok.filter(c=>validR(c.r));\n  if(!okv.length&&AUTO.ml&&ok.length)okv.push(...ok.filter(c=>c.r));   // ← ML: 모양은 머신러닝이 정함 → 계산식 판정과 상관없이 표시\n")
# 8) 상태 문장: 선택은 머신러닝 1위 (머신러닝 예상 온도는 표시 안 함)
src = rep(src, "st(AUTO.pick!=null?'직접 고른 모양입니다. 핫스팟을 옮기면 다시 자동으로 고릅니다.':`${S.direct?'':'직상부 공급형을 뺀 '}후보 ${ok.length}개를 계산해 전체 최고 온도가 가장 낮은 모양을 골랐습니다. 차이가 0.5 °C 이내면 압력강하가 작은 쪽입니다.`);",
          "st(AUTO.pick!=null?'직접 고른 모양입니다. 핫스팟을 옮기면 다시 자동으로 고릅니다.':(best&&best.ml?(ML_CALC?`후보 ${AUTO.calcN||ok.length}개(머신러닝이 만든 모양 · SimScale 로 돌려 본 모양 · 규칙 모양)를 이 에이전트 계산식으로 계산해, 최고 온도가 가장 낮은 모양을 1위(자동 최적화 모양)로 골랐습니다. 2~5위는 SimScale 로 돌려 본 모양 중 계산 온도가 낮은 순서입니다.`:`머신러닝(지금까지 SimScale 실측으로 학습)이 이 핫스팟에 맞춰 모양 ${AUTO.mlopt&&AUTO.mlopt.n||0}개를 그려 보고, 가장 좋은 설계에서 슬롯을 더하고 홈을 늘려 가며 새 모양으로 진화시켰습니다(1위, 지금까지 돌려 본 모양과 다른 새 모양). 2~5위는 지금까지 SimScale 로 돌려 본 매니폴드 중 머신러닝이 고른 것입니다(이 핫스팟에서 돌려 본 것은 실측값 기준). 온도·압력은 이 에이전트 계산식 값입니다.`):`${S.direct?'':'직상부 공급형을 뺀 '}후보 ${ok.length}개를 계산해 전체 최고 온도가 가장 낮은 모양을 골랐습니다. 차이가 0.5 °C 이내면 압력강하가 작은 쪽입니다.`));   // ← ML")
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
src = rep(src, "if(!best){const lam=okv.filter(c=>feas(c.r))", "if(ML_CALC&&AUTO.ml)mlRankCalc(ok);   // ← ML: 계산 순위 판 — 간단 계산이 끝난 지금 순위를 정함\n  if(!best&&AUTO.ml){best=ok.find(c=>c.ml===1&&c.r)||null}   // ← ML: 선택은 1위\n  if(!best){const lam=okv.filter(c=>feas(c.r))")
# 12) 3D NS 대상: 머신러닝 1·2위
src = rep(src, "let top=top0.slice(0,NS_K);", "let top=AUTO.ml&&AUTO.cands.some(c=>c.ml)?AUTO.cands.filter(c=>c.ml&&c.d&&c.g&&c.r).sort((a,b)=>a.ml-b.ml).slice(0,NS_K):top0.slice(0,NS_K);   // ← ML: 머신러닝 1·2위")
src = rep(src, "간이 모델 상위 후보 ${top.length}개", "${top.some(c=>c.ml)?'머신러닝':'간이 모델'} 상위 후보 ${top.length}개")
# 13) 3D 뒤 최종 선택도 머신러닝 1위 (3D 결과가 유효하면)
src = rep(src, "const b=pl.filter(x=>x.ns.Tmax<=tm+.5).reduce((p,q)=>p.ns.dp<=q.ns.dp?p:q),d=b.c.d;",
          "const b=(ML_CALC?null:cand.find(x=>x.c.ml===1))||pl.filter(x=>x.ns.Tmax<=tm+.5).reduce((p,q)=>p.ns.dp<=q.ns.dp?p:q);if(ML_CALC&&AUTO.pick==null)mlPromote(b.c);const d=b.c.d;   // ← ML: 머신러닝 1위 / 계산 순위 판은 3D 로 더 시원한 쪽을 1위로")
src = rep(src, "st(`3D 나비에–스토크스 + 열전달로 상위 후보 ${cand.length}개를 다시 풀어 최고 온도가 가장 낮은 모양을 골랐습니다(0.5 °C 이내면 압력강하가 작은 쪽). [${tbl}]",
          "st((b.c.ml?(ML_CALC?`3D 나비에–스토크스 + 열전달로 1·2위 후보 ${cand.length}개를 다시 풀었습니다. 3D 로 더 시원한 쪽이 1위입니다.`:`3D 나비에–스토크스 + 열전달로 머신러닝 상위 후보 ${cand.length}개를 계산했습니다. 선택은 머신러닝 ${b.c.ml}위입니다.`):`3D 나비에–스토크스 + 열전달로 상위 후보 ${cand.length}개를 다시 풀어 최고 온도가 가장 낮은 모양을 골랐습니다(0.5 °C 이내면 압력강하가 작은 쪽).`)+` [${tbl}]")
# 14) 순위: 1위 머신러닝 설계, 2~5위 실측 모양, 나머지 숨김
src = rep(src, "  const ok=AUTO.cands.filter(c=>c.d);\n",
          "  const ok=AUTO.cands.filter(c=>c.d);\n  mlRank(ok,HSN,S.Q);   // ← ML\n")
src = rep(src, "const ok=AUTO.cands.map((c,i)=>({c,i})).filter(x=>x.c.d&&x.c.r).sort((p,q)=>p.c.r.Tmax-q.c.r.Tmax)",
          "const ok=AUTO.cands.map((c,i)=>({c,i})).filter(x=>x.c.d&&x.c.r&&!x.c.hide).sort((p,q)=>(p.c.ml&&q.c.ml)?p.c.ml-q.c.ml:p.c.r.Tmax-q.c.r.Tmax)   /* ← ML: 머신러닝 순위, 5개만 */")
# 5) 후보 유량장: quick 이 수렴 못 하면 정식(quick=false)으로 다시 풂 — 바람개비형·D1 진화형 등은 quick 만 실패함 (2026-11-28, 식은 그대로)
src = rep(src, "const sols=await Promise.all(grp.map(async m=>{try{return FLOW_ASYNC?await FLOW_ASYNC(gSer(m.g),S.inl,Qt,fS,true):flowSolve(m.g,S.inl,Qt,fS,true)}catch(e){return null}}));",
          "const sols=await Promise.all(grp.map(async m=>{try{let s=FLOW_ASYNC?await FLOW_ASYNC(gSer(m.g),S.inl,Qt,fS,true):flowSolve(m.g,S.inl,Qt,fS,true);if(!(s&&isFinite(s.Rl)&&s.conv))s=FLOW_ASYNC?await FLOW_ASYNC(gSer(m.g),S.inl,Qt,fS,false):flowSolve(m.g,S.inl,Qt,fS,false);return s}catch(e){return null}}));   // ← ML: quick 실패 → 정식 풀이")
# 5b) (속도) 예비 설계는 1위 새 설계가 계산까지 됐으면 유량장을 풀지 않음
src = rep(src, "for(let i=0;i<made.length;i+=2){const grp=made.slice(i,i+2);",
          "for(let i=0;i<made.length;i+=2){const grp=made.slice(i,i+2).filter(m=>!(m.sp.fb&&mlEvoOK(list,mo)));if(!grp.length)continue;   // ← ML: 예비 설계 건너뜀")
# 5c) (v23 판만, 2026-11-28 사용자: "① 머신러닝 설계 ② 간단 계산 ③ 상위 2개 3D — 이 순서로 빠르게") 계산 순서 바꿈. 값·식은 그대로.
#   원본: 기존 구조 10개 유량장 재풀이(처음 약 25초) → 자동 설계 → 3D.   바꿈: 자동 설계(머신러닝) → 간단 계산 표시 → 기존 구조 재풀이 → 3D.
#   그동안 기존 구조는 d.flow 를 떼어 저장 유량장(원본의 대체값)으로 임시 계산하고, 재풀이 뒤 원래 값으로 바꿈. 떼고 붙이는 것은 지금 계산(token) 것만.
if VER != "v17":
    src = rep(src, "async function compute(){",
              "ML_NICE=true;ML_CALC=true;let ML_TMP=false;const ML_TMP_NOTE='기존 구조 10개는 유량장을 다시 푸는 중이라 값을 잠시 가렸습니다. 머신러닝 설계(1~5위)를 먼저 보여 드리고, 다 풀리면 표시합니다.';\n"
              "function mlDetach(){for(const d of DESIGNS)if(d.k!=='A'){if(typeof d.flow==='function')d._mlFlow=d.flow;if(d._mlFlow)d.flow=null}}   // ← ML: 기존 구조 유량장 재풀이를 뒤로 미룸\n"
              "function mlAttach(){for(const d of DESIGNS)if(d.k!=='A'&&d._mlFlow)d.flow=d._mlFlow}\n"
              "// 재풀이 전의 기존 구조 값(저장 유량장으로 낸 임시 값)은 화면에서 가림: 그림은 흐리게, 숫자는 '다시 푸는 중…'\n"
              "function mlMarkTmp(){try{const tmp=i=>ML_TMP&&res[i]&&res[i].d&&res[i].d.k!=='A'&&!!res[i].d._mlFlow;\n"
              "  document.querySelectorAll('#tiles .tile[data-i],#cmp tr[data-i]').forEach(el=>el.classList.toggle('mltmp',tmp(+el.dataset.i)));\n"
              "  const v=document.querySelector('.verdict');if(v)v.classList.toggle('mltmp',tmp(sel));\n"
              "  if(ML_TMP)document.querySelectorAll('#warns li').forEach(li=>{if(li.textContent!==ML_TMP_NOTE)li.style.display='none'})}catch(e){}}   // 임시 값으로 만든 경고 문장도 그동안 가림\n"
              "{const st=document.createElement('style');st.textContent='.tile.mltmp svg{opacity:.22}.tile.mltmp small{font-size:0}.tile.mltmp small::after{content:\"다시 푸는 중…\";font:500 12px var(--mono);color:var(--muted)}tr.mltmp td:not(:first-child){color:transparent}tr.mltmp td:nth-child(2)::after{content:\"푸는 중\";color:var(--muted);font:400 12px var(--sans)}.verdict.mltmp .kv b{color:transparent}.verdict.mltmp .kv:first-of-type b::after{content:\"다시 푸는 중…\";color:var(--muted);font:500 14px var(--sans);margin-left:-6em}';document.head.appendChild(st);\n"
              "  const r0=render,d0=drawMaps;render=function(){try{if(typeof mlViewApply==='function')mlViewApply()}catch(e){}const x=r0.apply(this,arguments);mlMarkTmp();return x};drawMaps=function(){const x=d0.apply(this,arguments);mlMarkTmp();return x}}\n"
              "async function compute(){")
    src = rep(src, "let out;try{G=setup(p);await prefetchFlows(DESIGNS,S.Q,'구조별 유량장');if(my!==token)return;out=DESIGNS.map(d=>evaluate(G,d,S.Q,S.t))}catch(e){",
              "let out;try{G=setup(p);mlDetach();ML_TMP=true;out=DESIGNS.map(d=>evaluate(G,d,S.Q,S.t))}catch(e){mlAttach();ML_TMP=false;   /* ← ML: 재풀이는 자동 설계 뒤로 */")
    src = rep(src, "  res=out;FAILS.length=0;render();\n  if(!(await autoDesign(my)))return;\n",
              "  res=out;FAILS.length=0;render();\n  if(!(await autoDesign(my))){if(my===token){mlAttach();ML_TMP=false}return}\n")
    src = rep(src, "  if(!(await nsStage(my)))return;   // ← 16차: 3D NS + 열전달\n",
              "  // ← ML: 이제 기존 구조 10개를 다시 풀어(그 유량에서 처음 한 번, 이후 캐시) 가렸던 값을 표시\n"
              "  mlAttach();await prefetchFlows(DESIGNS.filter(d=>d.k!=='A'),S.Q,'구조별 유량장');if(my!==token)return;\n"
              "  ML_TMP=false;try{res=DESIGNS.map(d=>evaluate(G,d,S.Q,S.t))}catch(e){FAILS.push('재계산 오류: '+(e.message||e))}render();\n"
              "  if(!(await nsStage(my)))return;   // ← 16차: 3D NS + 열전달\n")
    src = rep(src, "  if(FAILS.length)w.push(`계산 중 오류가 난 조건(건너뜀): ", "  if(ML_TMP)w.push(ML_TMP_NOTE);   // ← ML\n  if(FAILS.length)w.push(`계산 중 오류가 난 조건(건너뜀): ")
    # 5e) 떠 있는 알림(계산 중 상자): 긴 문장 대신 짧은 알림, 검은 배경 대신 눈에 띄는 색 (사용자 요청)
    src = rep(src, "h=`<button type=\"button\" aria-label=\"닫기\" data-x>✕</button><b>계산 중</b> · 경과 <b>${mmss(now-Math.max(tBusy,window.__busyT0||0))}</b><br>${esc((st||'구조별 유량 계산').slice(0,110))}`}",
              "h=`<button type=\"button\" aria-label=\"닫기\" data-x>✕</button><b>${esc(mlBusyText(st))}</b> · 경과 <b>${mmss(now-Math.max(tBusy,window.__busyT0||0))}</b>`}   // ← ML")
    src = rep(src, "background:#0B1A2Cee;color:#fff;border-radius:12px;padding:9px 12px;", "background:#FFC53D;color:#0A1F5C;border-radius:12px;padding:10px 14px;")
    src = rep(src, "#liveBox .bar{height:5px;background:#ffffff30;", "#liveBox .bar{height:5px;background:#0A1F5C26;")
    src = rep(src, "#liveBox .bar i{display:block;height:100%;background:#5DD39E;width:0}#liveBox .warn{color:#FFC857}#liveBox button{float:right;background:none;border:0;color:#fff9;",
              "#liveBox .bar i{display:block;height:100%;background:#0B4BD6;width:0}#liveBox .warn{color:#B3192E}#liveBox button{float:right;background:none;border:0;color:#0A1F5C99;")
    # 5g) (속도) 유량장 워커 2개 → 코어 수에 맞춰 최대 6개, 후보 유량장도 그 수만큼 한꺼번에. 풀이 식은 그대로.
    src = rep(src, "for(let i=0;i<2;i++)ws.push(mkW(i))", "for(let i=0,nW=Math.max(2,Math.min(6,((typeof navigator!=='undefined'&&navigator.hardwareConcurrency)||4)-1));i<nW;i++)ws.push(mkW(i))   /* ← ML: 워커 수 */")
    src = rep(src, "fa.state=()=>({dead,pend:pend.size});return fa}", "fa.state=()=>({dead,pend:pend.size});fa.n=ws.length;return fa}")
    src = rep(src, "for(let i=0;i<made.length;i+=2){const grp=made.slice(i,i+2).filter(", "for(let i=0,KW=(FLOW_ASYNC&&FLOW_ASYNC.n)||2;i<made.length;i+=KW){const grp=made.slice(i,i+KW).filter(")
    src = rep(src, "for(let i=0;i<need.length;i+=2){", "for(let i=0,KW=(FLOW_ASYNC&&FLOW_ASYNC.n)||2;i<need.length;i+=KW){")
    src = rep(src, "await Promise.all(need.slice(i,i+2).map(c=>c.d.flow.prefetch(S.Q,fQ).catch(()=>{})));", "await Promise.all(need.slice(i,i+KW).map(c=>c.d.flow.prefetch(S.Q,fQ).catch(()=>{})));")
    # 5f) 사용자 요청: 냉각 유체 버튼의 '(기본)'·제조사 이름 지움, 나노유체 긴 설명 두 문단 지움
    src = rep(src, '<button type="button" data-shfl="w">물<small>(기본)</small></button><button type="button" data-shfl="Al2O3">Al₂O₃ 나노유체<small>(99% · 나비엠알오)</small></button><button type="button" data-shfl="CuO">CuO 나노유체<small>(95% · 덕산화학)</small></button>',
              '<button type="button" data-shfl="w">물</button><button type="button" data-shfl="Al2O3">Al₂O₃ 나노유체</button><button type="button" data-shfl="CuO">CuO 나노유체</button>')
    src = rep(src, '<p class="sh-note" style="margin:12px 0 0">물성(밀도·비열·점도·열전도도)은 이론식(Maxwell·Brinkman)으로, 열전달계수 향상은 마이크로채널 실험 문헌값으로 계산합니다. 문헌의 최대 향상값을 쓰므로 낙관적 예측이며, 실험으로 확인해야 합니다.</p>', '')
    src = rep(src, '<p class="sh-note" id="shLimNote" style="margin:10px 0 0"></p>', '<p class="sh-note" id="shLimNote" hidden></p>')
    # 5h) 사용자 요청: 입력 화면 아래의 '예상 칩 최고 온도 … 계산 중' 칸을 없앰(값을 쓰는 코드는 그대로 두고 숨기기만, '다음' 버튼은 가로로 꽉 차게)
    src = rep(src, '<div class="sh-bar"><div class="sh-pv"><span>예상 칩 최고 온도</span>', '<div class="sh-bar" style="grid-template-columns:1fr"><div class="sh-pv" hidden><span>예상 칩 최고 온도</span>')
    # 5d) 결과 화면(모바일 흐름)을 머신러닝 순위로 — html_v23/ml_shell.js (1위 새 설계 · 2~5위 실측 모양 · 간단 계산 값 · 1·2위는 3D 값으로)
    _a = "shEl('shRail').addEventListener('click',e=>{const b=e.target.closest('[data-pick]');if(!b)return;SH.pick=DESIGNS.find(d=>d.k===b.dataset.pick);shRes()});"
    src = rep(src, _a, _a + "\n" + (VDIR / "ml_shell.js").read_text(encoding="utf-8"))
# 6) 제목
src = rep(src, "<title>핫스팟 에이전트</title>", "<title>핫스팟 에이전트 (ML 매니폴드)</title>" if VER == "v17" else f"<title>핫스팟 에이전트 {VER} (ML 매니폴드)</title>")

(VDIR / f"hotspot_agent_{VER}_ml.html").write_text(src, encoding="utf-8")
print("저장:", VDIR / f"hotspot_agent_{VER}_ml.html", len(src))
# 아티팩트에 올릴 본문 (<body> 안쪽) — new_result.py 와 같은 방식 (2026-11-28: patch_ml 만 돌려도 만들어지게)
_b = src[src.index("<body>") + 6:].lstrip("\n").rstrip()
if _b.endswith("</body></html>"):
    _b = _b[:-14].rstrip()
(VDIR / "artifact_body.html").write_text(_b, encoding="utf-8")
if len(sys.argv) < 2 and (HERE.parent / "html_v23" / "hotspot_agent_v23.html").exists():      # v17 다음에 v23 도
    import subprocess
    print(subprocess.run([sys.executable, str(Path(__file__).resolve()), "v23"], capture_output=True, text=True, check=True).stdout.strip())
