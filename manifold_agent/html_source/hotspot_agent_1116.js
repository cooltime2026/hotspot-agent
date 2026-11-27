/* 핫스팟 에이전트 — 11월 16일 최종 게시본(버전 1794839594-6deb)의 자바스크립트 전체
 * 원본: hotspot_agent_full_v11.html (단일 HTML). 아래 블록 순서대로 페이지에서 실행됨.
 * 제외: <script id="hsdata" type="application/json"> — 미리 풀어 둔 기본 구조 10개의 유량장 숫자 데이터(1.5 MB, 코드 아님)
 */

/* ==========================================================================================
 * 블록 1 — 계산 엔진: 상수, 물성, 구조 목록, 발열 지도 setup, 발달 구간 Nu, evaluate(열·압력 계산)   (HTML 740행부터)
 * ========================================================================================== */
/* ---------- 계산 엔진: 매니폴드 10개의 층류 유량장을 미리 풀어 넣었다. 유량에 비례해 키운다. ---------- */
const Z=12,N=22,NX=120,DY=.1,WC=.25,HC=.4,PITCH=.5,X0=.75,Y0=1.5,Y1=10.5,TB=.1,TL=.2,HCAL=1.0,I0=15,NC=90,Q0=60,TMS=['0.5'],MAP={x:0,y:0,w:12,h:12},CHIP={x0:.625,x1:11.375,y0:1.5,y1:10.5};
/* 물 물성: 기본은 온도 의존(5~95 °C 근사식, 유체 평균 온도에서 평가). 'fixed'는 팀 SimScale 고정값(약 24 °C) */
const WFIX={rho:997.3,cp:4180,kf:.5967,mu:9.313e-4};
const waterT=T=>{T=Math.max(5,Math.min(95,T));return {rho:1000.6-.0186*T-.0046*T*T,cp:4186,kf:.5706+.00175*T-6.46e-6*T*T,mu:2.414e-5*Math.pow(10,247.8/(T+273.15-140))}};
const water=T=>{let fx=false;try{fx=S&&S.wprop==='fixed'}catch(e){}return fx?WFIX:waterT(T)};
const chX=j=>X0+j*PITCH;
const stripEdges=j=>[j===0?0:chX(j)-PITCH/2,j===N-1?Z:chX(j)+PITCH/2];
const stripAt=x=>{for(let j=0;j<N;j++){if(x<stripEdges(j)[1])return j}return N-1};
const poiseuille=a=>24*(1-1.3553*a+1.9467*a*a-1.7012*a**3+.9564*a**4-.2537*a**5);
const nuInf=a=>8.235*(1-2.0421*a+3.0853*a*a-2.4765*a**3+1.0578*a**4-.1861*a**5);
const b64=(s,T)=>{const b=atob(s),u=new Uint8Array(b.length);for(let i=0;i<b.length;i++)u[i]=b.charCodeAt(i);return new T(u.buffer)};
const DESIGNS=[
  {k:'M0',name:'매니폴드 없음',note:'기준: 직선 평행 유로'},
  {k:'M1',name:'중앙 집중 빗살형',note:'중앙이 촘촘한 빗살'},
  {k:'M3',name:'V자 빗살형',note:'V자로 꺾인 빗살'},
  {k:'M4',name:'핫스팟 직상부 공급형',note:'핫스팟 바로 위에서 공급'},
  {k:'M5',name:'파도형 빗살',note:'물결 모양 빗살'},
  {k:'D0',name:'이중 바람개비형',note:'바람개비 2개, 다리로 이은 입구'},
  {k:'D1',name:'말굽형',note:'말굽 2개가 마주 보는 홈'},
  {k:'D2',name:'엇갈린 막대형',note:'막대 2개가 엇갈리고 포트는 대각선'},
  {k:'D4',name:'흡입 바람개비형',note:'바람개비로 빨아내고 양끝에서 공급'},
  {k:'D5',name:'말굽 완충형',note:'말굽형에 물이 섞이는 빈 칸 추가'},
  {k:'D6',name:'가로 빗살형',note:'가로 빗살 맞물림, 입구 5 · 출구 4'}];
function loadDesigns(data){
  const wc=WC*1e-3,H=HC*1e-3,A=wc*H,Dh=2*wc*H/(wc+H),al=wc/H,r=2*poiseuille(al)*1e-3/(Dh*Dh*A);
  for(const d of DESIGNS){
    if(d.k==='M0'){
      const t={F:b64(data.M0.F,Float32Array),Rl:data.M0.Rl};d.T={};TMS.forEach(k=>d.T[k]=t);d.ports=[[3,1],[9,1],[3,11],[9,11]];d.head=1;d.ref=true;continue;
    }
    const v=data[d.k];d.T={};for(const k of TMS){const q=v.t[k==='1.0'?'1.0':k];d.T[k]={F:b64(q.F,Float32Array),S:b64(q.S,Uint16Array),Rl:q.Rl,sp:q.sp};if(q.q)d.T[k].q={F:b64(q.q.F,Float32Array),S:b64(q.q.S,Uint16Array),Rl:q.q.Rl}}
    d.U=b64(v.U,Uint8Array);d.P=b64(v.P,Uint8Array);d.layers=v.layers.map(l=>({h:l.h,M:b64(l.M,Uint8Array),n:l.n,z:l.z}));d.ports=v.ports;d.head=v.head;d.ext=v.ext;d.e0=v.e0;d.en=v.en;d.pz=v.pz;if(v.fg){d.fg=b64(v.fg,Uint8Array);d.nfg=v.nfg}
  }
}
function setup(p){
  // 입력 정규화·방어: 문자열 숫자는 숫자로 바꾸고, 유한하지 않거나 범위 밖인 값은 기본값으로 대체하지 않고 오류로 멈춤
  const num=v=>typeof v==='string'&&v.trim()!==''?Number(v):v;
  if(!Array.isArray(p.hs))throw new RangeError('핫스팟 배열이 잘못되었습니다');
  p={...p,Tin:num(p.Tin),q0:num(p.q0),ks:num(p.ks),hs:p.hs.map(h=>({...h,x:num(h.x),y:num(h.y),lx:num(h.lx),ly:num(h.ly),q:num(h.q)}))};
  if(!Number.isFinite(p.ks)||p.ks<=0||!Number.isFinite(p.Tin)||!Number.isFinite(p.q0)||p.q0<0)throw new RangeError('재질 열전도도(>0, 유한)·입구 온도·바닥 열유속(≥0) 입력이 유효하지 않습니다');
  if(p.Tin<5||p.Tin>90)throw new RangeError('입구 온도는 5~90 °C만 지원합니다 (물 물성 상관식 범위)');
  for(const h of p.hs){
    if(![h.x,h.y,h.lx,h.ly,h.q].every(Number.isFinite)||h.lx<=0||h.ly<=0||h.q<0)throw new RangeError('핫스팟 입력값(위치·크기>0·열유속≥0)이 유효하지 않습니다');
    if(h.x+h.lx/2<=0||h.x-h.lx/2>=Z||h.y+h.ly/2<=0||h.y-h.ly/2>=Z)throw new RangeError('핫스팟이 판(12 × 12 mm) 밖에 있습니다');}   // 일부만 밖이면 판 안쪽만 발열로 잡는다(클리핑)
  const f=water(p.Tin+10),wc=WC*1e-3,H=HC*1e-3,A=wc*H,Dh=2*wc*H/(wc+H),al=wc/H;
  const heat=new Float64Array(NX*N);let Ptot=0;
  // 발열 지도(최대값 규칙, 정확한 면적 적분): 격자 셀을 셀 안을 지나는 모든 핫스팟 경계에서 작은 사각형으로 나누고,
  // 각 사각형은 그것을 덮는 핫스팟 중 가장 큰 열유속(없으면 q0) × 면적. 핫스팟이 겹쳐도 열이 더해지지 않고, 아무리 작은 핫스팟도 면적만큼 정확히 들어간다.
  const cuts=(a,b,edges)=>{const s=[a];for(const e of edges)if(e>a+1e-12&&e<b-1e-12)s.push(e);s.push(b);return s.sort((u,v)=>u-v)};
  const ex=[],ey=[];for(const h of p.hs){ex.push(h.x-h.lx/2,h.x+h.lx/2);ey.push(h.y-h.ly/2,h.y+h.ly/2)}
  for(let j=0;j<N;j++){const[xa,xb]=stripEdges(j),xs=cuts(xa,xb,ex);for(let i=0;i<NX;i++){const ya=i*DY,yb=(i+1)*DY,ys=cuts(ya,yb,ey);let q=0;
    for(let a=0;a<xs.length-1;a++)for(let b=0;b<ys.length-1;b++){const cx=(xs[a]+xs[a+1])/2,cy=(ys[b]+ys[b+1])/2;let f=-1;
      for(const h of p.hs)if(Math.abs(cx-h.x)<h.lx/2&&Math.abs(cy-h.y)<h.ly/2&&h.q>f)f=h.q;
      q+=(f<0?p.q0:f)*(xs[a+1]-xs[a])*(ys[b+1]-ys[b])}
    heat[j*NX+i]=q*1e-2;Ptot+=q*1e-2}}
  const f0=water(p.Tin),TmOf=Qml=>p.Tin+Ptot/(2*f0.rho*(Qml*1e-6/60)*f0.cp),fQ=Qml=>water(TmOf(Qml)),LG=lgCoef(H/wc,nuInf(al));return {p,f,f0,fQ,TmOf,A,Dh,wc,H,Nu:nuInf(al),LG,heat,Ptot,ks:p.ks};
}
function factor(a,n){for(let k=0;k<n;k++){const pv=a[k*5+2];for(let i=k+1;i<=Math.min(k+2,n-1);i++){const m=a[i*5+2+k-i]/pv;a[i*5+2+k-i]=m;for(let j=k+1;j<=Math.min(k+2,n-1);j++)a[i*5+2+j-i]-=m*a[k*5+2+j-k]}}}
function backsolve(a,n,b){for(let i=1;i<n;i++){let s=b[i];for(let k=Math.max(0,i-2);k<i;k++)s-=a[i*5+2+k-i]*b[k];b[i]=s}for(let i=n-1;i>=0;i--){let s=b[i];for(let k=i+1;k<=Math.min(i+2,n-1);k++)s-=a[i*5+2+k-i]*b[k];b[i]=s/a[i*5+2]}}
// 열적 발달 구간 국부 Nu: Lee & Garimella (2006, Int. J. Heat Mass Transfer 49:3060) 직사각 채널·H1·4면 가열 상관식
//   Nu_z = 1/(C1·z*^C2 + C3) + C4,  z* = s/(Re·Pr·Dh),  α = H/w (1 ≤ α ≤ 10; 이 힐트싱크 1.6),  s = 슬롯(입구)에서 재 거리(m)
//   완전발달 Nu_∞(Shah & London)와 만나는 z*_c 부터는 Nu_∞ (논문의 유효범위 z*_th는 zth에 보관; z*_th~z*_c 구간은 연속성을 위해 식을 그대로 연장)
//   이전 Hausen(원관·등온벽용) 평균식 + 평균→국부 미분 변환을 대체: Hausen 평균은 조화평균형이라 산술미분하면 국부 h를 약 10 % 과소평가했음 (검증 계획서 식 24·25)
function lgCoef(al,Nfd){al=Math.max(1,Math.min(10,al));const C1=-3.122e-3*al**3+2.435e-2*al**2+.2143*al+7.325,C2=.6412,C3=1.589e-4*al**2-2.603e-3*al+.02444,C4=7.148-13.28/al+15.15/al**2-5.936/al**3;
  const zth=-1.275e-6*al**6+4.709e-5*al**5-6.902e-4*al**4+5.014e-3*al**3-1.769e-2*al**2+1.845e-2*al+5.691e-2,zc=Nfd>C4?Math.pow(Math.max((1/(Nfd-C4)-C3)/C1,1e-12),1/C2):Infinity;return {C1,C2,C3,C4,zth,zc}}
const nuLoc=(g,z)=>{const c=g.LG;if(!(z<c.zc))return g.Nu;return Math.max(g.Nu,1/(c.C1*Math.pow(z,c.C2)+c.C3)+c.C4)};
// 격자 셀 [s1,s2]의 길이평균 국부 Nu = ∫Nu_z dz/(s2−s1). 치환 z = z1+(z2−z1)u²로 첫 셀(z1=0)의 z^-0.64 특이점을 완화한 4점 가우스 적분
const GX4=[.0694318,.3300095,.6699905,.9305682],GW4=[.1739274,.3260726,.3260726,.1739274];
const nuCell=(g,s1,s2,Re)=>{const Pr=g.f.mu*g.f.cp/g.f.kf,L=g.Dh*Re*Pr;if(!(L>0))return g.Nu;const z1=s1/L,z2=s2/L;if(!(z1<g.LG.zc))return g.Nu;let s=0;for(let k=0;k<4;k++){const u=GX4[k];s+=GW4[k]*nuLoc(g,z1+(z2-z1)*u*u)*2*u}return s};

function evaluate(g,d,Qml,tm){
  Qml=typeof Qml==='string'?Number(Qml):Qml;
  if(!Number.isFinite(Qml)||Qml<=0)throw new RangeError('유량은 0보다 큰 유한한 값이어야 합니다 (단상 모델은 Q=0에서 정의되지 않음)');
  // 단상·물성 범위 검사: 에너지 수지로 추정한 출구 수온(Tin + P/(ṁ·cp))이 95 °C 이하여야 하고, 계산 후 채널 유체 노드 최고 온도도 95 °C 이하여야 한다(아래에서 확인)
  const ToutEst=g.f0?g.p.Tin+g.Ptot/(g.f0.rho*(Qml*1e-6/60)*g.f0.cp):NaN;let rangeOK=!g.f0||(Number.isFinite(ToutEst)&&ToutEst<=95);
  if(g.fQ)g=Object.assign({},g,{f:g.fQ(Qml)}); // 물성은 이 유량에서의 유체 평균 온도(입구 + 상승분/2)에서 평가
  const V=(g.p.inl==='q'&&d.T[tm].q)||d.T[tm],FF=V.F,Rl=V.Rl,n=2*NX,ks=g.ks,scale=Qml/Q0,rc=g.f.rho*g.f.cp,dy=DY*1e-3,tb=TB*1e-3,H=g.H,wc=g.wc,tf=(PITCH-WC)*1e-3,Tin=g.p.Tin;
  const mats=[],meta=[],fg=d.fg,Tf=new Float64Array((d.nfg||0)+1).fill(Tin);let ReMax=0;const hy=1e-3,hHdr=HCAL*4.5*g.f.kf/(2*hy*HC*1e-3/(hy+HC*1e-3));
  for(let j=0;j<N;j++){
    const[xa,xb]=stripEdges(j),wid=(xb-xa)*1e-3,a=new Float64Array(5*n),bIn=new Float64Array(NX),bF=new Float64Array(NX),gF=new Uint8Array(NX),hAr=new Float64Array(NX),fixed=new Int8Array(NX);
    const set=(r,c,v)=>{a[r*5+2+c-r]+=v};
    const tFull=(TB+HC+parseFloat(tm))*1e-3,tCh=tb+H*tf/(PITCH*1e-3)+TL*1e-3,edge=j===0||j===N-1;
    const thick=i=>(i<I0||i>=I0+NC||edge)?tFull:tCh,Kxf=i=>{const ta=thick(i-1),tc=thick(i);return ks*wid/dy*2*ta*tc/(ta+tc)};
    const Kl=new Float64Array(NX),Kr=new Float64Array(NX),gap=q=>((stripEdges(q)[1]-stripEdges(q)[0])+(stripEdges(q+1)[1]-stripEdges(q+1)[0]))/2*1e-3;
    for(let i=0;i<NX;i++){const row=i<I0||i>=I0+NC;if(j>0)Kl[i]=ks*(row?tFull:(j===1||j===N-1?tb+H:tb)+TL*1e-3)*dy/gap(j-1);if(j<N-1)Kr[i]=ks*(row?tFull:(j===0||j===N-2?tb+H:tb)+TL*1e-3)*dy/gap(j)}
    const Fq=new Float64Array(NC+1);for(let c=0;c<=NC;c++)Fq[c]=FF[j*(NC+1)+c]*scale;
    const thr=Math.max(...Fq.map(Math.abs))*.03+1e-13,dist=new Float64Array(NC).fill(9e9);
    if(d.ext){if(Fq[0]>thr)dist[0]=d.e0*1e-3;if(Fq[NC]<-thr)dist[NC-1]=d.e0*1e-3}
    for(let c=0;c<NC;c++){const s=Fq[c+1]-Fq[c];if(s>thr&&!(fg&&fg[j*NC+c]))dist[c]=0;else if(c&&Fq[c]>0)dist[c]=Math.min(dist[c],dist[c-1]+dy)}
    for(let c=NC-1;c>=0;c--){const s=Fq[c+1]-Fq[c];if(s>thr&&!(fg&&fg[j*NC+c]))dist[c]=0;else if(c<NC-1&&Fq[c+1]<0)dist[c]=Math.min(dist[c],dist[c+1]+dy)}
    if(d.ref)for(let c=0;c<NC;c++)dist[c]=c*dy;
    const sink=[],ends={f0:Fq[0],fN:Fq[NC]};
    for(let c=0;c<NC;c++){
      const i=I0+c,rT=2*i,rF=rT+1,fL=Fq[c],fR=Fq[c+1],sv=fR-fL,v=Math.max(Math.abs(fL),Math.abs(fR))/g.A,Re=g.f.rho*v*g.Dh/g.f.mu;
      if(Re>ReMax)ReMax=Re;
      const s1=dist[c],s2=s1+dy,nu=Re<1?g.Nu:nuCell(g,s1,s2,Re);   // 격자 평균 국부 Nu (Lee & Garimella 국부식 적분; dist 미설정 9e9 → 완전발달)
      const h=HCAL*nu*g.f.kf/g.Dh,m=Math.sqrt(2*h/(ks*tf)),eta=Math.tanh(m*H)/(m*H);const hA=h*(wc+2*eta*H+wc/Math.cosh(m*H))*dy; // 바닥 + 핀 2면(효율) + 윗면(핀 끝 온도 = 밑면/cosh(mH))
      set(rT,rT,hA);set(rT,rF,-hA);
      const out=rc*(Math.max(fR,0)+Math.max(-fL,0)+Math.max(-sv,0));
      set(rF,rF,out+hA+1e-12);set(rF,rT,-hA);
      if(fL>0&&c>0)set(rF,rF-2,-rc*fL);
      if(fR<0&&c<NC-1)set(rF,rF+2,rc*fR);
      const gq=fg?fg[j*NC+c]:0;if(gq){bF[i]=rc*Math.max(sv,0);gF[i]=gq}else bIn[i]=rc*Math.max(sv,0)+0;
      if(sv<0)sink.push({i,w:-rc*sv,g:gq});
      if(c===0&&fL>0)ends.c0=i;
      if(c===NC-1&&fR<0)ends.cN=i;
    }
    for(let i=0;i<NX;i++){
      const r=2*i,y=(i+.5)*DY;
      if(i<I0||i>=I0+NC){
        // 헤더가 있으면 헤더 물과, 채널이 끝까지 이어진 구조는 그 구간 채널 물과 열을 주고받는다
        const inH=d.head&&y>.5&&y<11.5,e=i<I0?0:1,ex=d.ext&&y>d.ext[0]&&y<d.ext[1]&&Math.abs(e?ends.fN:ends.f0)>thr;let hA=inH?hHdr*wid*dy:0;
        if(ex){const hx=HCAL*g.Nu*g.f.kf/g.Dh,mx=Math.sqrt(2*hx/(ks*tf));hA=hx*(wc+2*Math.tanh(mx*H)/mx+wc/Math.cosh(mx*H))*dy}
        if(hA){set(r,r,hA);set(r,r+1,-hA);hAr[i]=hA}
        set(r+1,r+1,1);fixed[i]=d.ref&&inH?(e?3:1):inH||(ex&&d.en[e][j]!==1)?2:1;
      }
      let D=Kl[i]+Kr[i];if(i>0){const K=Kxf(i);a[r*5]+=-K;D+=K}if(i<NX-1){const K=Kxf(i+1);a[r*5+4]+=-K;D+=K}
      a[r*5+2]+=D;
    }
    factor(a,n);mats.push(a);meta.push({bIn,bF,gF,hAr,fixed,sink,Kl,Kr,ends,hdrA:hHdr*wid*dy,rc});
  }
  const T=new Float64Array(n*N).fill(Tin),b=new Float64Array(n),Tc=[Tin,Tin];let Th0=Tin,ThN=Tin;
  const Tb=Tin+g.Ptot/(2*g.f.rho*(Qml*1e-6/60)*g.f.cp);let sweeps=0;
  for(sweeps=0;sweeps<1500;sweeps++){
    let e0=0,w0=0,eN=0,wN=0;const ei=[0,0],wi=[0,0],win=[0,0];
    for(let j=0;j<N;j++){const f0=meta[j].ends.f0,fN=meta[j].ends.fN,a=d.en&&d.en[0][j]===1,b=d.en&&d.en[1][j]===1,t0=T[j*n+2*I0+1],tN=T[j*n+2*(I0+NC-1)+1];
      if(f0<0){if(a){ei[0]+=-f0*t0;wi[0]+=-f0}else{e0+=-f0*t0;w0+=-f0}}else if(a)win[0]+=f0;
      if(fN>0){if(b){ei[1]+=fN*tN;wi[1]+=fN}else{eN+=fN*tN;wN+=fN}}else if(b)win[1]+=-fN}
    if(!d.ref){if(w0>0)Th0=e0/w0;if(wN>0)ThN=eN/wN;
      // 머리 쪽 양끝은 끝끼리 섞이므로 평균으로 묶는다
    }
    // 입구 쪽 관통 공간: 새 물과 채널에서 되돌아온 물이 섞인 온도로 들어간다
    for(let e=0;e<2;e++)Tc[e]=win[e]>0?Tin+Math.max(0,ei[e]-wi[e]*Tin)/win[e]:Tin;
    if(fg){const nu=new Float64Array(Tf.length),de=new Float64Array(Tf.length);for(let j=0;j<N;j++)for(const q of meta[j].sink)if(q.g){nu[q.g]+=q.w*T[j*n+2*q.i+1];de[q.g]+=q.w}for(let k=1;k<Tf.length;k++)if(de[k]>0)Tf[k]=nu[k]/de[k]}
    let dmax=0;
    for(let j=0;j<N;j++){
      const M=meta[j],o=j*n;
      for(let i=0;i<NX;i++){
        let s=g.heat[j*NX+i];if(j>0)s+=M.Kl[i]*T[(j-1)*n+2*i];if(j<N-1)s+=M.Kr[i]*T[(j+1)*n+2*i];
        b[2*i]=s;
        if(M.fixed[i])b[2*i+1]=M.fixed[i]===2?Tb:M.fixed[i]===3?2*Tb-Tin:Tin;
        else {let f=M.bIn[i]*Tin+(M.bF[i]?M.bF[i]*Tf[M.gF[i]]:0);if(i===M.ends.c0)f+=rc*M.ends.f0*(d.ref?Tin:d.en&&d.en[0][j]===1?Tc[0]:Th0);if(i===M.ends.cN)f+=rc*(-M.ends.fN)*(d.ref?Tin:d.en&&d.en[1][j]===1?Tc[1]:ThN);b[2*i+1]=f}
      }
      backsolve(mats[j],n,b);
      for(let k=0;k<n;k++){const nv=T[o+k]+1.35*(b[k]-T[o+k]),dd=Math.abs(nv-T[o+k]);if(dd>dmax)dmax=dd;T[o+k]=nv}
    }
    if(dmax<1e-3&&sweeps>3)break;
  }
  let Eout=0,Etot=0;
  for(let j=0;j<N;j++){const M=meta[j];
    for(const s of M.sink)if(!s.g)Eout+=s.w*(T[j*n+2*s.i+1]-Tin);

    if(d.ref&&M.ends.fN>0)Eout+=rc*M.ends.fN*(T[j*n+2*(I0+NC-1)+1]-Tin);
    if(d.ext){const f0=M.ends.f0,fN=M.ends.fN,a=d.en[0][j]===1,b=d.en[1][j]===1;
      Eout+=f0<0?rc*-f0*(T[j*n+2*I0+1]-Tin):-rc*f0*((a?Tc[0]:Th0)-Tin);
      Eout+=fN>0?rc*fN*(T[j*n+2*(I0+NC-1)+1]-Tin):-rc*-fN*((b?Tc[1]:ThN)-Tin)}
    for(let i=0;i<NX;i++)if(M.hAr[i])Eout+=M.hAr[i]*(T[j*n+2*i]-(M.fixed[i]===2?Tb:M.fixed[i]===3?2*Tb-Tin:Tin))}
  let TfMax=-1e9;for(let j=0;j<N;j++)for(let c=0;c<NC;c++){const tf=T[j*n+2*(I0+c)+1];if(tf>TfMax)TfMax=tf}if(!(TfMax<=95))rangeOK=false;   // 채널 유체 최고 온도
  // 채널 구간 벽(채널 바닥·핀 뿌리) 평균 온도와 유체 평균 온도 (띠 폭 가중) → 논문 정의의 h = P/(A_wet·(T̄w − T̄f)) 계산용 (Hu 2026 식 14, Zhang 2026 식 9–10, Drummond 2018 식 4)
  let Tws=0,Tfs=0,nw=0;for(let j=0;j<N;j++){const w=stripEdges(j)[1]-stripEdges(j)[0];for(let c=0;c<NC;c++){Tws+=w*T[j*n+2*(I0+c)];Tfs+=w*T[j*n+2*(I0+c)+1];nw+=w}}const Twall=Tws/nw,Tfavg=Tfs/nw;
  const eAbs=Math.abs(Eout-g.Ptot),resRel=g.Ptot>1e-6?eAbs/g.Ptot:0,energyOK=g.Ptot>1e-6?resRel<.05:eAbs<1e-6;   // 발열 0 W 근방은 상대오차가 정의되지 않으므로 절대오차로 판정
  const field=new Float32Array(NX*N),fluid=new Float32Array(NC*N);let Tmax=-1e9,Tmin=1e9,sum=0,wsum=0,px=0,py=0;
  for(let j=0;j<N;j++){const[xa,xb]=stripEdges(j),wid=(xb-xa),cell=wid*1e-3*dy;for(let i=0;i<NX;i++){
    const t=T[j*n+2*i]+g.heat[j*NX+i]/cell*tb/(2*ks);field[j*NX+i]=t;if(t>Tmax){Tmax=t;px=(xa+xb)/2;py=(i+.5)*DY}if(t<Tmin)Tmin=t;sum+=t*wid;wsum+=wid}}
  // 핫스팟 온도 통계: 핫스팟과 면적이 겹치는 격자(띄 × y칸) 전부를 셌다 (발열 분배와 같은 겹침 기준). 채널 중심이 안 들어가는 작은 핫스팟도 값이 나온다
  const hot=g.p.hs.map(h=>{let mx=-1e9,s=0,c=0;const hx0=h.x-h.lx/2,hx1=h.x+h.lx/2,hy0=h.y-h.ly/2,hy1=h.y+h.ly/2;for(let j=0;j<N;j++){const[xa,xb]=stripEdges(j);if(xb<=hx0||xa>=hx1)continue;for(let i=0;i<NX;i++){const ya=i*DY,yb=(i+1)*DY;if(yb<=hy0||ya>=hy1)continue;const t=field[j*NX+i];if(t>mx)mx=t;s+=t;c++}}return {max:c?mx:NaN,avg:c?s/c:NaN,cells:c}});
  const Qt=Qml*1e-6/60,ap=Math.PI*Math.pow((d.k==='M4'?1:.8)*1e-3,2)/4,muS=g.f.mu/1e-3;
  // 입구 분배비: 같은 압력(p) 방식은 유동장에서 계산된 V.sp, 같은 유량(q) 방식은 1/2씩(정확). 포트 손실 = 유량이 큰 입구 포트(경로 최대) + 출구 포트(1/2 가정), K=1.5 (팀 가정, CFD 역산 대상 F12)
  const spv=(Array.isArray(V.sp)&&V.sp.length===2&&V.sp.every(Number.isFinite))?V.sp:[.5,.5],uPin=Math.max(spv[0],spv[1])*Qt/ap,KP=1.5;
  const dpPort=KP*g.f.rho/2*(uPin*uPin+Math.pow(Qt/(2*ap),2)),dpLin=Rl*muS*Qt;
  const RePort=g.f.rho*uPin*(d.k==='M4'?1:.8)*1e-3/g.f.mu;   // 포트 Re (채널 Re와 별도, 식 08): 1000을 넘으면 매니폴드 관성(Stokes 저항망·선형 스케일링 가정 밖) 경고
  // 채널 입구 발달 구간 추가 압력손실 K∞(α)·ρu²/2 (Shah & London), 평균 채널 유속 기준. Qu & Mudawar(2002) 실측 ΔP 재현에 필요
  const ub=Qt/(N*g.A),alK=g.wc/g.H,Kinf=.6796+1.2197*alK+3.3089*alK**2-9.5921*alK**3+8.9089*alK**4-2.9959*alK**5,dpDev=Kinf*g.f.rho/2*ub*ub;
  const chFlow=[];for(let j=0;j<N;j++){let s=0;for(let c=0;c<NC;c++){const sv=(FF[j*(NC+1)+c+1]-FF[j*(NC+1)+c])*scale;if(sv>0)s+=sv}
    if(d.ref)s=FF[j*(NC+1)]*scale;
    if(d.ext)s+=(Math.max(FF[j*(NC+1)],0)+Math.max(-FF[j*(NC+1)+NC],0))*scale;chFlow.push(s)}
  let vmax=0;for(let k=0;k<FF.length;k++){const v=Math.abs(FF[k])*scale/g.A;if(v>vmax)vmax=v}
  const hotShare=g.p.hs.length?(()=>{let s=0,t=0;for(let j=0;j<N;j++){t+=chFlow[j];if(g.p.hs.some(h=>{const[xa,xb]=stripEdges(j);return xb>h.x-h.lx/2&&xa<h.x+h.lx/2}))s+=chFlow[j]}return t>0?s/t:0})():0;
  return {px,py,d,tm,F:FF,S:V.S,field,Tmax,Tmin,Tavg:sum/wsum,dT:Tmax-Tmin,hot,Qml,dp:dpLin+dpPort+dpDev,dpPort,dpLin,dpDev,pump:(dpLin+dpPort+dpDev)*Qt,ReMax,vmax,chFlow,hotShare,res:resRel,eAbs,energyOK,sweeps,conv:sweeps<1500,rangeOK,TfMax,ToutEst,Twall,Tfavg,RePort,sp:spv};
}

/* ==========================================================================================
 * 블록 2 — 자동 최적 매니폴드: 후보 모양 생성, 연결성 검사, flowSolve(Stokes 저항망), aDesign   (HTML 922행부터)
 * ========================================================================================== */
/* ---------- 자동 최적 매니폴드: 핫스팟 위치에 맞춰 매니폴드를 그리고, 미리 푼 구조와 같은 층류 모델(격자 0.05 mm)로 유량장을 바로 푼다 ---------- */
const AR=.05,AG=240,AT=[.5,.35],APD=.8,AEXT=[.6,11.4],XL=.625,XR=11.375;
const aCl=(v,a,b)=>Math.max(a,Math.min(b,v)),aSnap=v=>Math.round(v/AR)*AR,aFin=x=>aCl(.5*Math.round(x/.5),1,11);
const aC0=v=>Math.max(0,Math.floor(v/AR+1e-6)),aC1=v=>Math.min(AG-1,Math.ceil(v/AR-1e-6)-1);
function aGeo(){return {cav:new Uint8Array(AG*AG),gro:new Uint8Array(AG*AG),pin:[],pout:[],bad:null}}
function aRect(g,L,x0,y0,x1,y1,net){for(let iy=aC0(y0);iy<=aC1(y1);iy++)for(let ix=aC0(x0);ix<=aC1(x1);ix++){const o=iy*AG+ix;if(L[o]&&L[o]!==net)g.bad='입구와 출구 유로가 겹침';L[o]=net}}
function aDisc(g,L,cx,cy,r,net){for(let iy=aC0(cy-r-AR);iy<=aC1(cy+r+AR);iy++)for(let ix=aC0(cx-r-AR);ix<=aC1(cx+r+AR);ix++){const dx=(ix+.5)*AR-cx,dy=(iy+.5)*AR-cy;if(dx*dx+dy*dy<=r*r){const o=iy*AG+ix;if(L[o]&&L[o]!==net)g.bad='입구와 출구 유로가 겹침';L[o]=net}}}
// 영역 안에 다른 망이 있는지
function aOther(L,x0,y0,x1,y1,net){for(let iy=aC0(y0);iy<=aC1(y1);iy++)for(let ix=aC0(x0);ix<=aC1(x1);ix++){const v=L[iy*AG+ix];if(v&&v!==net)return true}return false}
// 슬롯은 채널 단위로 끊는다: 범위 안에 중심이 있는 채널들을 덮는다
function aSlotX(x0,x1){let a=Math.ceil((x0-X0)/PITCH-1e-6),b=Math.floor((x1-X0)/PITCH+1e-6);a=aCl(a,0,N-1);b=aCl(b,0,N-1);if(b<a){a=b=aCl(Math.round(((x0+x1)/2-X0)/PITCH),0,N-1)}return [Math.max(XL,chX(a)-PITCH/2),Math.min(XR,chX(b)+PITCH/2)]}
function aEndBands(g,net){aRect(g,g.cav,XL,.6,XR,1.2,net);aRect(g,g.cav,XL,10.8,XR,11.4,net)}
// 양끝 대역의 포트 자리: 다른 망과 닿지 않는 첫 위치
function aEndPorts(g,net){
  const out=[];
  for(const top of [0,1]){
    const y0=top?9.8:1.2,y1=top?10.8:2.2,py=top?10.45:1.55;let ok=false;
    for(const px of [6,3,9,4.5,7.5,1.75,10.25]){
      if(aOther(g.cav,px-1.3,top?9.5:1.2,px+1.3,top?10.8:2.5,net)||aOther(g.gro,px-1.3,top?9.5:1.2,px+1.3,top?10.8:2.5,net)||aOther(g.gro,px-.75,py-.75,px+.75,py+.75,net))continue;
      aRect(g,g.cav,px-1,y0,px+1,y1,net);aDisc(g,g.gro,px,py,APD/2,net);out.push([px,py]);ok=true;break}
    if(!ok){g.bad='끝 포트를 놓을 자리가 없음';return}
  }
  (net===1?g.pin:g.pout).push(...out);
}
function aGroups(a){
  if(a.length<=2)return a.map((_,i)=>[i]);
  let bi=0,bj=1,bd=-1;for(let i=0;i<a.length;i++)for(let j=i+1;j<a.length;j++){const d=Math.hypot(a[i].x-a[j].x,a[i].y-a[j].y);if(d>bd){bd=d;bi=i;bj=j}}
  const A=[bi],B=[bj];for(let k=0;k<a.length;k++){if(k===bi||k===bj)continue;(Math.hypot(a[k].x-a[bi].x,a[k].y-a[bi].y)<=Math.hypot(a[k].x-a[bj].x,a[k].y-a[bj].y)?A:B).push(k)}
  return [A,B];
}
// 핫스팟 위 포트 2개: 핫스팟이 2개면 하나씩, 그 밖에는 두 묶음으로 나눠 덮개 홈으로 잇는다
function aHotPorts(g,a,net){
  const push=p=>(net===1?g.pin:g.pout).push(p);
  if(a.length===1){const x0=aCl(aSnap(a[0].x-1.2),.8,8.8),y=a[0].y;aRect(g,g.gro,x0,y-.4,x0+2.4,y+.4,net);for(const px of [x0+.5,x0+1.9]){aDisc(g,g.gro,px,y,APD/2,net);push([+px.toFixed(3),y])}return}
  for(const grp of aGroups(a)){
    const m=grp.map(i=>a[i]).sort((p,q)=>p.x-q.x);
    for(let k=1;k<m.length;k++){const p=m[k-1],q=m[k];aRect(g,g.gro,p.x-.4,p.y-.4,q.x+.4,p.y+.4,net);aRect(g,g.gro,q.x-.4,Math.min(p.y,q.y)-.4,q.x+.4,Math.max(p.y,q.y)+.4,net)}
    const b=m.reduce((p,q)=>q.w>p.w?q:p);aDisc(g,g.gro,b.x,b.y,APD/2,net);push([b.x,b.y]);
  }
}
const aHeat=h=>h.q*h.lx*h.ly;
// 직상부 공급형: 핫스팟 가운데 위에 입구 슬롯, 양끝으로 배출
function famDirect(hs,s,m,mg){
  const g=aGeo();aEndBands(g,2);
  const sl=hs.map(h=>{const [xa,xb]=m==='full'?[XL,XR]:aSlotX(h.x-h.lx/2-m,h.x+h.lx/2+m);return {xa,xb,x:h.x,y:aCl(aSnap(h.y),1.9+s/2,10.1-s/2),w:Math.max(aHeat(h),1e-9)}});
  // 같은 채널 위에 슬롯이 위아래로 둘 놓이면 그 사이 물이 멈춘다. mg이면 둘을 가운데 한 줄로 합친다
  if(mg)for(let ch=true;ch;){ch=false;
    scan:for(let i=0;i<sl.length;i++)for(let j=i+1;j<sl.length;j++){const p=sl[i],q=sl[j];
      if(p.xa<q.xb-1e-6&&q.xa<p.xb-1e-6&&Math.abs(p.y-q.y)>s+.2){const w=p.w+q.w;sl[i]={xa:Math.min(p.xa,q.xa),xb:Math.max(p.xb,q.xb),x:(p.x*p.w+q.x*q.w)/w,y:aSnap((p.y*p.w+q.y*q.w)/w),w};sl.splice(j,1);ch=true;break scan}}}
  const a=sl.map(q=>{aRect(g,g.cav,q.xa,q.y-s/2,q.xb,q.y+s/2,1);return {x:q.xb-q.xa>=.8?aCl(aSnap(q.x),q.xa+.4,q.xb-.4):aSnap((q.xa+q.xb)/2),y:q.y,w:q.w}});
  aHotPorts(g,a,1);aEndPorts(g,2);return g;
}
// 바람개비형: 핫스팟 아래쪽에는 왼쪽 절반, 위쪽에는 오른쪽 절반 채널로 입구 슬롯을 두고 덮개 홈으로 잇는다
function famPin(hs,m,mir,s,gap){
  const g=aGeo();aEndBands(g,2);
  const a=hs.map(h=>{const xm=aFin(h.x);let xa,xb;
    if(m==='vor'){ // 이웃 핫스팟과의 중간까지, 없으면 채널 배열 끝까지
      let l=XL,r=XR;for(const o of hs){if(o===h)continue;const c=aFin((o.x+h.x)/2);if(o.x<h.x-.5&&c>l)l=c;if(o.x>h.x+.5&&c<r)r=c}xa=l;xb=r}
    else [xa,xb]=aSlotX(h.x-h.lx/2-m,h.x+h.lx/2+m);
    const ya=aCl(aSnap(h.y-h.ly/2-gap-s),1.9,10.1-s),yb=aCl(aSnap(h.y+h.ly/2+gap),1.9,10.1-s);
    const A=mir?[xm,xb]:[xa,xm],B=mir?[xa,xm]:[xm,xb];
    if(A[1]-A[0]<.45||B[1]-B[0]<.45||yb-ya<s+.2){g.bad='핫스팟이 너무 작거나 가장자리에 가까움';return {x:xm,y:aSnap(h.y),w:0}}
    aRect(g,g.cav,A[0],ya,A[1],ya+s,1);aRect(g,g.cav,B[0],yb,B[1],yb+s,1);aRect(g,g.gro,xm-.4,ya,xm+.4,yb+s,1);
    return {x:xm,y:aCl(aSnap(h.y),ya+.4,yb+s-.4),w:aHeat(h)}});
  if(g.bad)return g;
  aHotPorts(g,a,1);aEndPorts(g,2);return g;
}
// V자 빗살형: 입구 빗살과 출구 빗살을 번갈아 놓고, 가운데 입구 빗살이 핫스팟 중심들을 지나도록 꺾는다. 양옆 덮개 홈이 빗살을 잇는다
function famV(hs,w,p){
  const g=aGeo();
  // 꺾이는 점: 핫스팟 중심(왼쪽부터). 기울기가 1을 넘으면 발열이 작은 쪽을 뺀다
  let pts=hs.map(h=>({x:aCl(h.x,2,10),y:aCl(aSnap(h.y),1.9,10.1),w:aHeat(h)})).sort((a,b)=>a.x-b.x);
  for(let ch=true;ch;){ch=false;for(let i=1;i<pts.length;i++)if(Math.abs(pts[i].y-pts[i-1].y)>Math.abs(pts[i].x-pts[i-1].x)+1e-9){pts.splice(pts[i].w<pts[i-1].w?i:i-1,1);ch=true;break}}
  const yc=x=>{if(x<=pts[0].x)return pts[0].y;for(let i=1;i<pts.length;i++)if(x<=pts[i].x){const a=pts[i-1],b=pts[i];return a.y+(b.y-a.y)*(x-a.x)/(b.x-a.x)}return pts[pts.length-1].y};
  // 양끝에는 출구 대역을 둬서 빗살 바깥쪽 채널에도 물이 흐르게 한다. 빗살 위 덮개에도 같은 모양의 홈을 파서 빗살을 따라가는 저항을 줄인다
  const ins=[],ymin=1.7+w/2,ymax=10.3-w/2;let nout=0;
  for(const L of [g.cav,g.gro]){aRect(g,L,1.5,.6,XR,1.2,2);aRect(g,L,1.5,10.8,XR,11.4,2)}
  for(let k=-12;k<=12;k++){const off=k*p,net=k%2===0?1:2,x0=net===1?XL:1.5,x1=net===1?10.5:XR,ye=(net===1?pts[0].y:pts[pts.length-1].y)+off;
    if(ye<ymin-1e-9||ye>ymax+1e-9)continue;   // 덮개 홈(줄기)에 닿는 쪽 끝이 범위 안에 있어야 한다
    for(let ix=aC0(x0);ix<=aC1(x1);ix++){const y=aSnap(yc((ix+.5)*AR)+off);if(y<ymin-1e-9||y>ymax+1e-9)continue;aRect(g,g.cav,ix*AR,y-w/2,(ix+1)*AR,y+w/2,net);aRect(g,g.gro,ix*AR,y-w/2,(ix+1)*AR,y+w/2,net)}
    if(net===1)ins.push(ye);else nout++}
  if(!ins.length){g.bad='입구 빗살을 놓을 자리가 없음';return g}
  let a=Math.min(...ins)-.3,b=Math.max(...ins)+.3;if(b-a<3){const c=(a+b)/2;a=c-1.5;b=c+1.5}if(a<1.6){b+=1.6-a;a=1.6}if(b>10.4){a-=b-10.4;b=10.4}
  for(const [net,y0,y1,gx] of [[1,a,b,[.65,1.25]],[2,.6,11.4,[10.75,11.35]]]){
    aRect(g,g.gro,gx[0],y0,gx[1],y1,net);const xc=(gx[0]+gx[1])/2;
    for(const f of [.25,.75]){const y=aSnap(y0+(y1-y0)*f);aDisc(g,g.gro,xc,y,APD/2,net);(net===1?g.pin:g.pout).push([xc,y])}}
  return g;
}
// 대역 대향류형: 채널을 대역으로 나눠 이웃 대역끼리 반대로 흐르게 한다. 대역 경계는 발열이 큰 핫스팟의 중심
function famBand(hs,flip){
  const g=aGeo();
  let xs=[...new Set(hs.slice().sort((p,q)=>aHeat(q)-aHeat(p)).map(h=>aCl(aFin(h.x),2,10)))].slice(0,2).sort((p,q)=>p-q);
  if(xs.length===2&&xs[1]-xs[0]<1.5)xs=[aCl(aFin((xs[0]+xs[1])/2),2,10)];
  const nb=xs.length+1,band=i=>[i===0?XL:xs[i-1]+.125,i===nb-1?XR:xs[i]-.125];
  for(const top of [0,1]){
    const y0=top?10.8:.6,y1=top?11.4:1.2,by=[[],[]];
    for(let i=0;i<nb;i++){const net=(i%2===0)!==!!top?1:2,[x0,x1]=band(i);aRect(g,g.cav,x0,y0,x1,y1,net);by[net-1].push([x0,x1])}
    for(const net of [1,2]){
      const c=by[net-1],put=p=>(net===1?g.pin:g.pout).push(p);
      if(c.length===1){const xc=aSnap((c[0][0]+c[0][1])/2),hw=Math.min(1,(c[0][1]-c[0][0])/2);aRect(g,g.cav,xc-hw,top?9.5:1.2,xc+hw,top?10.8:2.5,net);aDisc(g,g.gro,xc,top?10.45:1.55,APD/2,net);put([xc,top?10.45:1.55])}
      else{const leg=c.map(b=>{const xc=aSnap((b[0]+b[1])/2),hw=Math.min(.5,(b[1]-b[0])/2);return [xc-hw,xc+hw]}),ya=top?7.7:3.3,yb=top?8.7:4.3;
        for(const l of leg)aRect(g,g.gro,l[0],top?yb:.7,l[1],top?11.3:ya,net);
        aRect(g,g.gro,leg[0][0],ya,leg[1][1],yb,net);const xc=aSnap((leg[0][0]+leg[1][1])/2);aDisc(g,g.gro,xc,(ya+yb)/2,APD/2,net);put([xc,(ya+yb)/2])}
    }
  }
  return flip?aSwap(g):g;
}
function aSwap(g){for(const L of [g.cav,g.gro])for(let i=0;i<L.length;i++)if(L[i]===1)L[i]=2;else if(L[i]===2)L[i]=1;[g.pin,g.pout]=[g.pout,g.pin];return g}
function autoSpecs(hs){
  const L=[],mm=m=>m==='full'?'전폭 슬롯':`좌우 여유 ${m} mm`;
  for(const g of [0,1])for(const m of [0,.5,1.5,'full'])for(const s of [.4,.8])L.push({fam:'직상부 공급형',name:`직상부 공급형 · 슬롯 ${s} mm · ${mm(m)}${g?' · 가운데 한 줄':''}`,make:()=>famDirect(hs,s,m,g)});
  for(const g of [0,1])for(const m of [0,.5,1.5])L.push({fam:'흡입형',name:`흡입형 (양끝 공급, 핫스팟 위 배출) · ${mm(m)}${g?' · 가운데 한 줄':''}`,make:()=>aSwap(famDirect(hs,.8,m,g))});
  for(const w of [.4,.8])for(const p of [1.2,1.6,2.4])L.push({fam:'V자 빗살형',name:`V자 빗살형 · 빗살 폭 ${w} mm · 간격 ${p} mm`,make:()=>famV(hs,w,p)});
  for(const f of [0,1])L.push({fam:'대역 대향류형',name:`대역 대향류형${f?' · 방향 반대':''}`,make:()=>famBand(hs,f)});
  const pn=(m,s,gp,r)=>L.push({fam:'바람개비형',name:`바람개비형 · 슬롯 ${s} mm · ${m==='vor'?'이웃 핫스팟 중간까지':mm(m)} · ${gp<0?'슬롯이 핫스팟 모서리 안쪽':'슬롯이 핫스팟 바깥'}${r?' · 좌우 반전':''}`,make:()=>famPin(hs,m,r,s,gp)});
  for(const m of [1,1.5,'vor'])for(const s of [.4,.8])for(const r of [0,1])pn(m,s,-.4,r);
  for(const r of [0,1])pn(1.5,.4,.2,r);
  return L;
}
function aSig(g){let h=2166136261;for(const L of [g.cav,g.gro])for(let i=0;i<L.length;i++){h^=L[i]+1;h=Math.imul(h,16777619)}return h+'|'+g.pin.concat(g.pout).join(',')}
// 만들 수 있는 모양인지: 합선, 벽 두께, 포트 연결
function aCheck(g){
  if(g.bad)return g.bad;
  if(g.pin.length!==2||g.pout.length!==2)return '포트 4개를 놓지 못함';
  const n=AG,nn=n*n,L=[g.cav,g.gro],P=[...g.pin,...g.pout];
  for(let i=0;i<4;i++)for(let j=i+1;j<4;j++)if(Math.hypot(P[i][0]-P[j][0],P[i][1]-P[j][1])<1.2)return '포트끼리 너무 가까움';
  for(let i=0;i<nn;i++)if(g.cav[i]&&g.gro[i]&&g.cav[i]!==g.gro[i])return '덮개 홈이 다른 쪽 유로 위를 지나감';
  for(const M of L)for(let iy=0;iy<n;iy++)for(let ix=0;ix<n;ix++){const v=M[iy*n+ix];if(v!==1)continue;
    for(let dy=-3;dy<=3;dy++)for(let dx=-3;dx<=3;dx++){const y=iy+dy,x=ix+dx;if(y<0||x<0||y>=n||x>=n)continue;if(M[y*n+x]===2)return '입구와 출구 사이 벽이 0.2 mm보다 얇음'}}
  // 포트에서 출발해 같은 망을 따라 모두 닿는지
  const seen=[new Uint8Array(nn),new Uint8Array(nn)],st=[];
  P.forEach((p,k)=>{const net=k<2?1:2;for(let iy=aC0(p[1]-.45);iy<=aC1(p[1]+.45);iy++)for(let ix=aC0(p[0]-.45);ix<=aC1(p[0]+.45);ix++){const dx=(ix+.5)*AR-p[0],dy=(iy+.5)*AR-p[1],o=iy*n+ix;if(dx*dx+dy*dy<=APD*APD/4&&g.gro[o]===net&&!seen[1][o]){seen[1][o]=1;st.push(nn+o)}}});
  while(st.length){const q=st.pop(),l=q>=nn?1:0,o=q-l*nn,net=L[l][o],ix=o%n;
    const go=(ll,oo)=>{if(L[ll][oo]===net&&!seen[ll][oo]){seen[ll][oo]=1;st.push(ll*nn+oo)}};
    if(ix>0)go(l,o-1);if(ix<n-1)go(l,o+1);if(o>=n)go(l,o-n);if(o<nn-n)go(l,o+n);go(1-l,o)}
  for(let l=0;l<2;l++)for(let i=0;i<nn;i++)if(L[l][i]&&!seen[l][i])return '포트에 이어지지 않는 유로가 있음';
  return null;
}
// 벽까지 거리의 2배 = 국부 폭 (m). 정확한 유클리드 거리 변환
function aWidth(mask){
  const n=AG,INF=1e12,d=new Float64Array(n*n),f=new Float64Array(n),o=new Float64Array(n),v=new Int32Array(n),z=new Float64Array(n+1);
  const pass=()=>{let k=0;v[0]=0;z[0]=-INF;z[1]=INF;
    for(let q=1;q<n;q++){let s;for(;;){const p=v[k];s=((f[q]+q*q)-(f[p]+p*p))/(2*q-2*p);if(s<=z[k]&&k>0)k--;else break}k++;v[k]=q;z[k]=s;z[k+1]=INF}
    k=0;for(let q=0;q<n;q++){while(z[k+1]<q)k++;const p=v[k];o[q]=(q-p)*(q-p)+f[p]}};
  for(let x=0;x<n;x++){for(let y=0;y<n;y++)f[y]=mask[y*n+x]?INF:0;pass();for(let y=0;y<n;y++)d[y*n+x]=o[y]}
  for(let y=0;y<n;y++){for(let x=0;x<n;x++)f[x]=d[y*n+x];pass();for(let x=0;x<n;x++)d[y*n+x]=o[x]}
  for(let i=0;i<n*n;i++)d[i]=mask[i]?2*Math.sqrt(Math.min(d[i],1e9))*AR*1e-3:0;
  return d;
}
// 직사각 덕트(짧은 변 a, 긴 변 b)의 유량 보정계수: Q = (a³b/12μ)·corr·(−dp/dx), corr = 1 − (192/π⁵)(a/b)Σ_{n 홀수} tanh(nπb/2a)/n⁵ (Shah & London 정확해).
// 이전의 1차 근사 1−0.63a/b는 a/b=1(정사각)에서 저항을 12 % 과대평가(0.370 vs 0.422), a/b=0.8에서 3.7 % — 슬롯 폭 0.4~0.8 mm vs 두께 0.5/0.35 mm는 이 범위 (검증 계획서 식 17)
// 미리 풀어 둔 10개 구조의 유량장은 근사식 기준이나 전체 저항 차이는 0.4~2.7 %, 채널 분배비 차이 ≤0.2 %p (후보 44개 검사)
const rectCorr=r=>{r=Math.min(1,Math.max(r,1e-9));let s=0;for(let n=1;n<=9;n+=2)s+=Math.tanh(n*Math.PI/(2*r))/(n*n*n*n*n);return 1-192/Math.pow(Math.PI,5)*r*s};
function flowSolve(g,mode){
  const n=AG,nn=n*n,L=[g.cav,g.gro],ts=[AT[0]*1e-3,AT[1]*1e-3],mu=1e-3,Hc=HC*1e-3,wc=WC*1e-3,A=wc*Hc,Dh=2*wc*Hc/(wc+Hc),r=2*poiseuille(wc/Hc)*mu/(Dh*Dh*A),dyc=1e-4,area=AR*AR*1e-6;
  const idx=[new Int32Array(nn).fill(-1),new Int32Array(nn).fill(-1)];let N0=0;
  for(let l=0;l<2;l++)for(let i=0;i<nn;i++)if(L[l][i])idx[l][i]=N0++;
  const ca=Math.round((AEXT[0]-1.5)/.1),cb=Math.round((AEXT[1]-1.5)/.1),nc=cb-ca,chId=(j,c)=>N0+j*nc+(c-ca),IN=N0+N*nc,OUT=IN+1,IN2=OUT+1,M=IN2+1;
  const ea=[],eb=[],eg=[],link=(a,b,v)=>{ea.push(a);eb.push(b);eg.push(v)};
  const W=[aWidth(L[0]),aWidth(L[1])],Q=[];
  for(let l=0;l<2;l++){const t=ts[l],q=new Float64Array(nn),w=W[l],m=L[l];
    for(let i=0;i<nn;i++)if(m[i]){const a=Math.min(t,w[i]),b=Math.max(t,w[i]);q[i]=a*a*t/(12*mu)*rectCorr(a/Math.max(b,1e-12))}
    Q.push(q);
    for(let iy=0;iy<n;iy++)for(let ix=0;ix<n;ix++){const o=iy*n+ix,v=m[o];if(!v)continue;
      if(ix<n-1&&m[o+1]===v)link(idx[l][o],idx[l][o+1],2*q[o]*q[o+1]/(q[o]+q[o+1]+1e-30));
      if(iy<n-1&&m[o+n]===v)link(idx[l][o],idx[l][o+n],2*q[o]*q[o+n]/(q[o]+q[o+n]+1e-30))}}
  {const h=(ts[0]+ts[1])/2;for(let i=0;i<nn;i++)if(L[0][i]&&L[1][i]===L[0][i]){const ww=Math.min(W[0][i],W[1][i]);link(idx[0][i],idx[1][i],area*ww*ww/(12*mu*h))}}
  for(let j=0;j<N;j++)for(let c=ca;c<cb-1;c++)link(chId(j,c),chId(j,c+1),1/(r*dyc));
  {const h=(ts[0]+Hc)/2;for(let j=0;j<N;j++){const xc=.75+.5*j;for(let ix=0;ix<n;ix++){if(!(Math.abs((ix+.5)*AR-xc)<=.125))continue;
    for(let iy=0;iy<n;iy++){const o=iy*n+ix;if(!L[0][o])continue;const c=Math.floor(((iy+.5)*AR-1.5)/.1);if(c<ca||c>=cb)continue;const w=Math.min(W[0][o],wc);link(idx[0][o],chId(j,c),area*w*w/(12*mu*h))}}}}
  const G0=1e-6,PE=[[],[]],port=(p,node,net,k)=>{let cnt=0;for(const l of [1,0]){for(let iy=aC0(p[1]-.45);iy<=aC1(p[1]+.45);iy++)for(let ix=aC0(p[0]-.45);ix<=aC1(p[0]+.45);ix++){const dx=(ix+.5)*AR-p[0],dy=(iy+.5)*AR-p[1],o=iy*n+ix;if(dx*dx+dy*dy<=APD*APD/4&&L[l][o]===net){if(k!=null)PE[k].push(ea.length);link(idx[l][o],node,G0);cnt++}}if(cnt)break}return cnt};   // PE[k]: 입구 포트 k에 달린 링크 번호(입구 분배비 계산용)
  if(!port(g.pin[0],IN,1,0)||!port(g.pin[1],mode==='q'?IN2:IN,1,1)||!port(g.pout[0],OUT,2)||!port(g.pout[1],OUT,2))return null;
  // 대칭 양의 정부호 행렬(하삼각 CSR) 조립
  const E=ea.length,dg=new Float64Array(M).fill(1e-22),cnt=new Int32Array(M+1);dg[OUT]+=1;if(mode!=='q')dg[IN2]+=1;
  for(let e=0;e<E;e++){dg[ea[e]]+=eg[e];dg[eb[e]]+=eg[e];cnt[Math.max(ea[e],eb[e])+1]++}
  for(let i=0;i<M;i++)cnt[i+1]+=cnt[i];
  const rp=cnt,ci=new Int32Array(E),va=new Float64Array(E),pos=rp.slice(0,M);
  for(let e=0;e<E;e++){const i=Math.max(ea[e],eb[e]),k=pos[i]++;ci[k]=Math.min(ea[e],eb[e]);va[k]=-eg[e]}
  for(let i=0;i<M;i++){for(let k=rp[i]+1;k<rp[i+1];k++){const c=ci[k],x=va[k];let m=k-1;while(m>=rp[i]&&ci[m]>c){ci[m+1]=ci[m];va[m+1]=va[m];m--}ci[m+1]=c;va[m+1]=x}}
  // 불완전 촐레스키 분해 IC(0)
  const lv=new Float64Array(E),ld=new Float64Array(M);
  for(let i=0;i<M;i++){let d=dg[i];
    for(let k=rp[i];k<rp[i+1];k++){const j=ci[k];let s=va[k],p=rp[i],q=rp[j];const qe=rp[j+1];
      while(p<k&&q<qe){const cp=ci[p],cq=ci[q];if(cp===cq){s-=lv[p]*lv[q];p++;q++}else if(cp<cq)p++;else q++}
      lv[k]=s/ld[j];d-=lv[k]*lv[k]}
    ld[i]=Math.sqrt(d>dg[i]*1e-8?d:dg[i]*1e-8)}
  const mul=(x,y)=>{for(let i=0;i<M;i++)y[i]=dg[i]*x[i];for(let i=0;i<M;i++){const xi=x[i];let s=0;for(let k=rp[i];k<rp[i+1];k++){const j=ci[k];s+=va[k]*x[j];y[j]+=va[k]*xi}y[i]+=s}};
  const prec=(x,y)=>{for(let i=0;i<M;i++){let s=x[i];for(let k=rp[i];k<rp[i+1];k++)s-=lv[k]*y[ci[k]];y[i]=s/ld[i]}for(let i=M-1;i>=0;i--){const t=y[i]/ld[i];y[i]=t;for(let k=rp[i];k<rp[i+1];k++)y[ci[k]]-=lv[k]*t}};
  const b=new Float64Array(M),p=new Float64Array(M),rr=new Float64Array(M),zz=new Float64Array(M),dd=new Float64Array(M),Ad=new Float64Array(M);
  if(mode==='q'){b[IN]=b[IN2]=.5e-6}else b[IN]=1e-6;
  rr.set(b);prec(rr,zz);dd.set(zz);let rz=0,bn=0;for(let i=0;i<M;i++){rz+=rr[i]*zz[i];bn+=b[i]*b[i]}
  let it=0;for(;it<4000;it++){mul(dd,Ad);let dA=0;for(let i=0;i<M;i++)dA+=dd[i]*Ad[i];const al=rz/dA;let rn=0;
    for(let i=0;i<M;i++){p[i]+=al*dd[i];rr[i]-=al*Ad[i];rn+=rr[i]*rr[i]}
    if(rn<=1e-22*bn)break;prec(rr,zz);let rz2=0;for(let i=0;i<M;i++)rz2+=rr[i]*zz[i];const be=rz2/rz;rz=rz2;for(let i=0;i<M;i++)dd[i]=zz[i]+be*dd[i]}
  // 수렴 확인: 반복 횟수뿐 아니라 실제 방정식 잔차 ||A·p − b|| / ||b|| 를 독립적으로 재계산
  mul(p,Ad);let rs=0;for(let i=0;i<M;i++){const e2=Ad[i]-b[i];rs+=e2*e2}const resid=Math.sqrt(rs/Math.max(bn,1e-300));
  const F=new Float32Array(N*(NC+1));
  for(let j=0;j<N;j++)for(let c=0;c<=NC;c++)F[j*(NC+1)+c]=(p[chId(j,c-1)]-p[chId(j,c)])/(r*dyc);
  // 매니폴드 유속 (m/s): 층별 최대 → 0.1 mm 칸 최대 → 상위 0.5% 자름
  const sp=new Float64Array(nn);
  for(let l=0;l<2;l++){const m=L[l],q=Q[l],t=ts[l],id=idx[l],h=AR*1e-3;
    for(let iy=1;iy<n-1;iy++)for(let ix=1;ix<n-1;ix++){const o=iy*n+ix;if(!m[o]||!m[o-1]||!m[o+1]||!m[o-n]||!m[o+n])continue;
      const gx=(p[id[o+1]]-p[id[o-1]])/(2*h),gy=(p[id[o+n]]-p[id[o-n]])/(2*h),s=q[o]/t*Math.hypot(gx,gy);if(s>sp[o])sp[o]=s}}
  const sm=new Float64Array(120*120),pv=[];
  for(let iy=0;iy<120;iy++)for(let ix=0;ix<120;ix++){const o=2*iy*n+2*ix,v=Math.max(sp[o],sp[o+1],sp[o+n],sp[o+n+1]);sm[iy*120+ix]=v;if(v>0)pv.push(v)}
  let cap=Infinity;if(pv.length){pv.sort((a,b)=>a-b);const x=(pv.length-1)*.995,i0=Math.floor(x);cap=pv[i0]+(pv[Math.min(pv.length-1,i0+1)]-pv[i0])*(x-i0)}
  const S=new Uint16Array(120*120);for(let i=0;i<S.length;i++)S[i]=Math.min(65535,Math.floor(Math.min(sm[i],cap)*1000));
  // 입구 포트별 유량 분배비 sp (같은 압력 p 방식에서는 유동장이 정해 줌; 같은 유량 q 방식은 1/2씩) → 포트 손실은 유량이 큰 입구 기준 (검증 계획서 식 14)
  const Qp=[0,1].map(k=>{let s=0;for(const e of PE[k])s+=eg[e]*(p[eb[e]]-p[ea[e]]);return s}),Qs=Qp[0]+Qp[1],spl=mode==='q'?[.5,.5]:(Qs>0?[Qp[0]/Qs,Qp[1]/Qs]:[.5,.5]);
  return {F,S,Rl:(mode==='q'?Math.max(p[IN],p[IN2]):p[IN])/1e-6-p[OUT]/1e-6,sp:spl,it,nodes:M,resid,conv:it<4000&&resid<1e-6};
}
// 풀이 결과를 계산 엔진이 쓰는 구조 형식으로 바꾼다
function aDesign(g,sol){
  const pool=(L,bin)=>{const o=new Uint8Array(120*120);for(let iy=0;iy<120;iy++)for(let ix=0;ix<120;ix++){const k=2*iy*AG+2*ix,v=Math.max(L[k],L[k+1],L[k+AG],L[k+AG+1]);o[iy*120+ix]=bin?(v?1:0):v}return o};
  const en=[[],[]];
  for(let j=0;j<N;j++){const xc=.75+.5*j;for(let e=0;e<2;e++){const c=[0,0,0,0];
    for(let iy=0;iy<AG;iy++){const y=(iy+.5)*AR;if(!(e?y>10.5&&y<11.4:y>.6&&y<1.5))continue;for(let ix=0;ix<AG;ix++)if(Math.abs((ix+.5)*AR-xc)<=.125)c[g.cav[iy*AG+ix]]++}
    en[e].push(c[1]||c[2]?(c[1]>=c[2]?1:2):0)}}
  return {T:{'0.5':{F:sol.F,S:sol.S,Rl:sol.Rl,sp:sol.sp}},U:pool(g.gro),P:pool(g.cav),ports:[...g.pin,...g.pout],head:0,ext:AEXT,e0:.3,en,pz:[1,1.5],
    layers:[{h:.5,M:pool(g.cav,1),n:'관통 매니폴드층',z:[.5,1]},{h:.35,M:pool(g.gro,1),n:'덮개 홈층',z:[1,1.35]}]};
}

/* ==========================================================================================
 * 블록 3 — 실행·화면: compute, 자동 설계 실행, 순위·지표, 유량 스윕, 그리기   (HTML 1145행부터)
 * ========================================================================================== */
const $=id=>document.getElementById(id);
const HS0=[{x:3,y:6,lx:2,ly:2,q:300},{x:9,y:6,lx:2,ly:2,q:300}];
const DEF={Q:68,t:'0.5',inl:'q',Tin:20,q0:50,ks:235,wprop:'T',Tlim:null,dpMax:50,mode:'bal',hs:HS0.map(h=>({...h}))};
let S=(()=>{try{const t=localStorage.getItem('hs-agent-v14');if(t){const o=JSON.parse(t);if(o&&Array.isArray(o.hs))return {...DEF,...o}}}catch(e){}return JSON.parse(JSON.stringify(DEF))})();
const QS=[68,102,136,169,203],QNOM=300/67.74;
S.inl='q';if(S.dpMax==null)S.dpMax=50;if(S.Q>900)S.Q=900;if(S.wprop!=='fixed')S.wprop='T';
const save=()=>{try{localStorage.setItem('hs-agent-v14',JSON.stringify(S))}catch(e){}};
let allPool=[],fromInlet=false,G=null,res=[],sweep=[],sel=3,view='temp',selHs=0,token=0,timer=null,downloads=null,justDragged=false,drag=null,opt=null,imgs={};
let qcap=900;const QMAX=900;const FAILS=[];let SWQ=[];   // SWQ: 유량 스윙에 쓴 유량 목록   // 계산 중 예외가 난 조건 목록(화면 경고에 표시)
const AUTOD={k:'A',name:'자동 최적 매니폴드',note:''},AUTO={key:null,cands:[],pick:null,best:null,first:true};
loadDesigns(JSON.parse($('hsdata').textContent));
window.claude?.use?.('downloads').then(d=>{downloads=d;if(!d)$('xCsv').hidden=true}).catch(()=>{});
const BANDS=20,CMAP=[[0,[0,0,255]],[.25,[0,255,255]],[.5,[0,255,0]],[.75,[255,255,0]],[1,[255,0,0]]];
function cmapRaw(t){for(let k=1;k<CMAP.length;k++)if(t<=CMAP[k][0]){const[a,c]=CMAP[k-1],[b,e]=CMAP[k],u=(t-a)/(b-a);return c.map((v,i)=>Math.round(v+(e[i]-v)*u))}return CMAP[CMAP.length-1][1]}
function cmap(t){t=Math.max(0,Math.min(1,t));return cmapRaw(Math.min(BANDS-1,Math.floor(t*BANDS))/(BANDS-1))}
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const SER={M0:'var(--muted)',M1:'var(--s1)',M2:'var(--s2)',M3:'var(--s3)',M4:'var(--s4)',M5:'var(--s5)',D0:'var(--s6)',D1:'var(--s7)',D2:'var(--s8)',D4:'var(--s9)',D5:'var(--s10)',D6:'var(--s2)',A:'var(--ink)'};
const isD=d=>d.k[0]==='D',DASH='stroke-dasharray="12 3 3 3"',chY=d=>d.ext||[Y0,Y1];
function range(){
  if(view==='temp'){const hi=Math.max(...res.map(r=>r.Tmax)),lo=fromInlet?S.Tin:Math.min(...res.map(r=>r.Tmin));return [lo,Math.max(hi,lo+1),'Temperature °C']}
  if(view==='vch')return [0,Math.max(...res.map(r=>r.vmax),.01),'Channel velocity m/s'];
  if(view==='vman'){let m=.01;const s=S.Q/Q0/1000;for(const r of res)if(!r.d.ref)for(let i=0;i<r.S.length;i++)if(r.S[i]*s>m)m=r.S[i]*s;return [0,m,'Manifold velocity m/s']}
  return [0,1,''];
}
function image(r,lo,hi){
  const d=r.d,P=view==='vch'?480:view==='temp'?NX:120,c=document.createElement('canvas');c.width=P;c.height=P;
  const x=c.getContext('2d'),im=x.createImageData(P,P),px=(o,col,a=255)=>{im.data[o]=col[0];im.data[o+1]=col[1];im.data[o+2]=col[2];im.data[o+3]=a};
  const span=hi-lo;
  if(view==='temp')for(let py=0;py<P;py++)for(let ix=0;ix<P;ix++){const j=stripAt((ix+.5)*DY),i=P-1-py;px((py*P+ix)*4,cmap((r.field[j*NX+i]-lo)/span))}
  else if(view==='vch'){const sc=S.Q/Q0,step=Z/P,fin=[150,162,166];
    for(let py=0;py<P;py++)for(let ix=0;ix<P;ix++){const X=(ix+.5)*step,Yv=Z-(py+.5)*step,j=Math.round((X-X0)/PITCH),o=(py*P+ix)*4;
      if(j<0||j>=N||Math.abs(X-chX(j))>WC/2||Yv<chY(d)[0]||Yv>chY(d)[1]){px(o,fin,70);continue}
      const c0=Math.max(0,Math.min(NC,Math.round((Yv-Y0)/DY)));px(o,cmap(Math.abs(r.F[j*(NC+1)+c0])*sc/G.A/span))}}
  else if(view==='vman'){const s=S.Q/Q0/1000;
    if(!d.ref)for(let py=0;py<P;py++)for(let ix=0;ix<P;ix++){const iy=P-1-py,o=(py*P+ix)*4,v=r.S[iy*P+ix];if(d.U[iy*P+ix]||d.P[iy*P+ix])px(o,cmap(v*s/span));else px(o,[150,162,166],70)}}
  else if(d.U){const col={1:[11,75,214],2:[194,54,28],3:[226,150,0]};
    for(let py=0;py<P;py++)for(let ix=0;ix<P;ix++){const iy=P-1-py,o=(py*P+ix)*4,u=d.U[iy*P+ix],p=d.P[iy*P+ix];
      if(p)px(o,col[p]);else if(u)px(o,col[u],110);else px(o,[150,162,166],40)}}
  x.putImageData(im,0,0);return c.toDataURL();
}
const Yf=y=>Z-y;
function picture(r,lo,hi,big){
  const u=Z/(big?540:200),d=r.d,fs=u*12;
  let h=`<rect width="${Z}" height="${Z}" fill="var(--solid)"/>`;
  const key=d.k+view;if(!imgs[key])imgs[key]=image(r,lo,hi);
  if(view==='geo')for(let j=0;j<N;j++)h+=`<rect x="${chX(j)-WC/2}" y="${Yf(chY(d)[1])}" width="${WC}" height="${chY(d)[1]-chY(d)[0]}" fill="var(--fluid)"/>`;
  const inMap=view==='vman'||view==='geo';
  h+=inMap?(d.ref?'':`<clipPath id="cb"><rect width="${Z}" height="${Z}"/></clipPath><image clip-path="url(#cb)" href="${imgs[key]}" x="${MAP.x}" y="${Z-MAP.y-MAP.h}" width="${MAP.w}" height="${MAP.h}" preserveAspectRatio="none"/>`):`<image href="${imgs[key]}" width="${Z}" height="${Z}" preserveAspectRatio="none"/>`;
  h+=`<rect width="${Z}" height="${Z}" fill="none" stroke="var(--ink)" stroke-width="${u*1.2}"/>`;
  h+=`<rect x="${CHIP.x0}" y="${Yf(CHIP.y1)}" width="${CHIP.x1-CHIP.x0}" height="${CHIP.y1-CHIP.y0}" fill="none" stroke="var(--ink)" stroke-width="${u*1.3}" stroke-dasharray="${u*6} ${u*3}" pointer-events="none"/>`;
  d.ports.forEach((c,i)=>{const isIn=i<2,cl=isIn?'#0B4BD6':'#C2361C';h+=`<circle cx="${c[0]}" cy="${Yf(c[1])}" r="${d.k==='M4'?.5:.4}" fill="${cl}" stroke="#fff" stroke-width="${u}"/>`;if(big)h+=`<text x="${c[0]}" y="${Yf(c[1])}" text-anchor="middle" dominant-baseline="middle" font-size="${fs*.85}" font-weight="600" fill="#fff" font-family="var(--sans)" pointer-events="none">${isIn?'입':'출'}</text>`});
  S.hs.forEach((s,i)=>{const x=s.x-s.lx/2,y=Yf(s.y+s.ly/2);if(big)h+=`<g class="hsg${typeof HSX!=='undefined'&&HSX===i?' showx':''}">`;
    h+=`<rect x="${x}" y="${y}" width="${s.lx}" height="${s.ly}" fill="none" stroke="#0B1A22" stroke-width="${u*2.6}" pointer-events="none"/>`;
    h+=`<rect ${big?`class="hsb" data-i="${i}" style="cursor:grab;touch-action:none"`:''} x="${x}" y="${y}" width="${s.lx}" height="${s.ly}" fill="transparent" stroke="#fff" stroke-width="${u*(i===selHs&&big?1.6:1)}"/>`;
    if(big)h+=`<text x="${x+s.lx/2}" y="${y-u*5}" text-anchor="middle" font-size="${fs}" font-weight="600" fill="var(--ink)" font-family="var(--sans)" pointer-events="none">H${i+1}</text><g class="hsx" data-hsx="${i}" role="button" aria-label="H${i+1} 지우기"><title>H${i+1} 지우기</title><circle cx="${x+s.lx}" cy="${y}" r="${u*9}" fill="#13224A" stroke="#fff" stroke-width="${u*1.5}"/><path d="M${x+s.lx-u*3.5} ${y-u*3.5}l${u*7} ${u*7}m0 ${-u*7}l${-u*7} ${u*7}" stroke="#fff" stroke-width="${u*1.8}" stroke-linecap="round" pointer-events="none"/></g></g>`});
  return h;
}
function drawMaps(){
  if(!res.length)return;
  imgs={};const [lo,hi,name]=range();
  $('tiles').innerHTML=res.map((r,i)=>{const unit=view==='temp'?(()=>{const c=r.Tmax.toFixed(1),h=r.hot.length?Math.max(...r.hot.map(q=>q.max)).toFixed(1):c;return h===c?`칩·핫스팟 최고 온도 ${c} °C`:`칩 최고 온도 ${c} °C\n핫스팟 최고 온도 ${h} °C`})():view==='geo'?r.d.note:view==='vch'?`최대 ${r.vmax.toFixed(2)} m/s`:(!r.d.ref?`최대 ${(Math.max(...r.S)*S.Q/Q0/1000).toFixed(2)} m/s`:'매니폴드 없음');
    return `<button type="button" class="tile ${i===sel?'on':''}" data-i="${i}"><svg viewBox="-.1 -.1 12.2 12.2" aria-hidden="true">${picture(r,lo,hi,false)}</svg><b>${esc(r.d.name)}</b><small>${esc(unit)}</small></button>`}).join('');
  $('stage').setAttribute('viewBox','-.25 -.55 12.5 13.3');
  const r=res[sel];let h=picture(r,lo,hi,true);
  for(let x=0;x<=Z;x+=2){const fs=Z/540*11;h+=`<line x1="${x}" y1="${Z}" x2="${x}" y2="${Z+.1}" stroke="var(--muted)" stroke-width=".02"/><text x="${x}" y="${Z+.12+fs}" text-anchor="middle" font-size="${fs}" fill="var(--muted)" font-family="var(--mono)">${x}</text>`}
  $('stage').innerHTML=h;
  $('stTitle').textContent=`${r.d.name} · ${r.d.note}`;
  const show=view!=='geo';$('legend').hidden=!show;$('geoKey').hidden=show;$('lgScale').hidden=view!=='temp';
  if(show){$('lgName').textContent=name;drawLegend(lo,hi)}
}
function layerSvg(title,paint){
  const c=document.createElement('canvas'),P=240;c.width=P;c.height=P;const x=c.getContext('2d');
  x.fillStyle='#8FB8D8';x.fillRect(0,0,P,P);x.fillStyle='#fff';paint(x,P/Z);
  let t='';for(let v=0;v<=Z;v+=2){t+=`<text x="${v*10+22}" y="143" text-anchor="middle" class="ly">${v}</text><text x="17" y="${122-v*10+3}" text-anchor="end" class="ly">${v}</text>`}
  return `<figure class="ly-p"><figcaption>${esc(title)}</figcaption><svg viewBox="0 -6 150 154" role="img" aria-label="${esc(title)}"><image href="${c.toDataURL()}" x="22" y="2" width="120" height="120"/><rect x="22" y="2" width="120" height="120" fill="none" stroke="var(--ink)" stroke-width=".8"/>${t}</svg></figure>`;
}
function drawLayers(){
  const r=res[sel];if(!r)return;const d=r.d,t=parseFloat(S.t),z=v=>(+v.toFixed(3)).toString(),rows=[];
  const fy=(y,h,sc)=>(Z-y-h)*sc;
  rows.push(layerSvg(`히터층 · 핫스팟 분리`,(x,sc)=>{x.fillRect(0,0,240,240);x.fillStyle='#8FB8D8';x.fillRect(0,0,240,240);x.fillStyle='#fff';for(const h of S.hs)x.fillRect((h.x-h.lx/2)*sc,fy(h.y-h.ly/2,h.ly,sc),h.lx*sc,h.ly*sc)}));
  rows.push(layerSvg(`바닥판 · z 0~0.1`,()=>{}));
  rows.push(layerSvg(`채널층 · z 0.1~0.5`,(x,sc)=>{const[ya,yb]=chY(d);for(let j=0;j<N;j++)x.fillRect((chX(j)-WC/2)*sc,fy(ya,yb-ya,sc),WC*sc,(yb-ya)*sc);if(d.head){x.fillRect(.625*sc,fy(.5,1,sc),10.75*sc,sc);x.fillRect(.625*sc,fy(10.5,1,sc),10.75*sc,sc)}}));
  if(d.layers){
    const up=d.layers.slice(1).reduce((a,l)=>a+l.h,0),fac=(t-.2)/up;let zb=.5;
    d.layers.forEach((l,i)=>{if(l.z)zb=l.z[0];const hh=i?l.h*fac:.2,zt=l.z?l.z[1]:zb+hh,name=l.n||(i===0?'슬롯층':d.layers.length>2?`매니폴드 ${i}층`:'매니폴드층'),mask=l.M;
      rows.push(layerSvg(`${name} · z ${z(zb)}~${z(zt)}`,(x)=>{const c=document.createElement('canvas');c.width=120;c.height=120;const g=c.getContext('2d'),im=g.createImageData(120,120);for(let py=0;py<120;py++)for(let ix=0;ix<120;ix++){const o=(py*120+ix)*4,v=mask[(119-py)*120+ix];im.data[o]=im.data[o+1]=im.data[o+2]=255;im.data[o+3]=v?255:0}g.putImageData(im,0,0);x.imageSmoothingEnabled=false;x.drawImage(c,0,0,240,240)}));zb=zt});
    if(d.pz)zb=d.pz[0];
    rows.push(layerSvg(`포트층 · z ${z(zb)}~${z(zb+.5)}`,(x,sc)=>{for(const c of d.ports){x.beginPath();x.arc(c[0]*sc,(Z-c[1])*sc,(d.k==='M4'?.5:.4)*sc,0,7);x.fill()}}));
  } else rows.push(layerSvg(`포트층 · 덮개 위`,(x,sc)=>{for(const c of d.ports){x.beginPath();x.arc(c[0]*sc,(Z-c[1])*sc,.4*sc,0,7);x.fill()}}));
  $('layers').innerHTML=rows.join('');$('lyTitle').textContent=`층별 구조 · ${d.name}`;
}
function drawLegend(lo,hi){
  const W=600,l=26,r=26,y0=30,hb=18,pw=W-l-r,bw=pw/BANDS;let h='';
  for(let k=0;k<BANDS;k++){const[c1,c2,c3]=cmapRaw(k/(BANDS-1));h+=`<rect x="${l+k*bw}" y="${y0}" width="${bw+.5}" height="${hb}" fill="rgb(${c1},${c2},${c3})"/>`}
  for(let k=0;k<=25;k++){const x=l+pw*k/25,big=k%5===0;h+=`<line x1="${x}" x2="${x}" y1="${y0-(big?8:4)}" y2="${y0}" stroke="var(--muted)"/>`}
  const dec=hi<10?2:1;
  for(let k=0;k<=5;k++){const v=lo+(hi-lo)*k/5,x=l+pw*k/5;h+=`<text x="${x}" y="${y0-11}" text-anchor="middle" font-size="14" fill="var(--ink)" font-family="var(--sans)">${v.toFixed(k===5?2:dec)}</text>`}
  for(const x of [l,W-r])h+=`<path d="M${x} ${y0+hb} l-7 11 h14 z" fill="var(--ink)"/>`;
  $('legSvg').innerHTML=h;
}
function svgPt(e){const s=$('stage'),p=s.createSVGPoint();p.x=e.clientX;p.y=e.clientY;const q=p.matrixTransform(s.getScreenCTM().inverse());return{x:q.x,y:Z-q.y}}
$('stage').addEventListener('pointerdown',e=>{const t=e.target;if(t.dataset?.i===undefined)return;const i=+t.dataset.i,p=svgPt(e),s=S.hs[i];selHs=i;drag={i,dx:p.x-s.x,dy:p.y-s.y};$('stage').setPointerCapture(e.pointerId);renderHs();e.preventDefault()});
$('stage').addEventListener('pointermove',e=>{
  const p=svgPt(e);
  if(drag){const s=S.hs[drag.i];s.x=+Math.max(CHIP.x0+s.lx/2,Math.min(CHIP.x1-s.lx/2,p.x-drag.dx)).toFixed(2);s.y=+Math.max(CHIP.y0+s.ly/2,Math.min(CHIP.y1-s.ly/2,p.y-drag.dy)).toFixed(2);syncHs(drag.i);schedule();return}
  if(!res.length||p.x<0||p.x>Z||p.y<0||p.y>Z)return;
  const r=res[sel],j=stripAt(p.x),i=Math.min(NX-1,Math.floor(p.y/DY));let t=`x ${p.x.toFixed(2)} · y ${p.y.toFixed(2)} mm · ${r.field[j*NX+i].toFixed(1)} °C`;
  const c=Math.round((p.y-Y0)/DY);if(c>=0&&c<=NC)t+=` · 채널 ${j+1} 유속 ${(Math.abs(r.F[j*(NC+1)+c])*S.Q/Q0/G.A).toFixed(2)} m/s`;
  $('readout').textContent=t;
});
$('stage').addEventListener('pointerup',()=>{if(drag){justDragged=true;drag=null;schedule()}});
$('stage').addEventListener('pointercancel',()=>{drag=null});
$('stage').addEventListener('click',e=>{if(justDragged){justDragged=false;return}if(e.target.dataset?.i!==undefined)return;const p=svgPt(e);if(p.x<CHIP.x0||p.x>CHIP.x1||p.y<CHIP.y0||p.y>CHIP.y1)return;
  S.hs.push({x:+Math.max(CHIP.x0+1,Math.min(CHIP.x1-1,p.x)).toFixed(2),y:+Math.max(CHIP.y0+1,Math.min(CHIP.y1-1,p.y)).toFixed(2),lx:2,ly:2,q:300});selHs=S.hs.length-1;renderHs();schedule()});
function syncHs(i){const s=S.hs[i];for(const k of['x','y']){const el=$(`hs-${i}-${k}`);if(el)el.value=s[k]}}
function renderHs(){
  $('hsList').innerHTML=S.hs.map((s,i)=>`<div class="hs ${i===selHs?'sel':''}"><div class="hs-t"><span>H${i+1}</span><button type="button" data-del="${i}" aria-label="H${i+1} 삭제">삭제</button></div>
    <div class="grid3">${[['x','위치 x','mm'],['y','위치 y','mm'],['q','열유속','W/cm²'],['lx','가로','mm'],['ly','세로','mm']].map(([k,l,u])=>`<label class="f"><span>${l} <b>${u}</b></span><input id="hs-${i}-${k}" data-h="${i}" data-k="${k}" type="number" step="${k==='q'?10:.1}" value="${s[k]}"></label>`).join('')}</div></div>`).join('')||'<p class="note">핫스팟이 없습니다.</p>';
}
$('hsList').addEventListener('input',e=>{const t=e.target;if(t.dataset.h===undefined)return;const v=parseFloat(t.value);if(!isFinite(v))return;S.hs[+t.dataset.h][t.dataset.k]=v;selHs=+t.dataset.h;schedule()});
$('hsList').addEventListener('click',e=>{const d=e.target.dataset?.del;if(d===undefined)return;S.hs.splice(+d,1);selHs=0;renderHs();schedule()});
$('addHs').onclick=()=>{S.hs.push({x:6,y:6,lx:2,ly:2,q:300});selHs=S.hs.length-1;renderHs();schedule()};
$('resetHs').onclick=()=>{S.hs=HS0.map(h=>({...h}));selHs=0;renderHs();schedule()};
$('tm').value=S.t;$('tm').addEventListener('change',()=>{S.t=$('tm').value;schedule()});
if(![235,390,148].includes(+S.ks))S.ks=235;
{const el=$('wprop');if(el){el.value=S.wprop||'T';el.addEventListener('change',()=>{S.wprop=el.value;save();schedule()})}}
['Tin','q0','ks'].forEach(k=>{const el=$(k);el.value=S[k];el.addEventListener('input',()=>{const v=parseFloat(el.value);if(isFinite(v)){S[k]=v;schedule()}})});
const setQ=v=>{S.Q=Math.min(qcap,Math.max(10,Math.round(v)));$('Q').value=S.Q;$('Qr').value=S.Q};
$('Q').addEventListener('input',()=>{const v=parseFloat($('Q').value);if(isFinite(v)&&v>=10){S.Q=v;$('Qr').value=v;schedule()}});
$('Qr').addEventListener('input',()=>{setQ(+$('Qr').value);schedule()});
['Tlim','dpMax'].forEach(k=>{const el=$(k);el.value=S[k]??'';el.addEventListener('input',()=>{const v=parseFloat(el.value);S[k]=isFinite(v)?v:null;save();if(k==='dpMax'){AUTO.key=null;schedule()}else if(res.length){pickOpt();render()}})});
const syncInl=()=>document.querySelectorAll('[data-inl]').forEach(x=>x.setAttribute('aria-pressed',x.dataset.inl===S.inl));
document.querySelectorAll('[data-inl]').forEach(b=>b.onclick=()=>{S.inl=b.dataset.inl;syncInl();schedule()});syncInl();
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>{view=b.dataset.view;document.querySelectorAll('[data-view]').forEach(x=>x.setAttribute('aria-pressed',x===b));drawMaps()});
document.querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>{S.mode=b.dataset.mode;document.querySelectorAll('[data-mode]').forEach(x=>x.setAttribute('aria-pressed',x===b));save();if(res.length){pickOpt();render()}});
$('lgScale').onclick=()=>{fromInlet=!fromInlet;$('lgScale').textContent=fromInlet?'표면 온도 범위로 보기':'입구 온도부터 보기';drawMaps()};
$('tiles').addEventListener('click',e=>{const t=e.target.closest('.tile');if(!t)return;sel=+t.dataset.i;render()});
$('cmp').addEventListener('click',e=>{const t=e.target.closest('tr[data-i]');if(!t)return;sel=+t.dataset.i;render()});
function schedule(){clearTimeout(timer);$('vEyebrow').textContent='다시 계산 대기';timer=setTimeout(compute,120)}
// validR: 수치적으로 유효한 결과만 (유한값, 에너지 수지 오차 5 % 미만, 열 반복 수렴). feas: 거기에 Re·ΔP·최고 온도 한도까지 만족
const validR=r=>{
  if(!r||r.conv!==true||r.rangeOK!==true)return false;   // 수렴·범위 플래그가 명시적으로 true인 결과만 유효
  if(![r.Tmax,r.Tmin,r.Tavg,r.dp,r.ReMax,r.res,r.Qml].every(Number.isFinite))return false;
  if(r.dp<0||r.ReMax<0||r.Qml<=0||r.energyOK!==true)return false;   // 에너지 수지: 상대 5 % (발열 > 1e-6 W) 또는 절대 1e-6 W (발열 0 W 근방)
  if(!Array.isArray(r.hot)||!r.hot.every(h=>h.cells>0&&Number.isFinite(h.max)&&Number.isFinite(h.avg)))return false;
  return true};
const feas=r=>validR(r)&&r.ReMax<=2300&&(S.dpMax==null||r.dp<=S.dpMax*1e3)&&r.Tmax<=(S.Tlim??85);
function pickOpt(){
  if(!hasHeat()){opt=null;return}   // 발열 0 W: 최적 운전 조건 없음
  const pool=allPool.filter(r=>!r.d.ref&&validR(r));if(!pool.length){opt=null;return}
  const T=pool.map(r=>r.Tmax),D=pool.map(r=>Math.log10(r.dp)),T0=Math.min(...T),T1=Math.max(...T),D0=Math.min(...D),D1=Math.max(...D);
  const sc=r=>engScore(r,S.mode)+.05*(parseFloat(r.tm)-.55)/.45;
  const ok=pool.filter(feas);opt=(ok.length?ok:pool).reduce((a,b)=>sc(a)<=sc(b)?a:b);opt.ok=ok.length>0;
}
const M4D=DESIGNS.find(d=>d.k==='M4'),DORD=DESIGNS.slice();
function syncDirect(){const cur=DESIGNS[sel],i=DESIGNS.indexOf(M4D);
  if(!S.direct&&i>=0)DESIGNS.splice(i,1);
  else if(S.direct&&i<0){const o=DORD.indexOf(M4D);let at=DESIGNS.length;for(let k=o+1;k<DORD.length;k++){const j=DESIGNS.indexOf(DORD[k]);if(j>=0){at=j;break}}DESIGNS.splice(at,0,M4D)}
  if(!S.direct&&typeof SH!=='undefined'&&SH.pick===M4D)SH.pick=null;
  const n=DESIGNS.indexOf(cur);sel=n>=0?n:Math.min(3,DESIGNS.length-1)}
async function compute(){
  syncDirect();save();const my=++token;const p={...S,hs:S.hs.map(h=>({...h}))};
  let out;try{G=setup(p);out=DESIGNS.map(d=>evaluate(G,d,S.Q,S.t))}catch(e){$('vEyebrow').textContent='입력 오류 — 계산하지 않았습니다';$('vName').textContent=e&&e.message?e.message:String(e);$('warns').innerHTML=`<li>${esc(e&&e.message?e.message:e)}</li>`;return}
  res=out;FAILS.length=0;render();
  if(!(await autoDesign(my)))return;
  try{res=DESIGNS.map(d=>evaluate(G,d,S.Q,S.t))}catch(e){FAILS.push('재계산 오류: '+(e.message||e))}render();
  // 유량 스윙: 한 점이 실패해도 나머지는 계속, 실패는 FAILS에 기록
  // 예외가 나거나 유효성 검사에 실패한 점은 null(기록만 남김). 스윙 배열은 DESIGNS 순서를 그대로 유지하고(실패한 구조도 빈 배열로 남김) 각 배열에 구조 d를 붙인다
  const ev=(d,Q,t)=>{try{const x=evaluate(G,d,Q,t);if(!validR(x)){FAILS.push(`${d.name} ${Q} ml/min: 유효성 검사 실패`);return null}return x}catch(e){FAILS.push(`${d.name} ${Q} ml/min: ${e.message||e}`);return null}};
  const sw=[],pool=[],QSc=QS.some(q=>q<=qcap)?QS.filter(q=>q<=qcap):[qcap];SWQ=QSc.slice();
  for(const d of DESIGNS){const l=[];l.d=d;for(const Q of QSc){await new Promise(r=>setTimeout(r));if(my!==token)return;const x=ev(d,Q,S.t);l.push(x);if(x)pool.push(x)}sw.push(l)}   // 실패한 유량도 null로 자리를 유지 → l[i] ↔ SWQ[i] 정렬
  sweep=sw;drawSweep();
  for(const t of TMS){if(t===S.t)continue;for(const d of DESIGNS.slice(1))for(const Q of QS){await new Promise(r=>setTimeout(r));if(my!==token)return;const x=ev(d,Q,t);if(x)pool.push(x)}}
  allPool=pool;pickOpt();render();
}
const hotOf=r=>r.hot.length?Math.max(...r.hot.map(h=>h.max)):r.Tmax,tick=()=>new Promise(r=>setTimeout(r));
// 자동 최적 매니폴드: 핫스팟 배치가 바뀌면 후보 모양을 모두 만들어 풀고, 지금 조건에서 가장 좋은 것을 고른다
async function autoDesign(my){
  const st=t=>{$('autoStatus').textContent=t},drop=()=>{const i=DESIGNS.indexOf(AUTOD);if(i>=0){DESIGNS.splice(i,1);if(sel===i)sel=Math.min(3,DESIGNS.length-1);else if(sel>i)sel--}};
  if(!S.hs.length){drop();AUTO.key=null;AUTO.cands=[];AUTO.best=null;st('핫스팟을 하나 이상 놓으면 그 위치에 맞는 모양을 찾습니다.');drawAuto();return true}
  const HSN=(G&&G.p&&G.p.hs)||S.hs;   // setup()에서 정규화한 핫스팟(숫자 변환 완료)를 쓴다 — 형상 생성과 발열 계산에 같은 값이 들어가야 한다
  const key=JSON.stringify([S.inl,!!S.direct,HSN.map(h=>[h.x,h.y,h.lx,h.ly,h.q])]);
  if(AUTO.key!==key){
    AUTO.pick=null;if(DESIGNS.indexOf(AUTOD)>=0)AUTOD.note='핫스팟이 바뀌어 모양을 다시 찾는 중';
    if(drag){st('핫스팟을 놓으면 그 위치에 맞는 모양을 다시 찾습니다.');return true}
    const hs=HSN.map(h=>({...h})),specs=autoSpecs(hs).filter(q=>S.direct||q.fam!=='직상부 공급형'),list=[],seen=new Set();
    for(let i=0;i<specs.length;i++){
      st(`핫스팟 위치에 맞는 모양을 찾는 중입니다 (${i+1}/${specs.length})`);await tick();if(my!==token)return false;
      const sp=specs[i];
      try{const g=sp.make(),why=aCheck(g);
        if(why){list.push({name:sp.name,why});continue}
        const sg=aSig(g);if(seen.has(sg))continue;seen.add(sg);
        const sol=flowSolve(g,S.inl);if(!sol||!isFinite(sol.Rl)){list.push({name:sp.name,why:'포트가 유로에 닿지 않음'});continue}
        if(!sol.conv){list.push({name:sp.name,why:'유량장 풀이가 수렴하지 않음 (PCG 4000회)'});continue}
        list.push({name:sp.name,d:Object.assign({k:'A',name:'자동 최적 매니폴드',note:sp.name},aDesign(g,sol))});
      }catch(err){list.push({name:sp.name,why:'이 배치에서는 모양을 만들지 못함'})}
    }
    AUTO.key=key;AUTO.cands=list;
  }
  const ok=AUTO.cands.filter(c=>c.d);
  for(const c of ok){await tick();if(my!==token)return false;try{c.r=evaluate(G,c.d,S.Q,S.t)}catch(e){c.r=null;c.why='계산 오류: '+(e.message||e)}}
  if(!ok.length){drop();AUTO.best=null;AUTO.bestOk=false;st('이 핫스팟 배치에서는 만들 수 있는 모양을 찾지 못했습니다.');drawAuto();return true}
  // 선택 대상은 수치적으로 유효한 후보(validR)뿐. 유효 후보가 하나도 없으면 자동 설계를 내리고 종료
  const okv=ok.filter(c=>validR(c.r));
  if(!okv.length){drop();AUTO.best=null;AUTO.bestOk=false;st(`자동 설계 후보 ${ok.length}개가 모두 수치적으로 유효하지 않습니다(수렴 실패·비정상값·단상 범위 밖). 자동 최적 매니폴드를 표시하지 않습니다.`);drawAuto();return true}
  let best=AUTO.pick!=null&&AUTO.cands[AUTO.pick]&&AUTO.cands[AUTO.pick].d?AUTO.cands[AUTO.pick]:null,pickNote='';
  if(best&&!validR(best.r)){pickNote='직접 고른 모양은 계산이 유효하지 않아 자동 선택으로 돌아갔습니다. ';best=null;AUTO.pick=null}
  // 선택: 한도(feas: Re·ΔP·최고 온도 Tlim) 만족 후보 중 최고 온도 최저, 0.5 °C 이내면 ΔP 최소. 만족 후보가 없으면 유효 후보 중 가장 가까운 것을 "부적합"으로 표시
  if(!best){const lam=okv.filter(c=>feas(c.r)),pl=lam.length?lam:okv,tm=Math.min(...pl.map(c=>c.r.Tmax));best=pl.filter(c=>c.r.Tmax<=tm+.5).reduce((a,b)=>a.r.dp<=b.r.dp?a:b)}
  AUTO.bestOk=feas(best.r);AUTO.pickNote=pickNote;
  AUTO.best=best;const d=best.d;Object.assign(AUTOD,{T:d.T,U:d.U,P:d.P,ports:d.ports,head:0,ext:d.ext,e0:d.e0,en:d.en,pz:d.pz,layers:d.layers,note:best.name});
  if(DESIGNS.indexOf(AUTOD)<0){DESIGNS.splice(1,0,AUTOD);if(AUTO.first){sel=1;AUTO.first=false}else if(sel>=1)sel++}
  st(AUTO.pick!=null?'직접 고른 모양입니다. 핫스팟을 옮기면 다시 자동으로 고릅니다.':`${S.direct?'':'직상부 공급형을 뺀 '}후보 ${ok.length}개를 계산해 전체 최고 온도가 가장 낮은 모양을 골랐습니다. 차이가 0.5 °C 이내면 압력강하가 작은 쪽입니다.`);
  if(AUTO.pickNote)st(AUTO.pickNote+$('autoStatus').textContent);
  if(!hasHeat())st($('autoStatus').textContent+' ⚠ 총 발열이 0 W라 냉각 성능(최고 온도) 비교가 불가능합니다. 압력강하가 가장 작은 모양을 참고용으로만 표시하며 성능 우열이 아닙니다.');
  if(!AUTO.bestOk)st($('autoStatus').textContent+(AUTO.pick!=null?' ⚠ 직접 고른 모양은 한도(최고 온도·압력강하·Re)를 넘습니다 — 부적합 설계입니다.':` ⚠ 모든 제약조건(최고 온도 ${S.Tlim??85} °C · 압력강하 ${S.dpMax??'없음'} kPa · Re 2300)을 만족하는 설계가 없습니다. 정상 계산된 후보 중 최고 온도가 가장 낮은 설계를 참고용으로 표시합니다(제약 위반이 가장 작은 설계가 아닙니다) — 부적합 설계입니다.`));
  drawAuto();return true;
}
function drawAuto(){
  const b=AUTO.best,base=res[0];
  $('autoPick').textContent=b&&b.r?`${b.name} · 칩 최고 ${b.r.Tmax.toFixed(1)} °C${base?` (매니폴드 없음 ${base.Tmax.toFixed(1)} °C)`:''}${AUTO.bestOk===false?' · ⚠ 한도 밖(부적합)':''}`:'';
  $('autoReset').hidden=AUTO.pick==null;
  const ok=AUTO.cands.map((c,i)=>({c,i})).filter(x=>x.c.d&&x.c.r).sort((p,q)=>p.c.r.Tmax-q.c.r.Tmax),bad=AUTO.cands.filter(c=>c.why);
  $('autoDet').hidden=!AUTO.cands.length;$('autoSum').textContent=`후보 ${ok.length}개 비교 보기${bad.length?`, 만들 수 없는 모양 ${bad.length}개`:''}`;
  $('autoTbl').innerHTML=ok.map(({c,i})=>`<tr class="cand ${c===b?'on':''}" data-c="${i}"><td><button type="button" aria-pressed="${c===b}">${esc(c.name)}${c===b?'<span class="pill best">선택</span>':''}</button></td><td>${hotOf(c.r).toFixed(1)}</td><td>${c.r.Tmax.toFixed(1)}</td><td>${(c.r.dp/1e3).toFixed(1)}</td><td>${c.r.ReMax.toFixed(0)}</td></tr>`).join('')
    +bad.map(c=>`<tr class="fail"><td colspan="5">${esc(c.name)}: ${esc(c.why)}</td></tr>`).join('');
}
$('autoTbl').addEventListener('click',e=>{const t=e.target.closest('tr[data-c]');if(!t)return;AUTO.pick=+t.dataset.c;schedule()});
$('qPre').addEventListener('click',e=>{const q=e.target.dataset?.q;if(q){setQ(+q);schedule()}});
$('autoReset').onclick=()=>{AUTO.pick=null;schedule()};
$('autoDirect').checked=!!S.direct;$('autoDirect').onchange=()=>{S.direct=$('autoDirect').checked;schedule()};
function render(){
  if(sel>=res.length)sel=res.length-1;
  {const lim=res.reduce((a,b)=>b.ReMax/b.Qml>a.ReMax/a.Qml?b:a);const qRe=Math.max(30,Math.floor(2300*lim.Qml/lim.ReMax/10)*10);qcap=Math.min(QMAX,qRe);$('Qr').max=qcap;$('Q').max=qcap;
    $('qcapNote').textContent=qRe>=QMAX?`유량 한도 ${QMAX} ml/min (팀 설정 한도). 이 안에서는 모든 구조가 레이놀즈 수 2300 이하입니다.`:`유량 한도 ${qcap} ml/min. 이보다 많으면 ${lim.d.name}에서 레이놀즈 수가 2300을 넘습니다.`;
    if(S.Q>qcap){setQ(qcap);schedule()}}
  if($('qNom'))$('qNom').textContent=`논문 표기로는 약 ${Math.round(S.Q*QNOM/10)*10} ml/min 조건입니다. 버튼은 논문 표기 300, 450, 600, 750, 900 ml/min을 Re에 맞춰 바꾼 유량입니다.`;
  $('qPre').innerHTML=[68,136,203,300,600,900].map(q=>`<button type="button" data-q="${q}" aria-pressed="${q===S.Q}" ${q>qcap?'disabled':''}>${q}</button>`).join('');
  const base=res[0],best=res.slice(1).reduce((a,b)=>a.Tmax<=b.Tmax?a:b),r=res[sel],isB=r===best;
  $('vEyebrow').textContent=isB?`${S.Q} ml/min에서 칩 최고 온도를 가장 많이 낮춘 구조`:`${S.Q} ml/min, 선택한 구조`;
  $('vName').textContent=r.d.name;
  $('vSub').textContent=r.d.note;
  $('vT').textContent=r.Tmax.toFixed(1)+' °C';
  const dl=r.Tmax-base.Tmax,dEl=$('vD');dEl.textContent=r===base?'기준':(dl>0?'+':'−')+Math.abs(dl).toFixed(1)+' °C';dEl.className=r===base?'':dl<0?'good':'bad';
  $('vP').textContent=(r.dp/1e3).toFixed(1)+' kPa';
  $('ovh').textContent=r.Tmax>hotOf(r)+.5?`핫스팟 안 최고 온도는 ${hotOf(r).toFixed(1)} °C이고, 칩에서 가장 뜨거운 곳은 핫스팟 밖(x ${r.px.toFixed(1)}, y ${r.py.toFixed(1)} mm)입니다.`:'';
  const w=[];
  if(res.some(x=>x.ReMax>2300))w.push(`일부 구조는 레이놀즈 수가 2300을 넘습니다: ${res.filter(x=>x.ReMax>2300).map(x=>x.d.name).join(', ')}. 층류 가정이 맞지 않습니다.`);
  if(res.some(x=>x.RePort>1000))w.push(`포트 레이놀즈 수가 1000을 넘습니다 (최대 ${Math.max(...res.map(x=>x.RePort||0)).toFixed(0)}). 매니폴드 유동은 관성을 무시한 Stokes 저항망(유량에 비례 확대)으로 풀었으므로, 이 유량에서는 채널별 유량 분배와 포트·매니폴드 압력손실의 신뢰도가 낮습니다(추가 관성 손실 미반영). CFD로 분배·압력을 확인하세요.`);
  if(S.dpMax!=null&&res.some(x=>x.dp>S.dpMax*1e3))w.push(`일부 구조는 압력강하가 한도 ${S.dpMax} kPa를 넘습니다: ${res.filter(x=>x.dp>S.dpMax*1e3).map(x=>x.d.name).join(', ')}.`);
  {const HSN=G&&G.p?G.p.hs:S.hs,ov=[];for(let a=0;a<HSN.length;a++)for(let b=a+1;b<HSN.length;b++){const p=HSN[a],q=HSN[b];if(Math.abs(p.x-q.x)<(p.lx+q.lx)/2&&Math.abs(p.y-q.y)<(p.ly+q.ly)/2)ov.push(`H${a+1}·H${b+1}`)}
    if(ov.length)w.push(`핫스팟이 겹쳐 있습니다 (${ov.join(', ')}). 겹친 곳은 두 열유속 중 큰 값 하나만 적용합니다(더하지 않음). 의도한 배치가 아니면 핫스팟을 옮기세요.`)}
  if(!(G.Ptot>1e-6))w.push('총 발열이 0 W입니다. 열저항·CCPI·순위는 정의되지 않으므로 발열 조건(바닥 열유속·핫스팟)을 확인하세요.');
  if(res.some(x=>!validR(x)))w.push(`계산이 수렴하지 않았거나 값이 비정상이거나 단상 범위(유체 평균 ≤95 °C) 밖인 구조: ${res.filter(x=>!validR(x)).map(x=>x.d.name).join(', ')}. 순위와 최적 선택에서 제외합니다.`);
  if(FAILS.length)w.push(`계산 중 오류가 난 조건(건너뜀): ${FAILS.slice(0,5).join(' / ')}${FAILS.length>5?` 외 ${FAILS.length-5}건`:''}`);
  {const HSN=G&&G.p?G.p.hs:S.hs,pt=HSN.map((h,i)=>(h.x-h.lx/2<0||h.x+h.lx/2>Z||h.y-h.ly/2<0||h.y+h.ly/2>Z)?'H'+(i+1):null).filter(Boolean);if(pt.length)w.push(`판 밖으로 나간 핫스팟이 있습니다 (${pt.join(', ')}). 판 안쪽 부분만 발열로 계산합니다.`)}
  if(res.some(x=>x.Tmax>100))w.push(`최고 온도가 100 °C를 넘는 구조: ${res.filter(x=>x.Tmax>100).map(x=>x.d.name).join(', ')}. 단상(비등 없음) 모델의 유효 범위 밖이므로 값을 믿지 마세요.`);
  if(G.Ptot>1e-6&&res.some(x=>x.res>.01))w.push(`에너지 수지 오차가 1 %를 넘는 구조가 있습니다: ${res.filter(x=>x.res>.01).map(x=>`${x.d.name} ${(x.res*100).toFixed(1)} %`).join(', ')}. 수렴 부족이거나 유량장 데이터 문제입니다.`);
  $('warns').innerHTML=w.map(x=>`<li>${esc(x)}</li>`).join('');
  $('tblNote').textContent=`총 발열량 ${G.Ptot.toFixed(1)} W, 유량 ${S.Q} ml/min 기준입니다. 핫스팟 유량은 전체 채널 유량 중 핫스팟 위 채널로 가는 비율입니다.`;
  $('cmp').innerHTML=res.map((o,i)=>{const dv=o.Tmax-base.Tmax;return `<tr class="cand ${i===sel?'on':''}" data-i="${i}"><td><button type="button" data-i="${i}" aria-pressed="${i===sel}">${esc(o.d.name)}${o===best?'<span class="pill best">칩 최고 온도 최저</span>':''}</button><small>${esc(o.d.note)}</small></td><td>${o.Tmax.toFixed(1)}</td><td>${o===base?'–':(dv>0?'+':'')+dv.toFixed(1)}</td><td>${hotOf(o).toFixed(1)}</td><td>${o.Tavg.toFixed(1)}</td><td>${o.dT.toFixed(1)}</td><td>${(o.dp/1e3).toFixed(1)}</td><td>${o.vmax.toFixed(2)}</td><td>${(o.hotShare*100).toFixed(0)}</td></tr>`}).join('');
  if(opt){$('optNote').textContent=(opt.ok?'':'한도를 만족하는 조건이 없습니다. 유효한 결과 중 선택한 기준의 점수가 가장 좋은 조건을 참고용으로 표시합니다(부적합). ')+`${opt.d.name}, ${opt.Qml} ml/min, 전체 최고 ${opt.Tmax.toFixed(1)} °C, 압력강하 ${(opt.dp/1e3).toFixed(1)} kPa`;$('applyOpt').hidden=false}else{$('optNote').textContent=hasHeat()?'유량별 계산 중':'총 발열이 0 W라 최적 운전 조건을 정할 수 없습니다.';$('applyOpt').hidden=true}
  drawMaps();drawLayers();drawProfile();drawFlow();drawSim();
}
$('applyOpt').onclick=()=>{if(!opt||DESIGNS.indexOf(opt.d)<0)return;sel=DESIGNS.indexOf(opt.d);S.t=opt.tm;$('tm').value=opt.tm;setQ(opt.Qml);schedule()};
function legendHtml(el){$(el).innerHTML=RV().map(r=>`<span><i ${isD(r.d)?`class="dd" style="--c:${SER[r.d.k]}"`:`style="background:${SER[r.d.k]}"`}></i>${esc(r.d.name)}</span>`).join('')}
function drawProfile(){
  const W=860,H=300,l=46,r=14,t=10,b=34,pw=W-l-r,ph=H-t-b,hy=S.hs[selHs]?.y??6,ci=Math.min(NX-1,Math.floor(hy/DY));
  const RS=RV(),ser=RS.map(o=>Array.from({length:N},(_,j)=>o.field[j*NX+ci]));
  const all=ser.flat(),mn=Math.min(...all),mx=Math.max(...all),st=[1,2,5,10,20,50].find(s=>(mx-mn)/s<=6)||100;let y0=Math.floor(mn/st)*st,y1=Math.ceil(mx/st)*st;
  if(y1<=y0){const pad=Math.max(1,Math.abs(mn)*.05);y0=mn-pad;y1=mn+pad}   // 온도가 모두 같으면(발열 0 W) 축 폭 0 → NaN 방지
  const X=v=>l+pw*v/Z,Y=v=>t+ph*(1-(v-y0)/(y1-y0));let h='';
  for(const s of S.hs)if(Math.abs(s.y-hy)<=s.ly/2)h+=`<rect x="${X(s.x-s.lx/2)}" y="${t}" width="${X(s.x+s.lx/2)-X(s.x-s.lx/2)}" height="${ph}" fill="var(--hot)" fill-opacity=".1"/>`;
  for(let v=y0;v<=y1+1e-9;v+=st)h+=`<line x1="${l}" x2="${W-r}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--line)"/><text class="axis" x="${l-6}" y="${Y(v)+3.5}" text-anchor="end">${v}</text>`;
  for(let v=0;v<=Z;v+=2)h+=`<text class="axis" x="${X(v)}" y="${t+ph+14}" text-anchor="middle">${v}</text>`;
  h+=`<text class="axis" x="${l+pw/2}" y="${H-5}" text-anchor="middle">x, mm (붉은 띠가 핫스팟)</text><text class="axis" transform="translate(12 ${t+ph/2}) rotate(-90)" text-anchor="middle">표면 온도, °C</text>`;
  RS.forEach((o,k)=>{h+=`<polyline fill="none" stroke="${SER[o.d.k]}" stroke-width="${o===res[sel]||o.d.k==='A'?3:2}" ${o.d.ref?'stroke-dasharray="6 4"':isD(o.d)?DASH:''} points="${ser[k].map((v,j)=>`${X(chX(j)).toFixed(1)},${Y(v).toFixed(1)}`).join(' ')}"/>`});
  $('profile').innerHTML=h;legendHtml('pfLegend');
}
function drawSweep(){
  if(!sweep.length)return;if(SWM!=='tp'){drawSweepM();return}
  // 그래프에 올릴 수 있는 점: null 아님, 압력강하 > 0 (로그 축), 유한값 (6차 검토)
  const okP=o=>!!o&&Number.isFinite(o.dp)&&o.dp>0&&Number.isFinite(o.Tmax);
  const W=860,H=320,l=52,r=14,t=12,b=38,pw=W-l-r,ph=H-t-b,lg=Math.log10,all=SV().flat().filter(okP),ds=all.map(o=>o.dp/1e3),Ts=all.map(o=>o.Tmax);
  if(!all.length){$('sweep').innerHTML='';legendHtml('swLegend');return}
  let x0=Math.floor(lg(Math.min(...ds))),x1=Math.ceil(lg(Math.max(...ds)));const mn=Math.min(...Ts),mx=Math.max(...Ts),st=[2,5,10,20,50].find(s=>(mx-mn)/s<=6)||100;let y0=Math.floor(mn/st)*st,y1=Math.ceil(mx/st)*st;
  if(x1<=x0){x0-=1;x1+=1}                                        // 압력강하가 한 값(예: 정확히 1 kPa)뿐이면 로그 축 폭 0 → ±1 decade (눈금은 10의 거듭제곱 유지)
  if(y1<=y0){const pad=Math.max(1,Math.abs(mn)*.05);y0=mn-pad;y1=mn+pad}   // 최고 온도가 한 값뿐이면(유효 결과 1개, 발열 0 W 등) 분모 0 → ±pad
  const X=v=>l+pw*(lg(v)-x0)/(x1-x0),Y=v=>t+ph*(1-(v-y0)/(y1-y0));let h='';
  for(let v=y0;v<=y1+1e-9;v+=st)h+=`<line x1="${l}" x2="${W-r}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--line)"/><text class="axis" x="${l-6}" y="${Y(v)+3.5}" text-anchor="end">${v}</text>`;
  for(let e=x0;e<=x1;e++)for(const m of [1,2,5]){const v=m*10**e;if(v>10**x1)continue;h+=`<line x1="${X(v)}" x2="${X(v)}" y1="${t}" y2="${t+ph}" stroke="var(--line)"/><text class="axis" x="${X(v)}" y="${t+ph+13}" text-anchor="middle">${+v.toPrecision(2)}</text>`}
  h+=`<text class="axis" x="${l+pw/2}" y="${H-5}" text-anchor="middle">압력강하, kPa (로그 눈금, 점 하나가 유량 하나)</text><text class="axis" transform="translate(12 ${t+ph/2}) rotate(-90)" text-anchor="middle">전체 최고 온도, °C</text>`;
  // 선: 무효 유량(null) 구간에서 끊어지는 path (앞 점이 없으면 M, 있으면 L). 원 배열 인덱스 i 유지, 좌표는 o 자체 값
  sweep.forEach((l2,k)=>{if(!l2.some(okP)||!SHOW(l2.d))return;const c=SER[l2.d.k];
    const pd=l2.map((o,i)=>okP(o)?`${okP(l2[i-1])?'L':'M'}${X(o.dp/1e3).toFixed(1)} ${Y(o.Tmax).toFixed(1)}`:null).filter(Boolean).join(' ');
    h+=`<path d="${pd}" fill="none" stroke="${c}" stroke-width="${l2.d.k==='A'?3:2}" ${l2.d.ref?'stroke-dasharray="6 4"':isD(l2.d)?DASH:''}/>`;
    l2.forEach((o,i)=>{if(!okP(o))return;h+=`<circle data-s="${k}" data-q="${i}" cx="${X(o.dp/1e3).toFixed(1)}" cy="${Y(o.Tmax).toFixed(1)}" r="4.5" fill="${c}" fill-opacity="${o.ReMax>2300?.3:1}" stroke="var(--panel)" stroke-width="1.5" style="cursor:pointer"/>`})});
  $('sweep').innerHTML=h;legendHtml('swLegend');
}
const swPt=e=>{const t=e.target.dataset;return t?.s===undefined?null:((sweep[+t.s]||[])[+t.q]||null)};
$('sweep').addEventListener('pointermove',e=>{const o=swPt(e);if(o)$('swInfo').textContent=`${o.d.name} · ${o.Qml} ml/min · ${o.Tmax.toFixed(1)} °C · ${(o.dp/1e3).toFixed(1)} kPa`});
$('sweep').addEventListener('click',e=>{const o=swPt(e);if(!o||DESIGNS.indexOf(o.d)<0)return;sel=DESIGNS.indexOf(o.d);setQ(o.Qml);schedule()});
function drawFlow(){
  const o=res[sel],qs=o.chFlow.map(q=>q*6e7),uni=S.Q/N,W=640,H=300,l=52,r=8,t=10,b=44,pw=W-l-r,ph=H-t-b,maxQ=Math.max(...qs,uni)*1.08;
  const step=[.5,1,2,5,10,20,50,100,200].find(s=>maxQ/s<=5)||500,y=v=>t+ph*(1-v/maxQ);let h='';
  for(const s of S.hs)h+=`<rect x="${l+pw*Math.max(0,(s.x-s.lx/2-.625)/10.75)}" y="${t}" width="${pw*s.lx/10.75}" height="${ph}" fill="var(--hot)" fill-opacity=".1"/>`;
  for(let v=0;v<=maxQ;v+=step)h+=`<line x1="${l}" x2="${W-r}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line)"/><text class="axis" x="${l-6}" y="${y(v)+5}" text-anchor="end">${v}</text>`;
  const bw=pw/N;
  qs.forEach((q,j)=>{h+=`<rect x="${l+j*bw+bw*.12}" y="${y(q)}" width="${bw*.76}" height="${t+ph-y(q)}" fill="var(--accent)"><title>채널 ${j+1}: ${q.toFixed(1)} ml/min</title></rect>`;if((j+1)%5===0)h+=`<text class="axis" x="${l+(j+.5)*bw}" y="${H-b+18}" text-anchor="middle">${j+1}</text>`});
  h+=`<line x1="${l}" x2="${W-r}" y1="${y(uni)}" y2="${y(uni)}" stroke="var(--hot)" stroke-width="1.4" stroke-dasharray="5 3"/><text class="axis" x="${l+pw/2}" y="${H-3}" text-anchor="middle">채널 번호 (점선은 균일 분배 ${uni.toFixed(1)} ml/min, 붉은 띠는 핫스팟)</text>`;
  $('flowChart').innerHTML=h;$('fcTitle').textContent=`채널별 유량, ml/min · ${o.d.name}`;
}
function drawSim(){
  const o=res[sel],lines=[`구조           ${o.d.name}`,...(o.d.k==='A'?[`모양           ${o.d.note}`]:[]),`총 유량        ${(S.Q/6e7).toExponential(2)} m³/s (${S.Q} ml/min)`,`입구 조건      ${S.inl==='q'?`포트마다 같은 유량 (각 ${(S.Q/12e7).toExponential(2)} m³/s)`:'같은 공급 압력'+(o.d.T[o.tm].sp?` (입구 1에 ${(o.d.T[o.tm].sp[0]*100).toFixed(0)} %, 입구 2에 ${(o.d.T[o.tm].sp[1]*100).toFixed(0)} %)`:'')}`,`입구 온도      ${S.Tin} °C`,`출구 게이지압  0 Pa`,`발열 영역      바닥 전체 12 × 12 mm`,o.d.ext?`매니폴드       관통층 0.5 mm, 덮개 홈 0.35 mm`:`매니폴드       두께 0.2 mm, 높이 0.3 mm`,`재질           ${S.ks?$('ks').selectedOptions[0].textContent:'미정'}`,`기본 열유속    ${(S.q0*1e4).toExponential(2)} W/m²`];
  S.hs.forEach((h,i)=>lines.push(`H${i+1} 열유속     ${(h.q*1e4).toExponential(2)} W/m² (${h.lx}×${h.ly} mm)`));
  const fw=G.fQ?G.fQ(S.Q):G.f;lines.push(`물 물성        ${S.wprop==='fixed'?'SimScale 고정값':'온도 의존'} · μ ${fw.mu.toExponential(3)} Pa·s, k ${fw.kf.toFixed(3)} W/m·K, ρ ${fw.rho.toFixed(1)} kg/m³`,`총 발열량      ${G.Ptot.toFixed(1)} W`,`예상 출구 수온 ${(S.Tin+G.Ptot/(fw.rho*(S.Q/6e7)*fw.cp)).toFixed(1)} °C (에너지 수지: SimScale 출구 온도가 이 값과 ±2% 넘게 다르면 열유속·유량 입력 확인)`,`에너지 수지 오차 ${G.Ptot>1e-6?(o.res*100).toFixed(2)+' % (상대, 1% 이하 정상)':'발열 0 W — 절대 오차 '+(o.eAbs||0).toExponential(2)+' W (상대오차 정의 안 됨)'}`,`단상 범위 검사  출구 수온 추정 ${Number.isFinite(o.ToutEst)?o.ToutEst.toFixed(1):'-'} °C, 채널 유체 최고 ${Number.isFinite(o.TfMax)?o.TfMax.toFixed(1):'-'} °C → ${o.rangeOK?'범위 안(≤95 °C)':'범위 밖 — 결과 무효'}`,`최대 Re        ${o.ReMax.toFixed(0)}${o.ReMax<2300?' (층류 설정)':' (난류 검토)'}`,`포트 Re        ${Number.isFinite(o.RePort)?o.RePort.toFixed(0):'-'} (입구 분배 ${(o.sp||[.5,.5]).map(v=>(v*100).toFixed(0)+' %').join(' / ')}${Number.isFinite(o.RePort)&&o.RePort>1000?' — 관성 영역, 분배·압력 신뢰도 낮음':''})`,`예상 전체 최고 ${o.Tmax.toFixed(1)} °C (축소 모델)`,`예상 압력강하  ${(o.dp/1e3).toFixed(1)} kPa (축소 모델: 채널·매니폴드 ${(o.dpLin/1e3).toFixed(1)} + 입구 발달 ${(o.dpDev/1e3).toFixed(1)} + 포트 ${(o.dpPort/1e3).toFixed(1)})`);
  $('sim').textContent=lines.join('\n');
}
function csv(){
  const hotOf=r=>r.hot.length?Math.max(...r.hot.map(h=>h.max)):r.Tmax,rows=['구조,입구 조건,유량(ml/min),두께(mm),핫스팟 최고(°C),전체 최고(°C),평균(°C),온도차(°C),압력강하(kPa),최대 유속(m/s),최대 Re,핫스팟 유량(%),에너지 수지 오차(%)'];
  const line=o=>[o.d.k==='A'?`"자동 최적 매니폴드: ${o.d.note}"`:o.d.name,S.inl==='q'?'같은 유량':'같은 압력',o.Qml,o.tm,hotOf(o).toFixed(2),o.Tmax.toFixed(2),o.Tavg.toFixed(2),o.dT.toFixed(2),(o.dp/1e3).toFixed(2),o.vmax.toFixed(3),o.ReMax.toFixed(0),(o.hotShare*100).toFixed(1),(o.res*100).toFixed(2)].join(',');
  res.forEach(o=>rows.push(line(o)));allPool.forEach(o=>rows.push(line(o)));
  return '﻿'+rows.join('\r\n')+'\r\n';
}
$('xCsv').onclick=async()=>{const st=$('xStatus');try{await downloads.save({filename:`hotspot_compare_Q${S.Q}.csv`,data:csv()});st.textContent='결과표 저장을 요청했습니다.'}catch(e){st.textContent=e?.code==='declined'?'저장을 취소했습니다.':'파일을 저장하지 못했습니다. 결과표 복사를 쓰세요.'}};
$('xCopy').onclick=async()=>{const st=$('xStatus');try{await navigator.clipboard.writeText(csv());st.textContent='결과표를 복사했습니다. 엑셀에 붙여 넣으세요.'}catch(e){const p=$('sim');p.textContent=csv();const g=document.createRange();g.selectNodeContents(p);const s=getSelection();s.removeAllRanges();s.addRange(g);st.textContent='복사가 막혀 있어 아래에 표를 펼치고 선택해 두었습니다. Ctrl+C로 복사하세요.'}};
setQ(S.Q);document.querySelectorAll('[data-mode]').forEach(x=>x.setAttribute('aria-pressed',x.dataset.mode===S.mode));renderHs();compute();
/* ---------- 흐름 움직임: 열화상(온도 픽셀이 흐름 따라 일렁임) / 입자(채널 흐름 줄무늬) ---------- */
const FLOW={mode:(window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches)?'off':'thermal',raf:0,key:null,f:null,pts:[],els:[],last:0,t0:0,img:null,th:null,lastF:0};
const FLIFE=3,FPER=11,FVD=3.2;
function flowField(r){
  const d=r.d,F=r.F,[ya,yb]=chY(d),ch=[];let m=0;
  for(let k=0;k<F.length;k++)m=Math.max(m,Math.abs(F[k]));m=m||1;
  for(let j=0;j<N;j++){
    const o=j*(NC+1);
    ch.push(y=>{
      if(y<ya||y>yb)return 0;
      if(y<Y0){const f=F[o];return d.ext?f*Math.max(0,(y-ya)/(Y0-ya)):f}
      if(y>Y1){const f=F[o+NC];return d.ext?f*Math.max(0,(yb-y)/(yb-Y1)):f}
      const c=(y-Y0)/DY,i=Math.min(NC-1,Math.floor(c)),t=c-i;return F[o+i]*(1-t)+F[o+i+1]*t});
  }
  return {ch,ya,yb,v:(j,y)=>ch[j](y)/m*FVD};
}
/* 매끄럽게 반복되는 잡음 무늬 (64 × 64, 양선형 보간) */
const FNOISE=(()=>{const n=64,a=new Float32Array(n*n);let s=12345;const rnd=()=>(s=(s*1103515245+12345)>>>0)/4294967296;
  const g=new Float32Array(16*16);for(let i=0;i<g.length;i++)g[i]=rnd()*2-1;
  const sm=t=>t*t*(3-2*t);
  for(let y=0;y<n;y++)for(let x=0;x<n;x++){const fx=x/4,fy=y/4,x0=Math.floor(fx),y0=Math.floor(fy),tx=sm(fx-x0),ty=sm(fy-y0),G=(i,j)=>g[(j&15)*16+(i&15)];
    a[y*n+x]=(G(x0,y0)*(1-tx)+G(x0+1,y0)*tx)*(1-ty)+(G(x0,y0+1)*(1-tx)+G(x0+1,y0+1)*tx)*ty}
  let mx=0;for(const v of a)mx=Math.max(mx,Math.abs(v));for(let i=0;i<a.length;i++)a[i]/=mx;
  return (x,y)=>{x=((x%n)+n)%n;y=((y%n)+n)%n;const x0=Math.floor(x),y0=Math.floor(y),tx=x-x0,ty=y-y0,x1=(x0+1)%n,y1=(y0+1)%n;
    return (a[y0*n+x0]*(1-tx)+a[y0*n+x1]*tx)*(1-ty)+(a[y1*n+x0]*(1-tx)+a[y1*n+x1]*tx)*ty}})();
const TLIFE=4.5,TP=240,TFPS=30;
function thermalSetup(r){
  const P=TP,h=Z/P,f=FLOW.f,vel=new Float32Array(P*P),base=new Float32Array(P*P),mask=new Uint8Array(P*P),VCH=view==='vch';
  const cx=[...Array(N)].map((_,j)=>chX(j));
  const T=(j,y)=>{const c=Math.max(0,Math.min(NX-1,y/DY-.5)),i=Math.min(NX-2,Math.floor(c)),t=c-i;return r.field[j*NX+i]*(1-t)+r.field[j*NX+i+1]*t};
  for(let i=0;i<P;i++){const y=(i+.5)*h;for(let ix=0;ix<P;ix++){const X=(ix+.5)*h;
    let j0,j1,t;if(X<=cx[0]){j0=j1=0;t=0}else if(X>=cx[N-1]){j0=j1=N-1;t=0}else{j0=Math.floor((X-X0)/PITCH);j1=j0+1;t=(X-cx[j0])/PITCH}
    const k=i*P+ix;
    if(VCH){const jj=Math.round((X-X0)/PITCH),inC=jj>=0&&jj<N&&Math.abs(X-chX(jj))<=WC/2&&y>=chY(r.d)[0]&&y<=chY(r.d)[1];mask[k]=inC?1:0;base[k]=inC?Math.abs(f.ch[jj](y))*S.Q/Q0/G.A:0}
    else{mask[k]=1;base[k]=T(j0,y)*(1-t)+T(j1,y)*t}
    const inArr=X>=CHIP.x0&&X<=CHIP.x1;vel[k]=inArr?(f.v(j0,y)*(1-t)+f.v(j1,y)*t)*.65:0}}
  {const R=8,tmp=new Float32Array(P*P);for(let pass=0;pass<2;pass++){
    for(let i=0;i<P;i++){let acc=0;for(let x=-R;x<=R;x++)acc+=vel[i*P+Math.min(P-1,Math.max(0,x))];for(let x=0;x<P;x++){tmp[i*P+x]=acc/(2*R+1);acc+=vel[i*P+Math.min(P-1,x+R+1)]-vel[i*P+Math.max(0,x-R)]}}
    for(let x=0;x<P;x++){let acc=0;for(let i=-R;i<=R;i++)acc+=tmp[Math.min(P-1,Math.max(0,i))*P+x];for(let i=0;i<P;i++){vel[i*P+x]=acc/(2*R+1);acc+=tmp[Math.min(P-1,i+R+1)*P+x]-tmp[Math.max(0,i-R)*P+x]}}}}
  const c=document.createElement('canvas');c.width=P;c.height=P;
  const lut=new Uint8Array(256*3);for(let q=0;q<256;q++){const cc=cmapRaw(q/255);lut.set(cc,q*3)}
  return {P,h,vel,base,mask,c,x:c.getContext('2d'),im:c.getContext('2d').createImageData(P,P),lut};
}
function thermalFrame(t){
  const th=FLOW.th,[lo,hi]=range(),span=hi-lo,P=th.P,h=th.h,d=th.im.data,L=TLIFE,K=6;
  const ta=t%L,tb=(t+L/2)%L,wa=1-Math.abs(2*ta/L-1),wb=1-wa,A=.05,A2=.03,Nn=.006,pulse=.012*Math.sin(t*2*Math.PI/1.5),lut=th.lut;
  for(let i=0;i<P;i++){const py=P-1-i,y=(i+.5)*h;for(let ix=0;ix<P;ix++){const k=i*P+ix,v=th.vel[k],x=(ix+.5)*h;
    const u=th.vx?th.vx[k]:0,K2=K*2.3,n=wa*FNOISE((x-u*ta)*K,(y-v*ta)*K)+wb*FNOISE((x-u*tb)*K+31,(y-v*tb)*K+17),n2=wa*FNOISE((x-u*ta*1.6)*K2+7,(y-v*ta*1.6)*K2+3)+wb*FNOISE((x-u*tb*1.6)*K2+51,(y-v*tb*1.6)*K2+29),sp=Math.min(1,Math.hypot(u,v)/(FVD*.65));
    let q=((th.base[k]+span*(A*n+A2*n2+(.5+sp)*pulse*n2+Nn*(Math.random()*2-1))-lo)/span*255)|0;q=q<0?0:q>255?255:q;
    const o=(py*P+ix)*4;if(!th.mask[k]){d[o]=150;d[o+1]=162;d[o+2]=166;d[o+3]=70;continue}d[o]=lut[q*3];d[o+1]=lut[q*3+1];d[o+2]=lut[q*3+2];d[o+3]=255}}
  th.x.putImageData(th.im,0,0);
  if(FLOW.img&&FLOW.img.isConnected)FLOW.img.setAttribute('href',th.c.toDataURL());
}
function flowSpawn(p,fresh){p.y=FLOW.f.ya+Math.random()*(FLOW.f.yb-FLOW.f.ya);p.age=fresh?Math.random()*FLIFE:0}
const FNOTE={thermal:'열화상: 정상 상태 온도 위에 물 흐름 방향대로 온도 무늬가 밀려갑니다. 일렁임은 보기용 효과(범위의 약 8%)입니다.',
  cool:'식는 과정: 핫스팟일수록 뜨거운 상태에서 시작해, 물이 먼저 닿는 곳부터 정상 상태까지 식습니다. 시간은 연출입니다.',
  particle:'입자: 반투명 줄이 채널 속 물의 방향과 빠르기를 보여줍니다. 길고 빠르면 유량이 많고, 멈춘 점은 물이 고인 곳입니다.',
  off:'멈춤: 움직임 없이 계산된 정상 상태만 보여줍니다.'};
const FNOTE_V={thermal:'열화상: 정상 상태 유속 위에 물 흐름 방향대로 무늬가 밀려갑니다. 일렁임은 보기용 효과(범위의 약 8%)입니다.',
  cool:'채워지는 과정: 처음엔 물이 멈춰 있다가, 물이 먼저 닿는 채널 구간부터 정상 유속까지 빨라집니다. 시간은 연출입니다.'};
const FNOTE_M={thermal:'열화상: 매니폴드 유속 위에 물 흐름 방향대로 무늬가 밀려갑니다. 방향은 포트까지의 물길로 추정한 값입니다.',
  cool:'채워지는 과정: 입구 쪽 물길부터 물이 차고, 출구 쪽 물길은 그 뒤에 찹니다. 시간은 연출입니다.',
  particle:'입자: 반투명 줄이 매니폴드 안 물의 방향과 빠르기를 보여줍니다. 방향은 포트까지의 물길로 추정한 값입니다.'};
function flowSync(){const n=$('flowNote'),seg=$('flowSeg'),V=view==='vch'||view==='vman',VMn=view==='vman';if(n){n.hidden=!seg||seg.hidden;n.textContent=(VMn&&FNOTE_M[FLOW.mode])||(V&&FNOTE_V[FLOW.mode])||FNOTE[FLOW.mode]||''}const cb=document.querySelector('[data-flow=cool]');if(cb)cb.textContent=V?'채워지는 과정':'식는 과정';document.querySelectorAll('[data-flow]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.flow===FLOW.mode)))}
function flowMount(){
  const r=res[sel],seg=$('flowSeg'),okP=!!r&&(view==='temp'||view==='vch'||(view==='vman'&&!r.d.ref)),okT=okP,VM=view==='vman';
  if(seg){seg.hidden=!okP;seg.querySelectorAll('[data-flow=thermal],[data-flow=cool]').forEach(b=>b.disabled=!okT)}
  flowSync();FLOW.els=[];FLOW.img=null;
  const mode=(FLOW.mode==='thermal'||FLOW.mode==='cool')&&!okT?'particle':FLOW.mode;
  if(!okP||mode==='off'){cancelAnimationFrame(FLOW.raf);FLOW.raf=0;return}
  FLOW.vm=VM;
  const key=view+'|'+r.d.k+'|'+r.tm+'|'+(r.d.note||'')+'|'+r.Qml+'|'+S.q0+'|'+S.Tin+'|'+S.ks+'|'+JSON.stringify(S.hs);
  if(FLOW.key!==key){FLOW.key=key;FLOW.f=flowField(r);FLOW.th=null;FLOW.tp=null;FLOW.coolT0=0;FLOW.pts=[];
    if(VM){const m=manSetup(r);FLOW.th=m.th;FLOW.tp=m.tp;FLOW.t0=new Float32Array(m.th.P*m.th.P);FLOW.tmx=range()[1];for(let k=0;k<340;k++){const p={};manSpawn(p,true);FLOW.pts.push(p)}}
    else for(let j=0;j<N;j++)for(let k=0;k<FPER;k++){const p={j};flowSpawn(p,true);FLOW.pts.push(p)}}
  if(mode==='thermal'||mode==='cool'){
    if(!FLOW.th)FLOW.th=thermalSetup(r);
    if(mode==='cool'){if(!FLOW.tp)FLOW.tp=coolSetup(r);if(FLOW.cur!=='cool'||!FLOW.coolT0)FLOW.coolT0=performance.now();
      const NS='http://www.w3.org/2000/svg',tx=document.createElementNS(NS,'text');tx.setAttribute('x','.2');tx.setAttribute('y','.55');tx.setAttribute('font-size','.42');tx.setAttribute('fill','#fff');tx.setAttribute('stroke','#0B1A22');tx.setAttribute('stroke-width','.08');tx.setAttribute('paint-order','stroke');tx.setAttribute('font-family','var(--sans)');tx.setAttribute('font-weight','700');tx.setAttribute('pointer-events','none');$('stage').appendChild(tx);FLOW.lab=tx;if(typeof drawLegend==='function'){drawLegend(range()[0],FLOW.tmx)}}
    FLOW.img=$('stage').querySelector('image');if(FLOW.img)FLOW.img.style.imageRendering='auto';
  }else{
    const NS='http://www.w3.org/2000/svg',g=document.createElementNS(NS,'g');
    g.setAttribute('pointer-events','none');g.setAttribute('stroke','#fff');g.setAttribute('stroke-linecap','round');g.setAttribute('stroke-width','.13');
    FLOW.els=FLOW.pts.map(p=>{const l=document.createElementNS(NS,'line');if(!VM){const x=chX(p.j);l.setAttribute('x1',x);l.setAttribute('x2',x)}g.appendChild(l);return l});
    const st=$('stage'),port=st.querySelector('circle');if(port)st.insertBefore(g,port);else st.appendChild(g);flowDraw();
  }
  FLOW.cur=mode;FLOW.vm=VM;
  if(!FLOW.raf){FLOW.last=performance.now();FLOW.raf=requestAnimationFrame(flowTick)}
}
function flowDraw(){
  if(FLOW.vm){FLOW.pts.forEach((p,i)=>{const l=FLOW.els[i];if(!l)return;const v=manV(p.x,p.y)||[0,0],L=Math.hypot(v[0],v[1]),t=Math.max(L*.22,.02)/(L||1);
    l.setAttribute('x1',p.x.toFixed(3));l.setAttribute('y1',Yf(p.y).toFixed(3));l.setAttribute('x2',(p.x-(L?v[0]*t:0)).toFixed(3));l.setAttribute('y2',Yf(p.y-(L?v[1]*t:.02)).toFixed(3));
    l.setAttribute('stroke-opacity',(.5*Math.sqrt(Math.sin(Math.PI*p.age/FLIFE))).toFixed(2))});return}
  const f=FLOW.f;FLOW.pts.forEach((p,i)=>{const l=FLOW.els[i];if(!l)return;const v=f.v(p.j,p.y),tail=Math.sign(v)*Math.max(Math.abs(v)*.22,.02);
    l.setAttribute('y1',(Yf(p.y)).toFixed(3));l.setAttribute('y2',(Yf(p.y-tail)).toFixed(3));
    l.setAttribute('stroke-opacity',(.5*Math.sqrt(Math.sin(Math.PI*p.age/FLIFE))).toFixed(2))});
}
function flowTick(now){
  if(typeof SH!=='undefined'&&SH.open&&SH.page!=='det'){FLOW.last=now;FLOW.raf=requestAnimationFrame(flowTick);return}
  const dt=Math.min(.05,(now-FLOW.last)/1000);FLOW.last=now;
  if(FLOW.cur==='thermal'||FLOW.cur==='cool'){
    if(!FLOW.img||!FLOW.img.isConnected){FLOW.raf=0;return}
    if(now-FLOW.lastF>=1000/TFPS){FLOW.lastF=now;FLOW.cur==='cool'?coolFrame((now-FLOW.coolT0)/1000):thermalFrame(now/1000)}
  }else{
    if(!FLOW.els.length||!FLOW.els[0].isConnected){FLOW.raf=0;return}
    const f=FLOW.f;
    if(FLOW.vm)for(const p of FLOW.pts){const v=manV(p.x,p.y);p.age+=dt;if(!v||p.age>=FLIFE){manSpawn(p,false);continue}p.x+=v[0]*dt;p.y+=v[1]*dt;if(!manV(p.x,p.y))manSpawn(p,false)}
    else for(const p of FLOW.pts){p.y+=f.v(p.j,p.y)*dt;p.age+=dt;if(p.age>=FLIFE||p.y<f.ya||p.y>f.yb)flowSpawn(p,false)}
    flowDraw();
  }
  FLOW.raf=requestAnimationFrame(flowTick);
}
{const _dm=drawMaps;drawMaps=function(){_dm();flowMount()}}
document.querySelectorAll('[data-flow]').forEach(b=>b.onclick=()=>{FLOW.mode=b.dataset.flow;FLOW.coolT0=0;cancelAnimationFrame(FLOW.raf);FLOW.raf=0;drawMaps()});
flowMount();
/* ---------- 식는 과정(연출): 처음엔 칩 전체가 범례 최고 온도, 물이 닿는 순서대로 정상 상태까지 식는다 ---------- */
const CL={cool:9,hold:2.5,w:1.4,cond:.7};
function coolSetup(r){
  const d=r.d,F=r.F,f=FLOW.f,[ya,yb]=chY(d),G=NX,h=Z/G,tau=new Float32Array(G*G).fill(1e9);
  let m=0;for(let k=0;k<F.length;k++)m=Math.max(m,Math.abs(F[k]));m=m||1;const eps=m*.02;
  const ia=Math.max(0,Math.round(ya/h)),ib=Math.min(G-1,Math.round(yb/h)-1);
  for(let j=0;j<N;j++){
    const o=j*(NC+1),t=new Float64Array(G).fill(1e9),src=new Uint8Array(G);
    for(let i=ia;i<=ib;i++){const y=(i+.5)*h;
      if(y<Y0){if(d.ext?F[o]>eps:false)src[i]=1;continue}
      if(y>Y1){if(d.ext?F[o+NC]<-eps:false)src[i]=1;continue}
      const c=Math.min(NC-1,Math.floor((y-Y0)/DY));if(F[o+c+1]-F[o+c]>eps*.5)src[i]=1}
    if(!d.ext){if(F[o]>eps)src[ia]=1;if(F[o+NC]<-eps)src[ib]=1}
    for(let i=ia;i<=ib;i++)if(src[i])t[i]=0;
    for(let it=0;it<3;it++){
      for(let i=ia+1;i<=ib;i++){const v=f.v(j,(i+.5)*h);if(v>1e-4)t[i]=Math.min(t[i],t[i-1]+h/v)}
      for(let i=ib-1;i>=ia;i--){const v=f.v(j,(i+.5)*h);if(v<-1e-4)t[i]=Math.min(t[i],t[i+1]+h/(-v))}}
    const [x0,x1]=[chX(j)-WC/2,chX(j)+WC/2];
    for(let ix=Math.floor(x0/h);ix<=Math.ceil(x1/h)-1;ix++)for(let i=ia;i<=ib;i++)tau[i*G+ix]=Math.min(tau[i*G+ix],t[i])}
  // 고체 전도로 번지는 냉각: 채널에서 떨어진 곳은 느리게 식는다 (chamfer 거리)
  const s1=h/CL.cond,s2=s1*Math.SQRT2;
  for(let it=0;it<2;it++){
    for(let i=0;i<G;i++)for(let x=0;x<G;x++){const k=i*G+x;let v=tau[k];
      if(x>0)v=Math.min(v,tau[k-1]+s1);if(i>0){v=Math.min(v,tau[k-G]+s1);if(x>0)v=Math.min(v,tau[k-G-1]+s2);if(x<G-1)v=Math.min(v,tau[k-G+1]+s2)}tau[k]=v}
    for(let i=G-1;i>=0;i--)for(let x=G-1;x>=0;x--){const k=i*G+x;let v=tau[k];
      if(x<G-1)v=Math.min(v,tau[k+1]+s1);if(i<G-1){v=Math.min(v,tau[k+G]+s1);if(x<G-1)v=Math.min(v,tau[k+G+1]+s2);if(x>0)v=Math.min(v,tau[k+G-1]+s2)}tau[k]=v}}
  {const R=3,tmp=new Float32Array(tau.length);for(let pass=0;pass<2;pass++){
    for(let i=0;i<G;i++)for(let x=0;x<G;x++){let s=0,n=0;for(let q=-R;q<=R;q++){const xx=x+q;if(xx>=0&&xx<G){s+=tau[i*G+xx];n++}}tmp[i*G+x]=s/n}
    for(let i=0;i<G;i++)for(let x=0;x<G;x++){let s=0,n=0;for(let q=-1;q<=1;q++){const ii=i+q;if(ii>=0&&ii<G){s+=tmp[ii*G+x];n++}}tau[i*G+x]=s/n}}}
  let mx=0;for(const v of tau)if(v<1e8)mx=Math.max(mx,v);const sc=mx>0?(CL.cool-CL.w)/mx:1;
  for(let k=0;k<tau.length;k++)tau[k]=Math.min(tau[k]*sc,CL.cool-CL.w);
  const th=FLOW.th||thermalSetup(r),P=th.P,tp=new Float32Array(P*P);
  for(let i=0;i<P;i++){    for(let ix=0;ix<P;ix++){const cx=Math.max(0,Math.min(G-1.001,(ix+.5)*G/P-.5)),cyy=Math.max(0,Math.min(G-1.001,(i+.5)*G/P-.5)),x0=Math.floor(cx),y0=Math.floor(cyy),tx=cx-x0,ty=cyy-y0;
      tp[i*P+ix]=(tau[y0*G+x0]*(1-tx)+tau[y0*G+x0+1]*tx)*(1-ty)+(tau[(y0+1)*G+x0]*(1-tx)+tau[(y0+1)*G+x0+1]*tx)*ty}}
  // 시작 온도: 물이 닿기 전엔 열유속이 큰 곳일수록 더 뜨겁다 (정상 온도 + 열유속에 비례한 추가 상승, 고체 전도로 번짐)
  const q=new Float32Array(P*P),hh=Z/P;
  for(let i=0;i<P;i++)for(let ix=0;ix<P;ix++){const x=(ix+.5)*hh,y=(i+.5)*hh;let v=S.q0;for(const s of S.hs)if(Math.abs(x-s.x)<=s.lx/2&&Math.abs(y-s.y)<=s.ly/2)v=s.q;q[i*P+ix]=v}
  const R=Math.max(1,Math.round(.5/hh)),tmp=new Float32Array(P*P);
  for(let pass=0;pass<3;pass++){
    for(let i=0;i<P;i++)for(let x=0;x<P;x++){let a=0,n=0;for(let k=-R;k<=R;k++){const xx=x+k;if(xx>=0&&xx<P){a+=q[i*P+xx];n++}}tmp[i*P+x]=a/n}
    for(let i=0;i<P;i++)for(let x=0;x<P;x++){let a=0,n=0;for(let k=-R;k<=R;k++){const ii=i+k;if(ii>=0&&ii<P){a+=tmp[ii*P+x];n++}}q[i*P+x]=a/n}}
  if(view==='vch'){FLOW.t0=new Float32Array(P*P);FLOW.tmx=range()[1];FLOW.th=th;return tp}
  let qm=0;for(const v of q)qm=Math.max(qm,v);
  const [lo,hi]=range(),E=.6*(hi-lo)/(qm||1),t0=new Float32Array(P*P);let tmx=hi;
  for(let k=0;k<P*P;k++){t0[k]=th.base[k]+E*q[k];if(t0[k]>tmx)tmx=t0[k]}
  FLOW.t0=t0;FLOW.tmx=tmx;
  FLOW.th=th;return tp;
}
function coolFrame(t){
  const th=FLOW.th,tp=FLOW.tp,t0=FLOW.t0,[lo]=range(),hi=FLOW.tmx,span=hi-lo,P=th.P,d=th.im.data,lut=th.lut,per=CL.cool+CL.hold,tt=t%per;
  for(let i=0;i<P;i++){const py=P-1-i;for(let ix=0;ix<P;ix++){const k=i*P+ix;let u=(tt-tp[k])/CL.w;u=u<0?0:u>1?1:u;u=u*u*(3-2*u);
    let q=((t0[k]+(th.base[k]-t0[k])*u-lo)/span*255)|0;q=q<0?0:q>255?255:q;const o=(py*P+ix)*4;if(!th.mask[k]){d[o]=150;d[o+1]=162;d[o+2]=166;d[o+3]=70;continue}d[o]=lut[q*3];d[o+1]=lut[q*3+1];d[o+2]=lut[q*3+2];d[o+3]=255}}
  th.x.putImageData(th.im,0,0);
  if(FLOW.img&&FLOW.img.isConnected)FLOW.img.setAttribute('href',th.c.toDataURL());
  if(FLOW.lab&&FLOW.lab.isConnected)FLOW.lab.textContent=tt<CL.cool?`물 공급 후 ${tt.toFixed(1)} s (연출)`:'정상 상태';
}
/* ---------- 매니폴드 유속 움직임 ----------
   저장된 매니폴드 데이터에는 유속 크기만 있고 방향이 없다. 방향은 같은 물길(입구망/출구망) 안에서
   포트까지의 길 거리로 만든다: 입구망은 입구 포트에서 멀어지는 쪽, 출구망은 출구 포트로 다가가는 쪽. */
function manDijkstra(net,G,seeds,cost){
  const D=new Float32Array(G*G).fill(1e9),hp=[];const push=(k,v)=>{hp.push([v,k]);let i=hp.length-1;while(i>0){const p=(i-1)>>1;if(hp[p][0]<=hp[i][0])break;[hp[p],hp[i]]=[hp[i],hp[p]];i=p}};
  const pop=()=>{const t=hp[0],l=hp.pop();if(hp.length){hp[0]=l;let i=0;for(;;){const a=2*i+1,b=a+1;let m=i;if(a<hp.length&&hp[a][0]<hp[m][0])m=a;if(b<hp.length&&hp[b][0]<hp[m][0])m=b;if(m===i)break;[hp[m],hp[i]]=[hp[i],hp[m]];i=m}}return t};
  for(const k of seeds){D[k]=0;push(k,0)}
  const nb=[[1,0,1],[-1,0,1],[0,1,1],[0,-1,1],[1,1,Math.SQRT2],[1,-1,Math.SQRT2],[-1,1,Math.SQRT2],[-1,-1,Math.SQRT2]];
  while(hp.length){const [v,k]=pop();if(v>D[k])continue;const x=k%G,y=(k/G)|0;
    for(const [dx,dy,w] of nb){const xx=x+dx,yy=y+dy;if(xx<0||yy<0||xx>=G||yy>=G)continue;const kk=yy*G+xx;if(net[kk]!==net[k])continue;const nv=v+w*cost(kk);if(nv<D[kk]){D[kk]=nv;push(kk,nv)}}}
  return D;
}
function manSetup(r){
  const d=r.d,G=120,h=Z/G,net=new Uint8Array(G*G),Sv=r.S;
  for(let k=0;k<G*G;k++)net[k]=d.P[k]||d.U[k];
  const seedsOf=(pts)=>{const s=[];for(const [px,py] of pts){const cx=Math.floor(px/h),cy=Math.floor(py/h);let best=0;
    for(let y=cy-5;y<=cy+5;y++)for(let x=cx-5;x<=cx+5;x++){if(x<0||y<0||x>=G||y>=G)continue;if((x+.5-px/h)**2+(y+.5-py/h)**2<=(.45/h)**2&&net[y*G+x])s.push(y*G+x)}}return s};
  const pin=d.ports.slice(0,2),pout=d.ports.slice(2);
  const dIn=manDijkstra(net,G,seedsOf(pin),()=>1),dOut=manDijkstra(net,G,seedsOf(pout),()=>1);
  const vx=new Float32Array(G*G),vy=new Float32Array(G*G),sp=[];
  for(let y=0;y<G;y++)for(let x=0;x<G;x++){const k=y*G+x;if(!net[k])continue;
    const useIn=dIn[k]<1e8&&(dIn[k]<=dOut[k]||dOut[k]>=1e8),D=useIn?dIn:dOut;if(D[k]>=1e8)continue;
    const g=(a,b)=>{const ka=b*G+a;return a>=0&&b>=0&&a<G&&b<G&&net[ka]===net[k]&&D[ka]<1e8?D[ka]:null};
    const xp=g(x+1,y),xm=g(x-1,y),yp=g(x,y+1),ym=g(x,y-1);
    let gx=(xp!=null&&xm!=null)?(xp-xm)/2:xp!=null?xp-D[k]:xm!=null?D[k]-xm:0,gy=(yp!=null&&ym!=null)?(yp-ym)/2:yp!=null?yp-D[k]:ym!=null?D[k]-ym:0;
    const s=useIn?1:-1;vx[k]=s*gx;vy[k]=s*gy;sp.push(Sv[k])}
  for(let pass=0;pass<3;pass++){const ax=vx.slice(),ay=vy.slice();
    for(let y=0;y<G;y++)for(let x=0;x<G;x++){const k=y*G+x;if(!net[k])continue;let sx=0,sy=0;
      for(let b=-1;b<=1;b++)for(let a=-1;a<=1;a++){const xx=x+a,yy=y+b;if(xx<0||yy<0||xx>=G||yy>=G)continue;const kk=yy*G+xx;if(net[kk]!==net[k])continue;sx+=ax[kk];sy+=ay[kk]}vx[k]=sx;vy[k]=sy}}
  sp.sort((a,b)=>a-b);const p95=sp.length?Math.max(sp[Math.floor(sp.length*.95)],1):1;
  const mag=new Float32Array(G*G);
  for(let k=0;k<G*G;k++){if(!net[k])continue;const L=Math.hypot(vx[k],vy[k]),m=Math.min(Sv[k]/p95,1.3)*FVD;mag[k]=m;if(L>1e-9){vx[k]=vx[k]/L*m;vy[k]=vy[k]/L*m}else{vx[k]=vy[k]=0}}
  // 채워지는 순서: 입구망은 입구에서 유속을 따라 퍼지고, 출구망은 그 뒤에 먼 곳부터 출구 쪽으로 찬다
  const tIn=manDijkstra(net,G,seedsOf(pin),k=>h/Math.max(mag[k],.15*FVD));
  let tiM=0,doM=0;for(let k=0;k<G*G;k++){if(net[k]&&tIn[k]<1e8)tiM=Math.max(tiM,tIn[k]);if(net[k]&&dOut[k]<1e8)doM=Math.max(doM,dOut[k])}
  const tau=new Float32Array(G*G);
  for(let k=0;k<G*G;k++){if(!net[k])continue;if(tIn[k]<1e8&&(dIn[k]<=dOut[k]||dOut[k]>=1e8))tau[k]=tIn[k];else if(dOut[k]<1e8)tau[k]=tiM*.5+(doM-dOut[k])*h/(FVD*.5);else tau[k]=tiM}
  let tM=0;for(let k=0;k<G*G;k++)if(net[k])tM=Math.max(tM,tau[k]);const sc=tM>0?(CL.cool-CL.w)/tM:1;
  const P=TP,c=document.createElement('canvas');c.width=P;c.height=P;
  const lut=new Uint8Array(256*3);for(let q=0;q<256;q++)lut.set(cmapRaw(q/255),q*3);
  const base=new Float32Array(P*P),mask=new Uint8Array(P*P),vel=new Float32Array(P*P),vxx=new Float32Array(P*P),tp=new Float32Array(P*P),f=P/G,s=S.Q/Q0/1000;
  for(let i=0;i<P;i++)for(let ix=0;ix<P;ix++){const k=Math.floor(i/f)*G+Math.floor(ix/f),o=i*P+ix;mask[o]=net[k]?1:0;base[o]=Sv[k]*s;vel[o]=vy[k]*.65;vxx[o]=vx[k]*.65;tp[o]=tau[k]*sc}
  FLOW.man={G,h,net,vx,vy};
  return {th:{P,h:Z/P,vel,vx:vxx,base,mask,c,x:c.getContext('2d'),im:c.getContext('2d').createImageData(P,P),lut},tp};
}
function manSpawn(p,fresh){const m=FLOW.man;for(let t=0;t<40;t++){const k=(Math.random()*m.G*m.G)|0;if(m.net[k]&&(Math.abs(m.vx[k])+Math.abs(m.vy[k])>.05||t>30)){p.x=(k%m.G+Math.random())*m.h;p.y=(((k/m.G)|0)+Math.random())*m.h;break}}p.age=fresh?Math.random()*FLIFE:0}
function manV(x,y){const m=FLOW.man,G=m.G,cx=Math.floor(x/m.h),cy=Math.floor(y/m.h);if(cx<0||cy<0||cx>=G||cy>=G)return null;const k=cy*G+cx;if(!m.net[k])return null;return [m.vx[k],m.vy[k]]}
/* ---------- 흐름선: 물길을 따라 이어진 선 위의 무늬가 흐름 방향·빠르기대로 흘러간다 ---------- */
const LN={lam:.55,duty:.5,L:2.4,vs:.5,buckets:[[.12,.22],[.4,.38],[.7,.55]]};
function buildLines(r){
  const out=[],VM=view==='vman';
  if(!VM){const f=FLOW.f,[ya,yb]=[f.ya,f.yb],st=.05;
    for(let j=0;j<N;j++){const n=Math.max(2,Math.round((yb-ya)/st)+1),x=new Float32Array(n),y=new Float32Array(n),s=new Float32Array(n),v=new Float32Array(n);
      for(let i=0;i<n;i++){const yy=ya+(yb-ya)*i/(n-1);x[i]=chX(j);y[i]=yy;s[i]=yy;v[i]=f.v(j,yy)*LN.vs}out.push({x,y,s,v})}
    return out}
  const m=FLOW.man,G=m.G,h=m.h,occ=new Uint8Array(G*G),st=.05;
  const V=(x,y)=>{const cx=Math.floor(x/h),cy=Math.floor(y/h);if(cx<0||cy<0||cx>=G||cy>=G)return null;const k=cy*G+cx;if(!m.net[k])return null;return [m.vx[k],m.vy[k],k]};
  const trace=(x,y,dir)=>{const pts=[];const net0=V(x,y);if(!net0)return pts;const n0=m.net[net0[2]];
    for(let it=0;it<500;it++){const v=V(x,y);if(!v||m.net[v[2]]!==n0)break;const L=Math.hypot(v[0],v[1]);if(L<1e-3)break;if(it>3&&occ[v[2]]===2)break;
      pts.push([x,y,L]);occ[v[2]]=Math.max(occ[v[2]],1);x+=dir*v[0]/L*st;y+=dir*v[1]/L*st}return pts};
  const seeds=[];for(let y=.3;y<Z;y+=.45)for(let x=.3;x<Z;x+=.45)seeds.push([x+(Math.random()-.5)*.15,y+(Math.random()-.5)*.15]);
  seeds.sort((a,b)=>{const va=V(...a),vb=V(...b);return (vb?Math.hypot(vb[0],vb[1]):0)-(va?Math.hypot(va[0],va[1]):0)});
  for(const [sx,sy] of seeds){const v=V(sx,sy);if(!v||occ[v[2]])continue;
    const b=trace(sx,sy,-1).reverse(),f=trace(sx,sy,1);const pts=b.concat(f.slice(1));
    for(const p of pts){const k=Math.floor(p[1]/h)*G+Math.floor(p[0]/h);if(k>=0&&k<G*G)occ[k]=2;
      // 옆 칸도 차지한 것으로 표시해 선 간격을 띄운다
      const cx=Math.floor(p[0]/h),cy=Math.floor(p[1]/h);for(let b2=-2;b2<=2;b2++)for(let a2=-2;a2<=2;a2++){const xx=cx+a2,yy=cy+b2;if(xx>=0&&yy>=0&&xx<G&&yy<G&&!occ[yy*G+xx])occ[yy*G+xx]=1}}
    if(pts.length<8)continue;
    const n=pts.length,x=new Float32Array(n),y=new Float32Array(n),s=new Float32Array(n),vv=new Float32Array(n);let acc=0;
    for(let i=0;i<n;i++){if(i)acc+=Math.hypot(pts[i][0]-pts[i-1][0],pts[i][1]-pts[i-1][1]);x[i]=pts[i][0];y[i]=pts[i][1];s[i]=acc;vv[i]=pts[i][2]*LN.vs}
    out.push({x,y,s,v:vv})}
  return out;
}
function linesMount(){
  const NS='http://www.w3.org/2000/svg',g=document.createElementNS(NS,'g');
  g.setAttribute('pointer-events','none');g.setAttribute('fill','none');g.setAttribute('stroke','#fff');g.setAttribute('stroke-linecap','round');g.setAttribute('stroke-width','.1');
  FLOW.lp=[];for(let k=0;k<6;k++){const p=document.createElementNS(NS,'path');g.appendChild(p);FLOW.lp.push(p)}
  const st=$('stage'),port=st.querySelector('circle');if(port)st.insertBefore(g,port);else st.appendChild(g);
  FLOW.lg=g;
}
function linesFrame(t){
  const Lp=LN.L,ta=t%Lp,tb=(t+Lp/2)%Lp,wa=1-Math.abs(2*ta/Lp-1),wb=1-wa,vmax=FVD*LN.vs*1.3,B=LN.buckets;
  const ds=[['','',''],['','','']];
  for(const ln of FLOW.lines){const n=ln.x.length;
    for(let layer=0;layer<2;layer++){const tau=layer?tb:ta,off=layer?.5:0;let on=-1,ob=-1,seg='';
      for(let i=0;i<n;i++){const v=ln.v[i],a=Math.abs(v)/vmax;let b=-1;if(a>=B[0][0])b=a>=B[2][0]?2:a>=B[1][0]?1:0;
        const ph=(ln.s[i]-v*tau)/LN.lam+off,vis=b>=0&&(ph-Math.floor(ph))<LN.duty;
        if(vis&&on>=0&&b===ob){seg+=`L${ln.x[i].toFixed(3)} ${(Z-ln.y[i]).toFixed(3)}`}
        else{if(on>=0&&seg)ds[layer][ob]+=seg;seg='';on=-1;if(vis){on=i;ob=b;seg=`M${ln.x[i].toFixed(3)} ${(Z-ln.y[i]).toFixed(3)}`}}}
      if(on>=0&&seg)ds[layer][ob]+=seg}}
  for(let layer=0;layer<2;layer++)for(let b=0;b<3;b++){const p=FLOW.lp[layer*3+b];p.setAttribute('d',ds[layer][b]);p.setAttribute('stroke-opacity',(B[b][1]*(layer?wb:wa)).toFixed(3))}
}
/* ---------- 조건별 순위: 온도 우선 / 균형 / 압력 우선 ---------- */
const RMODES=[['temp','열전달 성능','논문 3.1절 · 최고 온도·열저항이 낮은 순'],['bal','종합 성능 (CCPI)','논문 3.3절 · CCPI가 높은 순'],['press','수력 성능','논문 3.2절 · 압력강하가 낮은 순']];
/* 공학적 점수 (°C 환산): 압력은 한도에 가까울수록 벌점이 커지고, 한도보다 훨씬 작으면 거의 0 */
const TLIM=()=>S.Tlim??85;
/* hasHeat: 총 발열이 0 W면 열저항·CCPI·성능 순위는 정의되지 않는다(Tmax≈Tin). 유동 계산 자체는 유효할 수 있으므로 validR은 건드리지 않고, 성능 비교만 끈다 (5차 검토) */
function hasHeat(){return !!G&&Number.isFinite(G.Ptot)&&G.Ptot>1e-6}
/* 균형: Wu 등(2026) CCPI = Nu/(f·Re³)^(1/3). 같은 채널·같은 유량에서는 Nu ∝ 1/(Tmax−Tin), f·Re³ ∝ ΔP 이므로
   CCPI ∝ 1/((Tmax−Tin)·ΔP^(1/3)). 점수는 그 역수(작을수록 좋음) */
/* 여러 유량을 함께 비교할 때: f·Re³ ∝ ΔP·u ∝ ΔP·Q 이므로 Q^(1/3) 인자를 포함 (같은 유량 안에서는 상수라 순위 불변) */
function ccpiInv(r){return Math.max(r.Tmax-S.Tin,1e-6)*Math.cbrt(Math.max(r.dp,1e-6)*Math.max(r.Qml,1e-6))}
/* 절대 CCPI (Wu 등 2026 정의: Nu/(f·Re³)^(1/3), f = 2ΔP·Dh/(ρu²L) Darcy, 전체 ΔP). h는 논문들(Hu 2026 식 14, Zhang 2026 식 9–10, Drummond 2018 식 4)과 같이
   유체 접촉면 평균 벽온도 − 유체 평균 온도 기준: h = P/(A_wet·(T̄w − T̄f)), A_wet = N·2(H+w)·Lc (수력직경과 같은 4면 젖은 둘레), 물성은 유체 평균 온도.
   이전 (Tmax − Tin) 기준은 h를 크게 과소평가하는 대리값이었음(검증 계획서 식 44). 순위용 대리 점수는 ccpiInv에 따로 있음 */
function ccpiAbs(r){if(!hasHeat()||!Number.isFinite(r.Twall)||!Number.isFinite(r.Tfavg))return null;const w=WC*1e-3,hc=HC*1e-3,L=(Y1-Y0)*1e-3,Dh=2*w*hc/(w+hc),A=N*2*(hc+w)*L,wf=G&&G.fQ?G.fQ(r.Qml):water(S.Tin),
  u=r.Qml/6e7/(N*w*hc),dT=r.Twall-r.Tfavg;if(!(dT>1e-6))return null;const h=G.Ptot/(A*dT),Nu=h*Dh/wf.kf,Re=wf.rho*u*Dh/wf.mu,f=2*r.dp*Dh/(wf.rho*u*u*L);
  return Nu/Math.cbrt(f*Re*Re*Re)}
function ccpiRel(r){if(!hasHeat())return null;const b=res.find(x=>x&&x.d.ref&&x.Qml===r.Qml)||res[0];return b?ccpiInv(b)/ccpiInv(r):1}
function engScore(r,mode){return mode==='temp'?r.Tmax+1e-4*r.dp:mode==='press'?r.dp/1e3+.001*r.Tmax:ccpiInv(r)}
function rankBy(mode){
  if(!hasHeat())return [];   // 발열 0 W: 냉각 성능 순위 없음(모든 구조 Tmax≈Tin, 1e-6 하한으로 억지 점수를 만들지 않는다)
  const pool=res.filter(r=>validR(r));if(!pool.length)return [];   // 수치적으로 유효한 결과만 순위에 올린다
  return pool.map(r=>({r,s:engScore(r,mode),ok:feas(r)})).sort((a,b)=>(b.ok-a.ok)||(a.s-b.s));
}
function drawRank(){
  const el=$('rank');if(!el)return;
  if(!res.length){el.innerHTML='<p class="note">계산이 끝나면 순위가 나옵니다.</p>';return}const qn=$('rankQ');if(qn)qn.textContent=res[0].Qml;
  el.innerHTML=RMODES.map(([m,t,sub])=>{const L=rankBy(m);
    return `<div class="rk-col ${S.mode===m?'on':''}"><button type="button" class="rk-head" data-mode-pick="${m}" aria-pressed="${S.mode===m}"><h3>${t}${S.mode===m?' <span class="tag">선택한 기준</span>':''}${S.mode===m?' <span class="tag">그래프에 1~5위만</span>':''}</h3><p class="note">${sub}${S.mode===m?' · 아래 그래프는 이 기준 1~5위만':' · 누르면 이 기준으로 바꿉니다'}</p></button><ol>`+
      L.slice(0,5).map((c,i)=>{const r=c.r;return `<li><button type="button" class="rk-row ${c.ok?'':'bad'}" data-k="${r.d.k}" data-q="${r.Qml}"><span class="rk-n">${i+1}</span><span class="rk-name">${esc(r.d.name)}${r.d.ref?' <small>(기준)</small>':''}</span><span class="rk-v">${rkVal(r,m)}${c.ok?'':' · 한도 밖'}</span></button></li>`}).join('')+'</ol></div>'}).join('');
}
$('rank').addEventListener('click',e=>{const hd=e.target.closest('.rk-head');
  if(hd){const m=hd.dataset.modePick;RFILT=m;S.mode=m;document.querySelectorAll('[data-mode]').forEach(x=>x.setAttribute('aria-pressed',String(x.dataset.mode===m)));save();pickOpt();render();drawSweep();return}
  const b=e.target.closest('.rk-row');if(!b)return;const i=DESIGNS.findIndex(d=>d.k===b.dataset.k);if(i<0)return;sel=i;render();$('stage').scrollIntoView({behavior:'smooth',block:'center'})});
{const _r=render;render=function(){_r();drawRank()}}
drawRank();
/* 순위 기준을 누르면 아래 두 그래프에 그 기준의 1~5위만 그린다 (다시 누르면 전체) */
var RFILT=null;
function rankTop(){if(!res.length||!hasHeat())return null;return new Set(rankBy(S.mode).slice(0,5).map(c=>c.r.d))}
function SHOW(d){const t=rankTop();return !t||t.has(d)}
function RV(){const t=rankTop();return t?res.filter(o=>t.has(o.d)):res}
function SV(){const t=rankTop();return t?sweep.filter(l=>t.has(l.d)):sweep}

/* 논문(Wu 등 2026) 방식 지표 */
function rthOf(r){if(!G||!Number.isFinite(G.Ptot)||G.Ptot<=1e-6)return null;return (r.Tmax-G.p.Tin)/G.Ptot}   // 발열이 0이면 열저항은 정의되지 않음(null → 화면 N/A)
function pctTxt(v,b,ref){return ref?'기준':`${v<=b?'−':'+'}${Math.abs((v-b)/b*100).toFixed(1)}%`}
function rkVal(r,m){const b=res.find(x=>x&&x.d.ref)||r,ref=r.d.ref;
  if(m==='temp')return `${r.Tmax.toFixed(1)} °C (${pctTxt(r.Tmax,b.Tmax,ref)}) · Rth ${rthOf(r)==null?'N/A (발열 0 W)':rthOf(r).toFixed(3)+' K/W'}`;
  if(m==='press')return `${(r.dp/1e3).toFixed(1)} kPa (${pctTxt(r.dp,b.dp,ref)}) · ${r.Tmax.toFixed(1)} °C`;
  if(ccpiAbs(r)==null)return `CCPI N/A (발열 0 W) · ${r.Tmax.toFixed(1)} °C · ${(r.dp/1e3).toFixed(1)} kPa`;
  return `CCPI ${ccpiAbs(r).toFixed(4)} (${ref?'기준':(()=>{const v=ccpiAbs(r),c=ccpiAbs(b);return c?`${v>=c?'+':'−'}${Math.abs((v-c)/c*100).toFixed(1)}%`:'기준 없음'})()}) · ${r.Tmax.toFixed(1)} °C · ${(r.dp/1e3).toFixed(1)} kPa`}
/* 유량별 그래프 탭: 온도-압력 / Tmax / Rth / ΔP / CCPI */
var SWM='tp';
var SWMS=[['tp','온도-압력'],['tmax','Tmax'],['rth','Rth'],['dp','ΔP'],['ccpi','CCPI']];
function swTabs(){return `<div class="seg swtabs" role="group" aria-label="유량별 그래프 종류">${SWMS.map(([k,t])=>`<button type="button" data-swm="${k}" aria-pressed="${SWM===k}">${t}</button>`).join('')}</div>`}
function swVal(o,i){const k=SWM;if(k==='tmax')return o.Tmax;if(k==='rth'){const v=rthOf(o);return v==null?NaN:v}if(k==='dp')return o.dp/1e3;
  const v=ccpiAbs(o);return v==null?NaN:v}
function drawSweepM(){
  const W=860,H=320,l=60,r=24,t=12,b=38,pw=W-l-r,ph=H-t-b,rows=SV(),qs=SWQ.slice();
  const okM=(o,i)=>!!o&&Number.isFinite(o.Qml)&&Number.isFinite(swVal(o,i));   // 원 배열 인덱스로 판정 (6차 검토)
  const vs=rows.flatMap(L=>L.map((o,i)=>okM(o,i)?swVal(o,i):NaN)).filter(Number.isFinite);if(!vs.length||!qs.length){$('sweep').innerHTML='';legendHtml('swLegend');return}let mn=Math.min(...vs),mx=Math.max(...vs);if(mx-mn<1e-9){mx+=1;mn-=1}
  const span=mx-mn,st=[.0005,.001,.002,.005,.01,.02,.05,.1,.2,.5,1,2,5,10,20,50].find(s=>span/s<=6)||100,y0=Math.floor(mn/st)*st,y1=Math.ceil(mx/st)*st,dg=st<.001?4:st<.01?3:st<.1?2:st<1?1:0;
  const q0=Math.min(...qs),q1=Math.max(...qs),X=q=>l+pw*(q-q0)/Math.max(q1-q0,1),Y=v=>t+ph*(1-(v-y0)/(y1-y0));let h='';
  for(let v=y0;v<=y1+1e-9;v+=st)h+=`<line x1="${l}" x2="${W-r}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--line)"/><text class="axis" x="${l-6}" y="${Y(v)+3.5}" text-anchor="end">${v.toFixed(dg)}</text>`;
  for(const q of qs)h+=`<line x1="${X(q)}" x2="${X(q)}" y1="${t}" y2="${t+ph}" stroke="var(--line)"/><text class="axis" x="${X(q)}" y="${t+ph+13}" text-anchor="middle">${q}</text>`;
  const yl={tmax:'전체 최고 온도 Tmax, °C',rth:'열저항 Rth = (Tmax−Tin)/Q, K/W',dp:'압력강하 ΔP, kPa',ccpi:'CCPI = Nu/(f·Re³)^(1/3)'}[SWM];
  h+=`<text class="axis" x="${l+pw/2}" y="${H-5}" text-anchor="middle">입구 총 유량, ml/min</text><text class="axis" transform="translate(12 ${t+ph/2}) rotate(-90)" text-anchor="middle">${yl}</text>`;
  // 선: 무효 유량(null·NaN) 구간에서 끊어지는 path. 원 배열 인덱스 i 유지, x는 o.Qml 직접 사용
  sweep.forEach((L,k)=>{if(!L.some(okM)||!SHOW(L.d))return;const c=SER[L.d.k];
    const pd=L.map((o,i)=>okM(o,i)?`${okM(L[i-1],i-1)?'L':'M'}${X(o.Qml).toFixed(1)} ${Y(swVal(o,i)).toFixed(1)}`:null).filter(Boolean).join(' ');
    h+=`<path d="${pd}" fill="none" stroke="${c}" stroke-width="${L.d.k==='A'?3:2}" ${L.d.ref?'stroke-dasharray="6 4"':isD(L.d)?DASH:''}/>`;
    L.forEach((o,i)=>{if(!okM(o,i))return;h+=`<circle data-s="${k}" data-q="${i}" cx="${X(o.Qml).toFixed(1)}" cy="${Y(swVal(o,i)).toFixed(1)}" r="4.5" fill="${c}" fill-opacity="${o.ReMax>2300?.3:1}" stroke="var(--panel)" stroke-width="1.5" style="cursor:pointer"/>`})});
  $('sweep').innerHTML=h;legendHtml('swLegend');
}
document.addEventListener('click',e=>{const b=e.target.closest('[data-swm]');if(!b)return;SWM=b.dataset.swm;
  document.querySelectorAll('[data-swm]').forEach(x=>x.setAttribute('aria-pressed',String(x.dataset.swm===SWM)));
  if(sweep.length)drawSweep();if(typeof shMoreFill==='function'&&document.getElementById('shMore')&&document.getElementById('shMore').open)shMoreFill()});
/* ---------- 3D 보기: 선택한 구조를 3차원으로, 고체는 바닥 표면 온도 색으로 칠한다 (외부 라이브러리 없이 WebGL) ---------- */
const V3={gl:null,ok:null,r:null,man:true,th:.9,ph:.85,dist:34,tgt:[6,6,1.6],EZ:4,buf:null,lab:null};
function v3Mat(){
  const c=document.getElementById('v3c'),w=c.width,h=c.height,asp=w/h,f=1/Math.tan(30*Math.PI/180/2),n=.1,fa=200;
  const P=[f/asp,0,0,0, 0,f,0,0, 0,0,(fa+n)/(n-fa),-1, 0,0,2*fa*n/(n-fa),0];
  const D=V3.dist*Math.max(1,.95/asp);
  const ce=[V3.tgt[0]+D*Math.cos(V3.ph)*Math.cos(V3.th),V3.tgt[1]+D*Math.cos(V3.ph)*Math.sin(V3.th),V3.tgt[2]+D*Math.sin(V3.ph)];
  const sub=(a,b)=>[a[0]-b[0],a[1]-b[1],a[2]-b[2]],nrm=a=>{const l=Math.hypot(...a);return a.map(v=>v/l)},cr=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]],dt=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
  const zf=nrm(sub(ce,V3.tgt)),xf=nrm(cr([0,0,1],zf)),yf=cr(zf,xf);
  const Vw=[xf[0],yf[0],zf[0],0, xf[1],yf[1],zf[1],0, xf[2],yf[2],zf[2],0, -dt(xf,ce),-dt(yf,ce),-dt(zf,ce),1];
  const m=new Float32Array(16);for(let i=0;i<4;i++)for(let j=0;j<4;j++){let s=0;for(let k=0;k<4;k++)s+=Vw[i*4+k]*P[k*4+j];m[i*4+j]=s}return m;
}
function v3Init(){
  if(V3.ok!==null)return V3.ok;
  const c=document.getElementById('v3c');if(!c){V3.ok=false;return false}
  const gl=c.getContext('webgl',{antialias:true,premultipliedAlpha:false});
  if(!gl){V3.ok=false;document.getElementById('v3msg').textContent='이 브라우저에서는 3D 그리기(WebGL)를 쓸 수 없습니다.';return false}
  const sh=(t,s)=>{const o=gl.createShader(t);gl.shaderSource(o,s);gl.compileShader(o);return o};
  const pr=gl.createProgram();
  gl.attachShader(pr,sh(gl.VERTEX_SHADER,'attribute vec3 p;attribute vec3 n;attribute vec4 c;uniform mat4 M;uniform vec3 L;varying vec4 v;void main(){gl_Position=M*vec4(p,1.);float s=length(n)<.5?1.:.62+.38*max(dot(normalize(n),L),0.)+.12*max(dot(normalize(n),vec3(0.,0.,1.)),0.);v=vec4(min(c.rgb*s,vec3(1.)),c.a);}'));
  gl.attachShader(pr,sh(gl.FRAGMENT_SHADER,'precision mediump float;varying vec4 v;void main(){gl_FragColor=v;}'));
  gl.linkProgram(pr);gl.useProgram(pr);
  V3.gl=gl;V3.pr=pr;V3.loc={p:gl.getAttribLocation(pr,'p'),n:gl.getAttribLocation(pr,'n'),c:gl.getAttribLocation(pr,'c'),M:gl.getUniformLocation(pr,'M'),L:gl.getUniformLocation(pr,'L')};
  // 마우스·터치로 돌리기, 휠로 확대
  let dr=null;
  c.addEventListener('pointerdown',e=>{dr={x:e.clientX,y:e.clientY,th:V3.th,ph:V3.ph};c.setPointerCapture(e.pointerId)});
  c.addEventListener('pointermove',e=>{if(!dr)return;V3.th=dr.th-(e.clientX-dr.x)*.008;V3.ph=Math.max(-1.5,Math.min(1.5,dr.ph+(e.clientY-dr.y)*.008));v3Draw()});
  c.addEventListener('pointerup',()=>{dr=null});c.addEventListener('pointercancel',()=>{dr=null});
  c.addEventListener('wheel',e=>{e.preventDefault();V3.dist=Math.max(8,Math.min(60,V3.dist*(1+Math.sign(e.deltaY)*.08)));v3Draw()},{passive:false});
  new ResizeObserver(()=>v3Draw()).observe(c);
  V3.ok=true;return true;
}
function v3Build(){
  const r=res[sel];if(!r||!v3Init())return;V3.r=r;
  const d=r.d,EZ=V3.EZ,Tl=r.Tmin,Th=r.Tmax,sp=Math.max(Th-Tl,1e-6);
  const cx=[...Array(N)].map((_,j)=>chX(j));
  const Tat=(x,y)=>{const c=Math.max(0,Math.min(NX-1,y/DY-.5)),i=Math.min(NX-2,Math.floor(c)),t=c-i,F=j=>r.field[j*NX+i]*(1-t)+r.field[j*NX+i+1]*t;
    if(x<=cx[0])return F(0);if(x>=cx[N-1])return F(N-1);const j0=Math.floor((x-X0)/PITCH),u=(x-cx[j0])/PITCH;return F(j0)*(1-u)+F(j0+1)*u};
  const col=(x,y)=>{const c=cmapRaw(Math.max(0,Math.min(1,(Tat(x,y)-Tl)/sp)));return [c[0]/255,c[1]/255,c[2]/255,1]};
  const O=[],T=[],Ln=[],W=[],WK=[],WG=[],WT=[];
  const GPw=240,ghw=Z/GPw,gk=(x,y)=>Math.min(GPw-1,Math.max(0,Math.floor(y/ghw)))*GPw+Math.min(GPw-1,Math.max(0,Math.floor(x/ghw)));
  const wv=(p,n,kind,g,tau)=>{W.push(p[0],p[1],p[2]*V3.EZ,n[0],n[1],n[2],.3,.7,1,.5);WK.push(kind);WG.push(g);WT.push(tau)};
  const wq=(a,b,c,e,n,kind,ta,tb,tc,te)=>{const G=p=>gk(p[0],p[1]),t=[ta,tb,tc,te];[[a,0],[b,1],[c,2],[a,0],[c,2],[e,3]].forEach(([p,i])=>wv(p,n,kind,t[i]==null?G(p):-1,t[i]==null?0:t[i]))};
  const push=(A,p,n,c)=>A.push(p[0],p[1],p[2]*EZ,n[0],n[1],n[2],c[0],c[1],c[2],c[3]);
  const quad=(A,a,b,cc,e,n,cf)=>{const C=[a,b,cc,e].map(p=>typeof cf==='function'?cf(p[0],p[1]):cf);push(A,a,n,C[0]);push(A,b,n,C[1]);push(A,cc,n,C[2]);push(A,a,n,C[0]);push(A,cc,n,C[2]);push(A,e,n,C[3])};
  const line=(a,b,c)=>{push(Ln,a,[0,0,0],c);push(Ln,b,[0,0,0],c)};
  const STEP=.2;
  // 온도로 칠한 직육면체: y 방향(필요하면 x 방향도)으로 잘게 나눠 색이 부드럽게 바뀐다
  const tbox=(x0,x1,y0,y1,z0,z1,faces)=>{
    const ny=Math.max(1,Math.round((y1-y0)/STEP)),nx=Math.max(1,Math.round((x1-x0)/STEP));
    for(let a=0;a<nx;a++)for(let b=0;b<ny;b++){const xa=x0+(x1-x0)*a/nx,xb=x0+(x1-x0)*(a+1)/nx,ya=y0+(y1-y0)*b/ny,yb=y0+(y1-y0)*(b+1)/ny;
      if(faces.top)quad(O,[xa,ya,z1],[xb,ya,z1],[xb,yb,z1],[xa,yb,z1],[0,0,1],col);
      if(faces.bot)quad(O,[xa,yb,z0],[xb,yb,z0],[xb,ya,z0],[xa,ya,z0],[0,0,-1],col)}
    for(let b=0;b<ny;b++){const ya=y0+(y1-y0)*b/ny,yb=y0+(y1-y0)*(b+1)/ny;
      if(faces.xm)quad(O,[x0,yb,z0],[x0,ya,z0],[x0,ya,z1],[x0,yb,z1],[-1,0,0],col);
      if(faces.xp)quad(O,[x1,ya,z0],[x1,yb,z0],[x1,yb,z1],[x1,ya,z1],[1,0,0],col)}
    for(let a=0;a<nx;a++){const xa=x0+(x1-x0)*a/nx,xb=x0+(x1-x0)*(a+1)/nx;
      if(faces.ym)quad(O,[xa,y0,z0],[xb,y0,z0],[xb,y0,z1],[xa,y0,z1],[0,-1,0],col);
      if(faces.yp)quad(O,[xb,y1,z0],[xa,y1,z0],[xa,y1,z1],[xb,y1,z1],[0,1,0],col)}};
  // 바닥판
  tbox(0,Z,0,Z,0,TB,{bot:1,xm:1,xp:1,ym:1,yp:1});
  // 채널층: 핀 + 채널 양끝 막힌 부분, 채널 바닥(바닥판 윗면)
  const [ya,yb]=chY(d),z1=TB+HC,edges=[0];
  for(let j=0;j<N;j++){edges.push(cx[j]-WC/2,cx[j]+WC/2)}edges.push(Z);
  for(let k=0;k<edges.length;k+=2){const xa=edges[k],xb=edges[k+1];if(xb-xa<1e-6)continue;tbox(xa,xb,0,Z,TB,z1,{top:1,xm:1,xp:1,ym:1,yp:1})}
  for(let j=0;j<N;j++){const xa=cx[j]-WC/2,xb=cx[j]+WC/2;
    if(ya>0)tbox(xa,xb,0,ya,TB,z1,{top:1,ym:1,yp:1});if(yb<Z)tbox(xa,xb,yb,Z,TB,z1,{top:1,ym:1,yp:1});
    tbox(xa,xb,ya,yb,TB-1e-4,TB,{top:1})}
  // 채널 속 물 (반투명)
  const wc=[.35,.75,.95,.18];
  for(let j=0;j<N;j++){const xa=cx[j]-WC/2+.01,xb=cx[j]+WC/2-.01,zt=z1-.01;
    quad(T,[xa,ya,zt],[xb,ya,zt],[xb,yb,zt],[xa,yb,zt],[0,0,1],wc)}
  // 흐르는 물(채널): 0.1 mm 간격으로 나눠 물이 지나가는 무늬를 칠한다
  for(let j=0;j<N;j++){const xa=cx[j]-WC/2+.015,xb=cx[j]+WC/2-.015,zt=z1-.03;for(let y=ya;y<yb-1e-9;y+=.1){const y2=Math.min(yb,y+.1);wq([xa,y,zt],[xb,y,zt],[xb,y2,zt],[xa,y2,zt],[0,0,1],0)}}
  // 외곽선
  const LC=[.62,.6,.95,.9],box=(x0,x1,y0,y1,z0,z2,c)=>{const P=[[x0,y0],[x1,y0],[x1,y1],[x0,y1]];for(let i=0;i<4;i++){const a=P[i],b=P[(i+1)%4];line([a[0],a[1],z0],[b[0],b[1],z0],c);line([a[0],a[1],z2],[b[0],b[1],z2],c);line([a[0],a[1],z0],[a[0],a[1],z2],c)}};
  box(0,Z,0,Z,0,z1,LC);
  for(const s of S.hs){const P=[[s.x-s.lx/2,s.y-s.ly/2],[s.x+s.lx/2,s.y-s.ly/2],[s.x+s.lx/2,s.y+s.ly/2],[s.x-s.lx/2,s.y+s.ly/2]];for(let i=0;i<4;i++){const a=P[i],b=P[(i+1)%4];line([a[0],a[1],-.003],[b[0],b[1],-.003],[1,1,1,1]);const L=Math.hypot(b[0]-a[0],b[1]-a[1]),n=Math.max(2,Math.round(L/.25));for(let k=0;k<n;k+=2){const u=k/n,v=Math.min(1,(k+1)/n);line([a[0]+(b[0]-a[0])*u,a[1]+(b[1]-a[1])*u,z1+.02],[a[0]+(b[0]-a[0])*v,a[1]+(b[1]-a[1])*v,z1+.02],[1,1,1,.9])}}}
  // 매니폴드 층: 판 외곽선 + 물길(입구 청록, 출구 빨강, 섞임 공간 노랑)
  let ztop=z1;
  if(V3.man){
    const NETC={1:[.05,.3,.84,.42],2:[.85,.25,.15,.42],3:[.93,.63,.0,.42]},NETL={1:[.45,.65,1,.95],2:[1,.5,.4,.95],3:[1,.8,.3,.95]};
    const lays=[];
    if(d.layers){const t=parseFloat(S.t),up=d.layers.slice(1).reduce((a,l)=>a+l.h,0)||1,fac=(t-.2)/up;let zb=.5;
      d.layers.forEach((l,i)=>{if(l.z)zb=l.z[0];const hh=i?l.h*fac:.2,zt=l.z?l.z[1]:zb+hh;lays.push({z0:zb,z1:zt,M:l.M,net:i===0?d.P:d.U});zb=zt})}
    for(const L of lays){box(0,Z,0,Z,L.z0,L.z1,[.62,.6,.95,.5]);ztop=Math.max(ztop,L.z1);
      // 같은 물길 값이 이어진 칸을 직사각형으로 묶는다
      const G=120,h=Z/G,code=k=>L.M[k]?(L.net[k]||d.P[k]||d.U[k]||1):0,used=new Uint8Array(G*G);
      for(let y=0;y<G;y++)for(let x=0;x<G;x++){const k=y*G+x,v=code(k);if(!v||used[k])continue;let w=1;while(x+w<G&&!used[y*G+x+w]&&code(y*G+x+w)===v)w++;
        let hgt=1;out:while(y+hgt<G){for(let a=0;a<w;a++){const kk=(y+hgt)*G+x+a;if(used[kk]||code(kk)!==v)break out}hgt++}
        for(let b=0;b<hgt;b++)for(let a=0;a<w;a++)used[(y+b)*G+x+a]=1;
        const xa=x*h,xb=(x+w)*h,yy0=y*h,yy1=(y+hgt)*h,c=NETC[v]||NETC[1];
        quad(T,[xa,yy0,L.z1],[xb,yy0,L.z1],[xb,yy1,L.z1],[xa,yy1,L.z1],[0,0,1],c);quad(T,[xa,yy1,L.z0],[xb,yy1,L.z0],[xb,yy0,L.z0],[xa,yy0,L.z0],[0,0,-1],c);
        quad(T,[xa,yy0,L.z0],[xb,yy0,L.z0],[xb,yy0,L.z1],[xa,yy0,L.z1],[0,-1,0],c);quad(T,[xb,yy1,L.z0],[xa,yy1,L.z0],[xa,yy1,L.z1],[xb,yy1,L.z1],[0,1,0],c);
        quad(T,[xa,yy1,L.z0],[xa,yy0,L.z0],[xa,yy0,L.z1],[xa,yy1,L.z1],[-1,0,0],c);quad(T,[xb,yy0,L.z0],[xb,yy1,L.z0],[xb,yy1,L.z1],[xb,yy0,L.z1],[1,0,0],c)}
      // 물길 테두리 선 (칸 경계에서 값이 바뀌는 곳만)
      for(let y=0;y<=G;y++)for(let x=0;x<G;x++){const a=y<G?code(y*G+x):0,b=y>0?code((y-1)*G+x):0;if(a!==b){const v=a||b;line([x*h,y*h,L.z0],[(x+1)*h,y*h,L.z0],NETL[v]);line([x*h,y*h,L.z1],[(x+1)*h,y*h,L.z1],NETL[v])}}
      for(let x=0;x<=G;x++)for(let y=0;y<G;y++){const a=x<G?code(y*G+x):0,b=x>0?code(y*G+x-1):0;if(a!==b){const v=a||b;line([x*h,y*h,L.z0],[x*h,(y+1)*h,L.z0],NETL[v]);line([x*h,y*h,L.z1],[x*h,(y+1)*h,L.z1],NETL[v])}}}
    // 포트: 원기둥
    const pz0=lays.length?Math.max(...lays.map(l=>l.z1)):z1,pz1=pz0+.5;
    d.ports.forEach((p,i)=>{const R=d.k==='M4'?.5:.4,c=i<2?[.05,.3,.84,.5]:[.85,.25,.15,.5],lc=i<2?[.45,.65,1,1]:[1,.45,.35,1],S2=24;
      for(let k=0;k<S2;k++){const a=k/S2*2*Math.PI,b=(k+1)/S2*2*Math.PI,A=[p[0]+R*Math.cos(a),p[1]+R*Math.sin(a)],B=[p[0]+R*Math.cos(b),p[1]+R*Math.sin(b)];
        quad(T,[A[0],A[1],pz0],[B[0],B[1],pz0],[B[0],B[1],pz1],[A[0],A[1],pz1],[Math.cos(a),Math.sin(a),0],c);
        line([A[0],A[1],pz0],[B[0],B[1],pz0],lc);line([A[0],A[1],pz1],[B[0],B[1],pz1],lc)}
      line([p[0]+R,p[1],pz0],[p[0]+R,p[1],pz1],lc);line([p[0]-R,p[1],pz0],[p[0]-R,p[1],pz1],lc)});
    // 흐르는 물(매니폴드 물길 윗면, 포트 안)
    for(const L of lays){const G=120,h=Z/G;for(let y=0;y<G;y++)for(let x=0;x<G;x++){const k=y*G+x;if(!L.M[k])continue;const nt=L.net[k]||d.P[k]||d.U[k]||1,kind=nt===1?1:2,zt=L.z1+.006;
      wq([x*h,y*h,zt],[(x+1)*h,y*h,zt],[(x+1)*h,(y+1)*h,zt],[x*h,(y+1)*h,zt],[0,0,1],kind)}}
    d.ports.forEach((p,i)=>{const R=(d.k==='M4'?.5:.4)*.82,inl=i<2,S2=20,NZ=8;for(let k=0;k<S2;k++){const a=k/S2*2*Math.PI,b=(k+1)/S2*2*Math.PI;
      for(let s=0;s<NZ;s++){const za=pz0+(pz1-pz0)*s/NZ,zb=pz0+(pz1-pz0)*(s+1)/NZ,ta=inl?(pz1-za)*3:(za-pz0)*3,tb=inl?(pz1-zb)*3:(zb-pz0)*3,A=[p[0]+R*Math.cos(a),p[1]+R*Math.sin(a)],B=[p[0]+R*Math.cos(b),p[1]+R*Math.sin(b)];
        wq([A[0],A[1],za],[B[0],B[1],za],[B[0],B[1],zb],[A[0],A[1],zb],[Math.cos(a),Math.sin(a),0],inl?3:4,ta,ta,tb,tb)}}});
    // 포트 위 화살표: 입구는 아래로(들어감), 출구는 위로(나감)
    d.ports.forEach((p,i)=>{const inl=i<2,w=.42,hh=.16,gap=.24,base=pz1+.12;
      for(let c=0;c<3;c++){const zc=inl?base+gap*(2-c):base+gap*c,tip=inl?zc:zc+hh,bak=inl?zc+hh:zc,tau=inl?-1.2+c*.4:1.7+c*.4,kd=inl?5:6;
        for(const [ux,uy] of [[1,0],[0,1]]){const n=[-uy,ux,0],P=(o,z)=>[p[0]+ux*o,p[1]+uy*o,z];
          [P(-w,bak),P(0,tip),P(0,tip+(inl?.09:-.09))].forEach(q=>wv(q,n,kd,-1,tau));[P(-w,bak),P(0,tip+(inl?.09:-.09)),P(-w,bak+(inl?.09:-.09))].forEach(q=>wv(q,n,kd,-1,tau));
          [P(w,bak),P(0,tip),P(0,tip+(inl?.09:-.09))].forEach(q=>wv(q,n,kd,-1,tau));[P(w,bak),P(0,tip+(inl?.09:-.09)),P(w,bak+(inl?.09:-.09))].forEach(q=>wv(q,n,kd,-1,tau))}}});
    ztop=pz1;
  }
  const gl=V3.gl,mk=a=>{const b=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,b);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(a),a===O?gl.DYNAMIC_DRAW:gl.STATIC_DRAW);return {b,n:a.length/10}};
  if(V3.buf)for(const k in V3.buf)gl.deleteBuffer(V3.buf[k].b);
  // 움직임용: 고체 꼭짓점마다 온도 격자(240칸) 위치와 원래 색을 기억
  V3.Oarr=new Float32Array(O);const nv=V3.Oarr.length/10,GP=240,gh=Z/GP;V3.oi=new Int32Array(nv);V3.c0=new Float32Array(nv*3);
  for(let q=0;q<nv;q++){const o=q*10,x=V3.Oarr[o],y=V3.Oarr[o+1];V3.oi[q]=Math.min(GP-1,Math.max(0,Math.floor(y/gh)))*GP+Math.min(GP-1,Math.max(0,Math.floor(x/gh)));V3.c0[q*3]=V3.Oarr[o+6];V3.c0[q*3+1]=V3.Oarr[o+7];V3.c0[q*3+2]=V3.Oarr[o+8]}
  V3.Tl=Tl;V3.Th=Th;V3.zc=(TB+HC/2)*EZ;V3.animKey=null;
  V3.Warr=new Float32Array(W);V3.WK=Uint8Array.from(WK);V3.WG=Int32Array.from(WG);V3.WT=Float32Array.from(WT);V3.wtau=null;
  V3.buf={O:mk(O),T:mk(T),L:mk(Ln),W:(()=>{const b=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,b);gl.bufferData(gl.ARRAY_BUFFER,V3.Warr,gl.DYNAMIC_DRAW);return {b,n:V3.Warr.length/10}})()};V3.P={b:gl.createBuffer(),n:0};V3.tgt=[6,6,ztop*EZ/2];
  document.getElementById('v3t').textContent=`3D 보기 · ${d.name}`;
  document.getElementById('v3lo').textContent=Tl.toFixed(1)+' °C';document.getElementById('v3hi').textContent=Th.toFixed(1)+' °C';
  v3Draw();
}
function v3Draw(){
  const gl=V3.gl,c=document.getElementById('v3c');if(!gl||!V3.buf||!c)return;
  const dpr=Math.min(window.devicePixelRatio||1,2),w=Math.round(c.clientWidth*dpr),h=Math.round(c.clientHeight*dpr);if(!w||!h)return;
  if(c.width!==w||c.height!==h){c.width=w;c.height=h}
  gl.viewport(0,0,w,h);gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
  gl.uniformMatrix4fv(V3.loc.M,false,v3Mat());const Ld=[-.4,-.6,.7],l=Math.hypot(...Ld);gl.uniform3f(V3.loc.L,Ld[0]/l,Ld[1]/l,Ld[2]/l);
  const bind=B=>{gl.bindBuffer(gl.ARRAY_BUFFER,B.b);const s=40;gl.enableVertexAttribArray(V3.loc.p);gl.vertexAttribPointer(V3.loc.p,3,gl.FLOAT,false,s,0);gl.enableVertexAttribArray(V3.loc.n);gl.vertexAttribPointer(V3.loc.n,3,gl.FLOAT,false,s,12);gl.enableVertexAttribArray(V3.loc.c);gl.vertexAttribPointer(V3.loc.c,4,gl.FLOAT,false,s,24)};
  gl.enable(gl.DEPTH_TEST);gl.depthMask(true);gl.disable(gl.BLEND);gl.enable(gl.POLYGON_OFFSET_FILL);gl.polygonOffset(1,1);
  bind(V3.buf.O);gl.drawArrays(gl.TRIANGLES,0,V3.buf.O.n);gl.disable(gl.POLYGON_OFFSET_FILL);
  gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);
  bind(V3.buf.L);gl.drawArrays(gl.LINES,0,V3.buf.L.n);
  gl.depthMask(false);bind(V3.buf.T);gl.drawArrays(gl.TRIANGLES,0,V3.buf.T.n);if(V3.buf.W&&V3.buf.W.n){bind(V3.buf.W);gl.drawArrays(gl.TRIANGLES,0,V3.buf.W.n)}
  if(V3.P&&V3.P.n){gl.disable(gl.DEPTH_TEST);bind(V3.P);gl.drawArrays(V3.P.tri?gl.TRIANGLES:gl.LINES,0,V3.P.n);gl.enable(gl.DEPTH_TEST)}
  gl.depthMask(true);
}
(function(){
  const sec=document.getElementById('v3sec');if(!sec)return;
  let seen=false;
  const go=()=>{if(seen&&res.length&&V3.r!==res[sel])v3Build()};
  new IntersectionObserver(es=>{if(es.some(e=>e.isIntersecting)){seen=true;go()}}).observe(sec);
  const _r=render;render=function(){_r();go()};
  document.getElementById('v3man').onclick=e=>{V3.man=!V3.man;e.currentTarget.setAttribute('aria-pressed',String(V3.man));V3.r=null;go()};
  document.getElementById('v3reset').onclick=()=>{V3.th=.9;V3.ph=.85;V3.dist=34;v3Draw()};
})();
/* ---------- 3D 움직임: 열화상 · 식는 과정 · 입자 · 멈춤 (도면과 같은 계산을 3D 고체 색과 채널 속 입자로) ---------- */
const V3A={raf:0,last:0,lut:null,tt:null};
function v3Lut(){if(V3A.lut)return V3A.lut;const L=new Float32Array(256*3);for(let q=0;q<256;q++){const c=cmapRaw(q/255);L[q*3]=c[0]/255;L[q*3+1]=c[1]/255;L[q*3+2]=c[2]/255}return V3A.lut=L}
function v3Temps(mode,now){
  const th=FLOW.th;if(!th||!th.base)return null;const P=th.P,h=th.h,G=new Float32Array(P*P),span=V3.Th-V3.Tl;
  if(mode==='cool'){if(!FLOW.tp||!FLOW.t0)return null;const per=CL.cool+CL.hold,tt=((now-(FLOW.coolT0||now))/1000)%per;V3A.tt=tt;
    for(let k=0;k<P*P;k++){let u=(tt-FLOW.tp[k])/CL.w;u=u<0?0:u>1?1:u;u=u*u*(3-2*u);G[k]=FLOW.t0[k]+(th.base[k]-FLOW.t0[k])*u}return G}
  const t=now/1000,L=TLIFE,K=6,K2=K*2.3,ta=t%L,tb=(t+L/2)%L,wa=1-Math.abs(2*ta/L-1),wb=1-wa,pulse=.012*Math.sin(t*2*Math.PI/1.5);
  for(let i=0;i<P;i++){const y=(i+.5)*h;for(let ix=0;ix<P;ix++){const k=i*P+ix,v=th.vel[k],x=(ix+.5)*h;
    const n=wa*FNOISE(x*K,(y-v*ta)*K)+wb*FNOISE(x*K+31,(y-v*tb)*K+17),n2=wa*FNOISE(x*K2+7,(y-v*ta*1.6)*K2+3)+wb*FNOISE(x*K2+51,(y-v*tb*1.6)*K2+29),sp=Math.min(1,Math.abs(v)/(FVD*.65));
    G[k]=th.base[k]+span*(.05*n+.03*n2+(.5+sp)*pulse*n2)}}
  return G;
}
function v3Paint(G,lo,hi){
  const A=V3.Oarr,lut=v3Lut(),nv=A.length/10,sp=Math.max(hi-lo,1e-6);
  if(!G){for(let q=0;q<nv;q++){A[q*10+6]=V3.c0[q*3];A[q*10+7]=V3.c0[q*3+1];A[q*10+8]=V3.c0[q*3+2]}}
  else for(let q=0;q<nv;q++){let c=((G[V3.oi[q]]-lo)/sp*255)|0;c=c<0?0:c>255?255:c;A[q*10+6]=lut[c*3];A[q*10+7]=lut[c*3+1];A[q*10+8]=lut[c*3+2]}
  const gl=V3.gl;gl.bindBuffer(gl.ARRAY_BUFFER,V3.buf.O.b);gl.bufferSubData(gl.ARRAY_BUFFER,0,A);
}
function v3Particles(on){
  const gl=V3.gl,a=[];
  if(on&&FLOW.f&&FLOW.pts.length&&FLOW.pts[0].j!==undefined){const f=FLOW.f,z=V3.zc;
    // 굵은 띠(가로·세로 십자)로 그려 어느 각도에서도 잘 보이게: 어두운 테두리 위에 밝은 흰 줄
    const rib=(x,y0,y1,w,hz,c,a0,a1)=>{const q=(P0,P1,P2,P3)=>{for(const P of [P0,P1,P2,P0,P2,P3])a.push(P[0],P[1],P[2],0,0,0,c[0],c[1],c[2],P[3])};
      q([x-w,y0,z,a0],[x+w,y0,z,a0],[x+w*.35,y1,z,a1],[x-w*.35,y1,z,a1]);q([x,y0,z-hz,a0],[x,y0,z+hz,a0],[x,y1,z+hz*.35,a1],[x,y1,z-hz*.35,a1])};
    for(const p of FLOW.pts){const v=f.v(p.j,p.y),tail=Math.sign(v||1)*Math.max(Math.abs(v)*.3,.12),al=Math.sqrt(Math.max(0,Math.sin(Math.PI*p.age/FLIFE))),x=chX(p.j);
      rib(x,p.y,p.y-tail,.085,.34,[.04,.1,.25],.55*al,.05*al);rib(x,p.y,p.y-tail,.05,.2,[1,1,1],al,.15*al)}}
  gl.bindBuffer(gl.ARRAY_BUFFER,V3.P.b);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(a),gl.DYNAMIC_DRAW);V3.P.n=a.length/10;V3.P.tri=true;
}
function v3Note(){const ns=document.querySelectorAll('#v3anote,.v3anote');if(!ns.length)return;const n={textContent:''},m=FLOW.mode;
  n.textContent=m==='thermal'?'열화상: 고체 온도 무늬가 채널 물 흐름 방향대로 밀려갑니다. 일렁임은 보기용 효과입니다.':m==='cool'?`식는 과정(연출): 핫스팟일수록 뜨거운 상태에서 시작해 물이 먼저 닿는 곳부터 식습니다.${V3A.tt!=null?` · ${V3A.tt<CL.cool?'물 공급 후 '+V3A.tt.toFixed(1)+' s':'정상 상태'}`:''}`:m==='particle'?'입자: 흰 줄이 채널 속 물의 방향과 빠르기를 보여줍니다. 길고 빠를수록 유량이 많습니다.':'멈춤: 계산된 정상 상태 온도만 보여줍니다.';
  if(m!=='off')n.textContent+=' 파란 물은 입구에서 들어와 채널로 흐르고, 주황 물은 출구로 나갑니다. 포트 위 화살표가 들어가고(▼ 입구) 나가는(▲ 출구) 방향을 보여 주고, 색이 은은하게 밀려가는 방향이 물이 흐르는 방향입니다.';
  ns.forEach(e=>e.textContent=n.textContent);
  document.querySelectorAll('[data-v3a]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.v3a===m)))}
function v3AnimTick(now){
  V3A.raf=0;const on=typeof SH!=='undefined'&&SH.page==='det'&&SH.tab==='3d'&&V3.buf&&V3.Oarr;if(!on)return;
  const m=FLOW.mode,hiEl=document.getElementById('v3hi');
  if(now-V3A.last>=(m==='particle'?30:45)){V3A.last=now;
    if(m==='thermal'||m==='cool'){const G=v3Temps(m,now),hi=m==='cool'?Math.max(V3.Th,FLOW.tmx||V3.Th):V3.Th;v3Paint(G,V3.Tl,hi);v3Particles(false);if(hiEl)hiEl.textContent=hi.toFixed(1)+' °C'}
    else{if(V3.animKey!==m){v3Paint(null);if(hiEl)hiEl.textContent=V3.Th.toFixed(1)+' °C'}v3Particles(m==='particle')}
    v3PaintWater(now,m==='off');V3.animKey=m;v3Note();v3Draw()}
  if(m!=='off')V3A.raf=requestAnimationFrame(v3AnimTick);
}
function v3AnimStart(){if(typeof SH!=='undefined'&&!SH.open){v3DashStart();return}cancelAnimationFrame(V3A.raf);V3A.raf=0;V3A.last=0;V3A.tt=null;
  if(view!=='temp'){const vb=document.querySelector('[data-view="temp"]');if(vb)vb.click()}else if(typeof drawMaps==='function'&&res.length)drawMaps();
  V3A.raf=requestAnimationFrame(v3AnimTick)}
document.addEventListener('click',e=>{const b=e.target.closest('[data-v3a]');if(!b)return;FLOW.mode=b.dataset.v3a;FLOW.coolT0=0;if(V3D.S)V3D.S.coolT0=0;cancelAnimationFrame(FLOW.raf);FLOW.raf=0;if(typeof drawMaps==='function'&&res.length)drawMaps();v3AnimStart()});

/* 흐르는 물: 물이 도착하는 순서(채널은 슬롯에서, 매니폴드는 입구 포트에서)에 맞춰 밝은 띠가 하류로 흘러간다 */
function v3WaterTau(){
  if(V3.wtau)return true;const r=res[sel];if(!r||!FLOW.f)return false;
  try{if(!FLOW.th)FLOW.th=thermalSetup(r);if(!FLOW.tp)FLOW.tp=coolSetup(r)}catch(_){return false}
  let tm=null;if(!r.d.ref){try{tm=manSetup(r).tp}catch(_){tm=null}}
  const n=V3.WK.length,t=new Float32Array(n);
  for(let q=0;q<n;q++){const k=V3.WK[q],g=V3.WG[q];t[q]=k>=3?V3.WT[q]:k===0?FLOW.tp[g]:(tm?tm[g]:0)}
  V3.wtau=t;return true;
}
const V3W={0:[[.02,.2,.5],[.8,1,1]],1:[[.02,.12,.45],[.7,.95,1]],2:[[.35,.08,.04],[1,.85,.6]],3:[[.02,.15,.6],[.75,.97,1]],4:[[.5,.1,.03],[1,.88,.6]],5:[[.1,.35,.95],[.85,1,1]],6:[[.9,.3,.08],[1,.92,.65]]};
function v3PaintWater(now,still){
  if(!V3.buf||!V3.buf.W||!V3.Warr)return;const A=V3.Warr,n=V3.WK.length,ok=!still&&v3WaterTau(),t=now/1000,LAM=2.6,PER=4.5;
  for(let q=0;q<n;q++){const k=V3.WK[q],c=V3W[k];let b=.5;
    if(ok&&k>=3){const c2=.5+.5*Math.cos(2*Math.PI*(V3.wtau[q]*.7-t/1.6));b=c2*c2}
    else if(ok){const ph=V3.wtau[q]/LAM-t/PER,g=V3.WG[q];b=.5+.32*Math.cos(2*Math.PI*ph)+.1*Math.sin((g%240)*.05+(g/240|0)*.03+t*.9)+.08*Math.sin((g/240|0)*.06-(g%240)*.02-t*.6)}
    const o=q*10;A[o+6]=c[0][0]+(c[1][0]-c[0][0])*b;A[o+7]=c[0][1]+(c[1][1]-c[0][1])*b;A[o+8]=c[0][2]+(c[1][2]-c[0][2])*b;A[o+9]=k>=5?(still?.9:.3+.7*b):k>=3?(still?.6:.35+.6*b):still?.45:.3+.3*b}
  const gl=V3.gl;gl.bindBuffer(gl.ARRAY_BUFFER,V3.buf.W.b);gl.bufferSubData(gl.ARRAY_BUFFER,0,A);
}

/* ---------- 컴퓨터 대시보드 3D에도 열화상 · 식는 과정 · 입자 · 멈춤 (2D 도면 상태와 따로 계산) ---------- */
const V3D={key:null,S:null,raf:0,last:0,lt:0,vis:true};
function v3DashOn(){return (typeof SH==='undefined'||!SH.open)&&V3.buf&&V3.Oarr&&V3D.vis&&res.length}
function v3DashState(){const r=res[sel];if(!r)return null;
  const key=r.d.k+'|'+r.tm+'|'+(r.d.note||'')+'|'+r.Qml+'|'+S.q0+'|'+S.Tin+'|'+S.ks+'|'+JSON.stringify(S.hs);
  if(V3D.key===key)return V3D.S;
  const sv={f:FLOW.f,th:FLOW.th,tp:FLOW.tp,t0:FLOW.t0,tmx:FLOW.tmx},vw=view;let st=null;
  try{view='temp';FLOW.f=flowField(r);FLOW.th=null;const th=thermalSetup(r);FLOW.th=th;const tp=coolSetup(r);
    st={f:FLOW.f,th,tp,t0:FLOW.t0,tmx:FLOW.tmx,pts:[],coolT0:0};
    for(let j=0;j<N;j++)for(let k=0;k<FPER;k++){const p={j};flowSpawn(p,true);st.pts.push(p)}}
  catch(_){st=null}
  finally{view=vw;Object.assign(FLOW,sv)}
  V3D.key=key;V3D.S=st;return st}
function v3DashTick(now){
  V3D.raf=0;if(!v3DashOn())return;const m=FLOW.mode,st=v3DashState(),hiEl=document.getElementById('v3hi');
  if(now-V3D.last>=(m==='particle'?30:45)){const dt=Math.min(.05,(now-(V3D.lt||now))/1000);V3D.lt=now;V3D.last=now;
    const sv={f:FLOW.f,th:FLOW.th,tp:FLOW.tp,t0:FLOW.t0,tmx:FLOW.tmx,pts:FLOW.pts,coolT0:FLOW.coolT0};
    try{if(st){Object.assign(FLOW,{f:st.f,th:st.th,tp:st.tp,t0:st.t0,tmx:st.tmx,pts:st.pts,coolT0:st.coolT0||(st.coolT0=now)})}
      if(st&&(m==='thermal'||m==='cool')){const G=v3Temps(m,now),hi=m==='cool'?Math.max(V3.Th,FLOW.tmx||V3.Th):V3.Th;v3Paint(G,V3.Tl,hi);v3Particles(false);if(hiEl)hiEl.textContent=hi.toFixed(1)+' °C'}
      else{if(V3D.key2!==m+V3.Oarr.length){v3Paint(null);if(hiEl)hiEl.textContent=V3.Th.toFixed(1)+' °C'}
        if(st&&m==='particle'){const f=st.f;for(const p of st.pts){p.y+=f.v(p.j,p.y)*dt;p.age+=dt;if(p.age>=FLIFE||p.y<f.ya||p.y>f.yb)flowSpawn(p,false)}}
        v3Particles(!!st&&m==='particle')}
      v3PaintWater(now,m==='off'||!st);V3D.key2=m+V3.Oarr.length}
    finally{Object.assign(FLOW,sv)}
    v3Note();v3Draw()}
  if(m!=='off')V3D.raf=requestAnimationFrame(v3DashTick)}
function v3DashStart(){cancelAnimationFrame(V3D.raf);V3D.raf=0;V3D.last=0;V3D.lt=0;V3D.key2=null;V3D.raf=requestAnimationFrame(v3DashTick)}
{const _b=v3Build;v3Build=function(){_b.apply(this,arguments);if(typeof SH==='undefined'||!SH.open)v3DashStart()}}
(function(){const sec=document.getElementById('v3sec');if(!sec)return;
  new IntersectionObserver(es=>{const v=es.some(e=>e.isIntersecting);if(v&&!V3D.vis){V3D.vis=true;v3DashStart()}else V3D.vis=v}).observe(sec);
  document.addEventListener('click',e=>{if(e.target.closest('[data-flow]'))setTimeout(()=>{if(typeof SH==='undefined'||!SH.open)v3DashStart()})});
  /* 자세히 보기 3D: 매니폴드 넣고 빼기 */
  const mb=document.getElementById('v3manDet');
  if(mb){const sync=()=>mb.setAttribute('aria-pressed',String(V3.man!==false));sync();
    mb.addEventListener('click',()=>{document.getElementById('v3man').click();sync();if(typeof SH!=='undefined'&&SH.page==='det'&&SH.tab==='3d')requestAnimationFrame(()=>{if(V3.r!==res[sel])v3Build();v3AnimStart()})});
    document.getElementById('v3man').addEventListener('click',sync)}
})();
/* ---------- 모바일 시작 화면: 첫 화면 → 사용법 → 변수 입력 → 결과(기존 화면) ---------- */
var SH={open:true,busy:true,page:'land',drag:null};
const shEl=id=>document.getElementById(id);
const SHSTEP={1:['핫스팟','칩 그림을 눌러 뜨거운 곳을 놓아 주세요.'],2:['운전 조건','물 유량과 온도, 재질을 고릅니다. 잘 모르면 그대로 두세요.'],3:['최적 기준','무엇을 가장 중요하게 볼지 고르면 그 기준으로 순위를 매깁니다.']};
function shShow(page){
  const prev=SH.page;
  if(prev==='det'&&page!=='det')shDetLeave();
  let sec=page;if(/^in[123]$/.test(page)){SH.step=+page[2];sec='input'}
  SH.page=page;SH.open=page!=='dash';
  document.body.classList.toggle('shell-open',SH.open);shEl('shell').hidden=!SH.open;
  for(const p of ['land','guide','input','res','det'])shEl('sh-'+p).hidden=p!==sec;
  if(sec==='input'){for(const k of [1,2,3])shEl('shPane'+k).hidden=k!==SH.step;shEl('shStepT').textContent=SHSTEP[SH.step][0];shEl('shStepS').textContent=SHSTEP[SH.step][1];
    document.querySelectorAll('.sh-prog button').forEach((b,i)=>{b.classList.toggle('on',i+1===SH.step);b.classList.toggle('done',i+1<SH.step)});
    shEl('shNext').textContent=SH.step<3?'다음':'결과 보기';shEl('shInReset').hidden=SH.step!==1}
  if(page==='res'&&prev!=='det')SH.pick=null;
  if(page==='det')shDetEnter();
  if(SH.open){if(prev!==page)shEl('shell').scrollTop=0;shUpdate()}
  else{window.scrollTo(0,0);if(typeof drawMaps==='function'&&res.length){drawMaps();if(typeof drawSweep==='function')drawSweep()}}
}
function shRoute(){let h=(location.hash||'').slice(1);if(h==='input')h='in1';shShow(['dash','guide','in1','in2','in3','res','det'].includes(h)?h:'land')}
window.addEventListener('hashchange',shRoute);
document.addEventListener('click',e=>{const b=e.target.closest('[data-go]');if(!b)return;e.preventDefault();const g=b.dataset.go;location.hash=g==='land'?'start':g});
/* 색: 파랑 → 흰색 → 빨강 (첫 화면 그림용) */
function shCool(t){t=Math.max(0,Math.min(1,t));const A=[30,79,216],W=[246,248,252],R=[215,38,61];const m=(a,b,u)=>a.map((v,i)=>Math.round(v+(b[i]-v)*u));return t<.5?m(A,W,t/.5):m(W,R,(t-.5)/.5)}
function shChipImg(r){
  const P=120,c=document.createElement('canvas');c.width=P;c.height=P;const x=c.getContext('2d'),im=x.createImageData(P,P),lo=r.Tmin,sp=Math.max(r.Tmax-r.Tmin,1e-6);
  for(let py=0;py<P;py++)for(let ix=0;ix<P;ix++){const j=stripAt((ix+.5)*DY),i=P-1-py,col=shCool((r.field[j*NX+i]-lo)/sp),o=(py*P+ix)*4;im.data[o]=col[0];im.data[o+1]=col[1];im.data[o+2]=col[2];im.data[o+3]=255}
  x.putImageData(im,0,0);return c.toDataURL();
}
function shManImg(d){
  const P=240,c=document.createElement('canvas');c.width=P;c.height=P;const x=c.getContext('2d'),im=x.createImageData(P,P);
  for(let py=0;py<P;py++)for(let ix=0;ix<P;ix++){const k=(119-(py>>1))*120+(ix>>1),v=d.P[k]||d.U[k],col=v===1?[26,71,200]:v===2?[110,160,240]:v===3?[150,185,245]:[255,255,255],o=(py*P+ix)*4;im.data[o]=col[0];im.data[o+1]=col[1];im.data[o+2]=col[2];im.data[o+3]=255}
  x.putImageData(im,0,0);return c.toDataURL();
}
function shIllus(){
  const a=res.find(r=>r.d.k==='A');if(!a)return '';
  const s=15,cx=192;
  const T=y0=>`transform="matrix(${(.866*s).toFixed(3)} ${(.5*s).toFixed(3)} ${(-.866*s).toFixed(3)} ${(.5*s).toFixed(3)} ${cx} ${y0})"`;
  const edge=`<rect x="0" y="0" width="12" height="12" fill="none" stroke="#0A1F5C" stroke-width=".07"/>`;
  const L=[34,150,266];
  let h=`<svg viewBox="0 0 420 ${L[2]+200}" class="sh-svg" role="img" aria-label="매니폴드, 마이크로채널, 칩 표면 온도를 층별로 펼친 그림">`;
  // 칩 표면 온도
  h+=`<g ${T(L[2])}><image href="${shChipImg(a)}" x="0" y="0" width="12" height="12" preserveAspectRatio="none" style="image-rendering:auto"/>`;
  for(const s2 of S.hs)h+=`<rect x="${s2.x-s2.lx/2}" y="${12-s2.y-s2.ly/2}" width="${s2.lx}" height="${s2.ly}" fill="none" stroke="#0A1F5C" stroke-width=".08"/>`;
  h+=edge+`</g>`;
  // 마이크로채널
  h+=`<g ${T(L[1])}><rect x="0" y="0" width="12" height="12" fill="#DCE7FA" fill-opacity=".96"/>`;
  const [ya,yb]=chY(a.d);for(let j=0;j<N;j++)h+=`<rect x="${chX(j)-WC/2}" y="${12-yb}" width="${WC}" height="${yb-ya}" fill="#fff"/>`;
  h+=edge+`</g>`;
  // 매니폴드
  h+=`<g ${T(L[0])}><image href="${shManImg(a.d)}" x="0" y="0" width="12" height="12" preserveAspectRatio="none"/>`;
  a.d.ports.forEach((p,i)=>{h+=`<circle cx="${p[0]}" cy="${12-p[1]}" r=".42" fill="${i<2?'#0A1F5C':'#fff'}" stroke="#0A1F5C" stroke-width=".07"/>`});
  h+=edge+`</g>`;
  const lab=(y,t,s2)=>`<text x="412" y="${y}" text-anchor="end" class="sh-lt">${t}</text><text x="412" y="${y+20}" text-anchor="end" class="sh-ls">${s2}</text>`;
  h+=lab(L[0]+28,'매니폴드','핫스팟에 맞춰 자동 생성')+lab(L[1]+48,'마이크로채널',`${N}개, 폭 ${WC} mm`)+lab(L[2]+150,'칩 표면 온도','');
  h+=`<defs><linearGradient id="shg" x1="0" x2="1"><stop offset="0" stop-color="rgb(30,79,216)"/><stop offset=".5" stop-color="rgb(246,248,252)"/><stop offset="1" stop-color="rgb(215,38,61)"/></linearGradient></defs>`;
  h+=`<rect x="292" y="${L[2]+160}" width="120" height="10" fill="url(#shg)" stroke="#0A1F5C" stroke-width=".6"/><text x="292" y="${L[2]+188}" class="sh-ls">${a.Tmin.toFixed(0)} °C</text><text x="412" y="${L[2]+188}" text-anchor="end" class="sh-ls">${a.Tmax.toFixed(0)} °C</text>`;
  return h+`</svg>`;
}
let shLastIll=null;
function shUpdate(){
  if(!SH.open||!res.length)return;
  const a=res.find(r=>r.d.k==='A'),m=res.find(r=>r.d.ref);
  const t0=m?m.Tmax.toFixed(1)+' °C':'…',t1=a?a.Tmax.toFixed(1)+' °C':'…';
  for(const id of ['shP0'])if(shEl(id))shEl(id).textContent=t0;
  for(const id of ['shP1'])if(shEl(id))shEl(id).textContent=SH.busy?'계산 중…':t1;
  if(/^in/.test(SH.page))shDrawInput();
  if(SH.page==='in3')shCrit();
  if(SH.page==='res')shRes();
  if(SH.page==='det')shDetHead();
}
/* ---------- 변수 입력 ---------- */
function shSync(){
  $('Tin').value=S.Tin;$('q0').value=S.q0;$('ks').value=S.ks;setQ(S.Q);renderHs();save();schedule();
}
function shMap(){
  const [ya,yb]=[CHIP.y0,CHIP.y1];let h=`<rect x="0" y="0" width="12" height="12" rx=".25" fill="#E8EFFC" stroke="#0A1F5C" stroke-width=".06"/>`;
  // 축: 아래 x(가로), 왼쪽 y(세로), 2 mm 눈금
  for(let v=0;v<=12;v+=2){h+=`<line x1="${v}" x2="${v}" y1="12" y2="12.22" stroke="#5B6A86" stroke-width=".04"/><text x="${v}" y="12.62" text-anchor="middle" font-size=".38" fill="#5B6A86">${v}</text>`;
    h+=`<line x1="-.22" x2="0" y1="${12-v}" y2="${12-v}" stroke="#5B6A86" stroke-width=".04"/><text x="-.32" y="${12-v+.13}" text-anchor="end" font-size=".38" fill="#5B6A86">${v}</text>`}
  h+=`<text x="12" y="13.2" text-anchor="end" font-size=".42" font-weight="700" fill="#0A1F5C">x (가로, mm) →</text>`;
  h+=`<text transform="translate(-.98 6) rotate(-90)" text-anchor="middle" font-size=".42" font-weight="700" fill="#0A1F5C">y (세로, mm) →</text>`;
  for(let j=0;j<N;j++)h+=`<rect x="${chX(j)-WC/2}" y="${12-yb}" width="${WC}" height="${yb-ya}" fill="#fff"/>`;
  h+=`<rect x="${CHIP.x0}" y="${12-CHIP.y1}" width="${CHIP.x1-CHIP.x0}" height="${CHIP.y1-CHIP.y0}" fill="none" stroke="#5B6A86" stroke-width=".05" stroke-dasharray=".25 .18"/>`;
  S.hs.forEach((s,i)=>{h+=`<g class="sh-hs${SH.xi===i?' showx':''}" data-hi="${i}"><rect x="${s.x-s.lx/2}" y="${12-s.y-s.ly/2}" width="${s.lx}" height="${s.ly}" rx=".12" fill="#D7263D" fill-opacity=".85" stroke="#fff" stroke-width=".08"/>${(()=>{const big=s.lx>=2.2,fs=Math.min(.7,s.lx*.38),cy=12-s.y,ty=big?cy+.62:cy+s.ly/2+.42,c=big?'#fff':'#0A1F5C';
  return `<text x="${s.x}" y="${big?cy+.05:cy+fs*.35}" text-anchor="middle" font-size="${fs}" font-weight="700" fill="#fff" pointer-events="none">H${i+1}</text><text x="${s.x}" y="${ty}" text-anchor="middle" font-size=".38" font-weight="600" fill="${c}" ${big?'':'stroke="#fff" stroke-width=".1" paint-order="stroke"'} pointer-events="none">(${s.x.toFixed(1)}, ${s.y.toFixed(1)})</text>`})()}<g class="sh-del" data-hx="${i}" role="button" aria-label="H${i+1} 지우기"><circle cx="${s.x+s.lx/2}" cy="${12-s.y-s.ly/2}" r=".36" fill="#0A1F5C" stroke="#fff" stroke-width=".06"/><path d="M${s.x+s.lx/2-.14} ${12-s.y-s.ly/2-.14}l.28 .28m0 -.28l-.28 .28" stroke="#fff" stroke-width=".07" stroke-linecap="round"/></g></g>`});
  return h;
}
/* 입력 한도: 유량은 팀 한도(250 ml/min)와 레이놀즈 수 한도 중 낮은 값까지 */
function shLim(k,i){const s=S.hs[i];return ({Q:[30,qcap,0],Tin:[5,60,1],q0:[0,200,0],q:[50,1000,0],sz:[.5,4,1],
  x:s?[+(CHIP.x0+s.lx/2).toFixed(1),+(CHIP.x1-s.lx/2).toFixed(1),1]:[0,12,1],y:s?[+(CHIP.y0+s.ly/2).toFixed(1),+(CHIP.y1-s.ly/2).toFixed(1),1]:[0,12,1]})[k]}
const shNum=(k,v,i,lab,w)=>{const L=shLim(k,i);return `<input class="sh-num${w?' w':''}" type="number" inputmode="decimal" data-f="${k}" ${i!=null?`data-i="${i}"`:''} min="${L[0]}" max="${L[1]}" step="${L[2]?Math.pow(10,-L[2]):1}" value="${v}" aria-label="${lab} (${L[0]}~${L[1]})">`};
function shDrawInput(){
  const ae=document.activeElement,keep=ae&&ae.classList&&ae.classList.contains('sh-num')&&shEl('shHsList').contains(ae)?{f:ae.dataset.f,i:ae.dataset.i,v:ae.value}:null;
  shEl('shMap').innerHTML=shMap();
  shEl('shHsList').innerHTML=S.hs.map((s,i)=>`<div class="sh-row"><span class="sh-tag">H${i+1}</span><div class="sh-rowb sh-2c"><div>
    <div class="sh-ctl" style="margin-top:0"><span class="sh-cl">크기 <em>mm · 0.5~4</em></span><div class="sh-step"><button type="button" data-hsd="${i}" data-d="-0.5" aria-label="H${i+1} 크기 줄이기">−</button>${shNum('sz',s.lx,i,`H${i+1} 크기 mm`)}<button type="button" data-hsd="${i}" data-d="0.5" aria-label="H${i+1} 크기 늘리기">+</button></div></div>
    <div class="sh-ctl"><span class="sh-cl">열유속 <em>W/cm² · 50~1000</em></span><div class="sh-step"><button type="button" data-hq="${i}" data-d="-50" aria-label="H${i+1} 열유속 줄이기">−</button>${shNum('q',s.q,i,`H${i+1} 열유속 W/cm²`)}<button type="button" data-hq="${i}" data-d="50" aria-label="H${i+1} 열유속 늘리기">+</button></div></div></div>
    <div class="sh-pos2"><span class="sh-cl">위치 <em>mm</em></span><label><span>x</span>${shNum('x',s.x,i,`H${i+1} 위치 x mm`)}</label><label><span>y</span>${shNum('y',s.y,i,`H${i+1} 위치 y mm`)}</label></div></div>
    <button type="button" class="sh-x" data-hdel="${i}" aria-label="H${i+1} 지우기">✕</button></div>`).join('')||'<p class="sh-empty">지도를 눌러 핫스팟을 놓아 주세요.</p>';
  if(keep){const n=shEl('shHsList').querySelector(`[data-f="${keep.f}"][data-i="${keep.i}"]`);if(n){n.value=keep.v;n.focus()}}
  shEl('shAddNote').textContent='빈 곳을 누르면 추가, 끌면 이동, 두 번 누르면 오른쪽 위에 나오는 ✕로 삭제됩니다. 숫자 칸에 직접 입력해도 됩니다.';
  const setv=(id,v)=>{const e=shEl(id);if(e!==document.activeElement)e.value=v};
  setv('shQv',S.Q);shEl('shQv').max=qcap;shEl('shQlim').textContent=`30~${qcap}`;
  document.querySelectorAll('[data-shq]').forEach(b=>b.setAttribute('aria-pressed',String(+b.dataset.shq===S.Q)));
  setv('shTin',S.Tin);setv('shQ0',S.q0);
  document.querySelectorAll('[data-shks]').forEach(b=>b.setAttribute('aria-pressed',String(+b.dataset.shks===+S.ks)));
}
function shToast(t,undo){const e=shEl('shToast');e.textContent=t;if(undo){const b=document.createElement('button');b.type='button';b.textContent='되돌리기';b.className='sh-undo';b.onclick=()=>{e.hidden=true;undo()};e.append(' ',b)}
  e.hidden=false;clearTimeout(SH.tt);SH.tt=setTimeout(()=>{e.hidden=true},undo?4500:2600)}
function shDelHs(i){const h=S.hs.splice(i,1)[0];if(!h)return;SH.xi=null;selHs=0;shDrawInput();shSync();try{navigator.vibrate&&navigator.vibrate(25)}catch(_){}
  shToast(`H${i+1} 핫스팟을 지웠습니다.`,()=>{S.hs.splice(Math.min(i,S.hs.length),0,h);shDrawInput();shSync()})}
(function(){
  const map=shEl('shMap'),pt=e=>{const q=map.createSVGPoint();q.x=e.clientX;q.y=e.clientY;const m=q.matrixTransform(map.getScreenCTM().inverse());return {x:m.x,y:12-m.y}};
  const clampHs=s=>{s.x=+Math.max(CHIP.x0+s.lx/2,Math.min(CHIP.x1-s.lx/2,s.x)).toFixed(1);s.y=+Math.max(CHIP.y0+s.ly/2,Math.min(CHIP.y1-s.ly/2,s.y)).toFixed(1)};
  map.addEventListener('contextmenu',e=>e.preventDefault());
  map.addEventListener('pointerdown',e=>{const del=e.target.closest('.sh-del');if(del){e.preventDefault();e.stopPropagation();shDelHs(+del.dataset.hx);return}
    const g=e.target.closest('.sh-hs'),p=pt(e);
    if(g){const i=+g.dataset.hi,s=S.hs[i];SH.drag={i,dx:p.x-s.x,dy:p.y-s.y,moved:false,p0:p};map.setPointerCapture(e.pointerId);e.preventDefault();
      const now=Date.now();if(SH.tap&&SH.tap.i===i&&now-SH.tap.t<400){SH.xi=SH.xi===i?null:i;SH.tap=null}else SH.tap={i,t:now};return}
    SH.xi=null;const s={x:p.x,y:p.y,lx:2,ly:2,q:300};clampHs(s);S.hs.push(s);selHs=S.hs.length-1;shDrawInput();shSync()});
  map.addEventListener('pointermove',e=>{if(!SH.drag)return;const p=pt(e),s=S.hs[SH.drag.i];if(!SH.drag.moved&&Math.hypot(p.x-SH.drag.p0.x,p.y-SH.drag.p0.y)<.2)return;clearTimeout(SH.lp);s.x=p.x-SH.drag.dx;s.y=p.y-SH.drag.dy;clampHs(s);SH.drag.moved=true;shEl('shMap').innerHTML=shMap();
    const ix=shEl('shHsList').querySelector(`[data-f=x][data-i="${SH.drag.i}"]`),iy=shEl('shHsList').querySelector(`[data-f=y][data-i="${SH.drag.i}"]`);if(ix)ix.value=s.x;if(iy)iy.value=s.y});
  const end=()=>{clearTimeout(SH.lp);if(SH.drag){const m=SH.drag.moved;SH.drag=null;if(m){shDrawInput();shSync()}else shEl('shMap').innerHTML=shMap()}};
  map.addEventListener('pointerup',end);map.addEventListener('pointercancel',end);
  shEl('sh-input').addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;const D=b.dataset;
    if(D.hsd!==undefined){const s=S.hs[+D.hsd];s.lx=s.ly=Math.max(.5,Math.min(4,+(s.lx+(+D.d)).toFixed(1)));clampHs(s)}
    else if(D.hq!==undefined){const s=S.hs[+D.hq];s.q=Math.max(50,Math.min(1000,s.q+(+D.d)))}
    else if(D.hdel!==undefined){S.hs.splice(+D.hdel,1);selHs=0}
    else if(D.hreset!==undefined){shClearHs();return}
    else if(D.shq!==undefined){S.Q=+D.shq}
    else if(D.tin!==undefined){S.Tin=Math.max(5,Math.min(60,S.Tin+(+D.tin)))}
    else if(D.q0d!==undefined){S.q0=Math.max(0,Math.min(200,S.q0+(+D.q0d)))}
    else if(D.shks!==undefined){S.ks=+D.shks}
    else return;
    shDrawInput();shSync()});
  shEl('sh-input').addEventListener('change',e=>{const t=e.target;if(!t.classList||!t.classList.contains('sh-num'))return;
    const k=t.dataset.f,i=t.dataset.i!=null?+t.dataset.i:null,L=shLim(k,i);let v=parseFloat(t.value);
    const name={Q:'물 유량',Tin:'물 온도',q0:'바닥 열유속',q:'열유속',sz:'크기',x:'위치 x',y:'위치 y'}[k];
    if(!isFinite(v)){shToast(`${name}에 숫자를 입력해 주세요.`);shDrawInput();return}
    const r=+v.toFixed(L[2]),c=Math.max(L[0],Math.min(L[1],r));if(c!==r)shToast(`${name}: ${L[0]}~${L[1]} 사이만 넣을 수 있어서 ${c}(으)로 맞췄습니다.`);v=c;
    if(k==='Q')S.Q=v;else if(k==='Tin')S.Tin=v;else if(k==='q0')S.q0=v;
    else{const s=S.hs[i];if(k==='q')s.q=v;else if(k==='sz'){s.lx=s.ly=v;clampHs(s)}else s[k]=v}
    shDrawInput();shSync()});
  shEl('sh-input').addEventListener('keydown',e=>{if(e.key==='Enter'&&e.target.classList&&e.target.classList.contains('sh-num'))e.target.blur()});
})();
{const _s=schedule;schedule=function(){SH.busy=true;_s();shUpdate()}}
{const _r=render;render=function(){_r();shUpdate()}}
{const _d=drawSweep;drawSweep=function(){_d();if(SH.busy){SH.busy=false;shUpdate()}}}

/* ---------- 단계 이동 ---------- */
shEl('shNext').onclick=()=>{location.hash=SH.step<3?'in'+(SH.step+1):'res'};
shEl('shBack').onclick=()=>{location.hash=SH.step>1?'in'+(SH.step-1):'guide'};
/* ---------- 최적 기준 ---------- */
function shCrit(){
  document.querySelectorAll('[data-crit]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.crit===S.mode)));
  document.querySelectorAll('[data-top]').forEach(e=>{const L=res.length?rankBy(e.dataset.top):[];e.textContent=!hasHeat()?'발열 0 W — 순위 없음':SH.busy||!L.length?'1위 계산 중…':`지금 조건 1위 · ${L[0].r.d.name} ${L[0].r.Tmax.toFixed(1)} °C · ${(L[0].r.dp/1e3).toFixed(1)} kPa`})
}
shEl('shCrit').addEventListener('click',e=>{const b=e.target.closest('[data-crit]');if(!b)return;S.mode=b.dataset.crit;
  document.querySelectorAll('[data-mode]').forEach(x=>x.setAttribute('aria-pressed',String(x.dataset.mode===S.mode)));save();if(res.length){pickOpt();render()}shCrit()});
/* ---------- 결과 카드 ---------- */
const SHCRIT={temp:'온도 우선',bal:'균형',press:'압력 우선'};
function shTile(r,lo,hi,big){
  const P=120,c=document.createElement('canvas');c.width=P;c.height=P;const x=c.getContext('2d'),im=x.createImageData(P,P),sp=Math.max(hi-lo,1e-6);
  for(let py=0;py<P;py++)for(let ix=0;ix<P;ix++){const j=stripAt((ix+.5)*DY),i=P-1-py,col=cmap((r.field[j*NX+i]-lo)/sp),o=(py*P+ix)*4;im.data[o]=col[0];im.data[o+1]=col[1];im.data[o+2]=col[2];im.data[o+3]=255}
  x.putImageData(im,0,0);
  let h=`<svg viewBox="0 0 12 12" class="sh-tsvg" aria-hidden="true"><image href="${c.toDataURL()}" x="0" y="0" width="12" height="12" preserveAspectRatio="none" style="image-rendering:pixelated"/>`;
  h+=`<rect x="${CHIP.x0}" y="${12-CHIP.y1}" width="${CHIP.x1-CHIP.x0}" height="${CHIP.y1-CHIP.y0}" fill="none" stroke="#0B1A22" stroke-width=".06" stroke-dasharray=".3 .2"/>`;
  for(const s2 of S.hs)h+=`<rect x="${s2.x-s2.lx/2}" y="${12-s2.y-s2.ly/2}" width="${s2.lx}" height="${s2.ly}" fill="none" stroke="#fff" stroke-width=".09"/>`;
  r.d.ports.forEach((p,i)=>{h+=`<circle cx="${p[0]}" cy="${12-p[1]}" r="${big?.4:.5}" fill="${i<2?'#0B4BD6':'#C2361C'}" stroke="#fff" stroke-width=".07"/>`});
  return h+'</svg>';
}
function shRes(){
  if(!res.length)return;
  const L=rankBy(S.mode).slice(0,5),m=res.find(r=>r.d.ref);if(!L.length){shEl('shResBusy').hidden=true;shEl('shResSub').textContent=hasHeat()?'유효한 결과가 없어 순위를 매길 수 없습니다.':'총 발열이 0 W라 냉각 성능 순위를 매길 수 없습니다. 발열 조건을 확인하세요.';return}
  if(!SH.pick||!L.some(c=>c.r.d===SH.pick))SH.pick=L[0].r.d;
  const c=L.find(c=>c.r.d===SH.pick),r=c.r,rk=L.indexOf(c)+1,lo=Math.min(...res.map(o=>o.Tmin)),hi=Math.max(...res.map(o=>o.Tmax));
  shEl('shResBusy').hidden=!SH.busy;
  shEl('shResSub').textContent=`${SHCRIT[S.mode]} 기준 · 유량 ${S.Q} ml/min · 핫스팟 ${S.hs.length}개`;
  const dT=m?r.Tmax-m.Tmax:0;
  shEl('shTop').innerHTML=`<div class="sh-tw">${shTile(r,lo,hi,true)}<span class="sh-rk">${rk}위</span></div>
    <div class="sh-tb"><b class="sh-tn">${esc(r.d.name)}</b><small>${esc(r.d.note||'')}</small>
    <div class="sh-kv"><div><span>칩 최고 온도</span><b>${r.Tmax.toFixed(1)} °C</b></div><div><span>매니폴드 없음 대비</span><b class="${dT<0?'good':'bad'}">${r.d.ref?'기준':(dT>0?'+':'')+dT.toFixed(1)+' °C'}</b></div><div><span>압력강하</span><b>${(r.dp/1e3).toFixed(1)} kPa</b></div></div>
    ${c.ok?'':'<p class="sh-warn">한도(압력강하·레이놀즈 수·최고 온도)를 넘는 조건입니다.</p>'}</div>`;
  shEl('shRail').innerHTML=L.map((c2,i)=>`<button type="button" class="sh-card2 ${c2.r.d===SH.pick?'on':''}" data-pick="${c2.r.d.k}"><div class="sh-tw sm">${shTile(c2.r,lo,hi,false)}<span class="sh-rk">${i+1}</span></div><b>${esc(c2.r.d.name)}</b><span>${c2.r.Tmax.toFixed(1)} °C · ${(c2.r.dp/1e3).toFixed(1)} kPa</span></button>`).join('');
  if(!SH.inSel)shSel();
  if(shEl('shMore').open)shMoreFill();
}
/* 결과 그림을 누르면 그 자리에 핫스팟 추가 */
shEl('shTop').addEventListener('click',e=>{const sv=e.target.closest('.sh-tsvg');if(!sv||1)return;const q=sv.createSVGPoint();q.x=e.clientX;q.y=e.clientY;const m=q.matrixTransform(sv.getScreenCTM().inverse()),x=m.x,y=12-m.y;
  if(x<CHIP.x0||x>CHIP.x1||y<CHIP.y0||y>CHIP.y1){shToast('점선 칩 영역 안을 눌러 주세요.');return}
  const h={x:+Math.max(CHIP.x0+1,Math.min(CHIP.x1-1,x)).toFixed(1),y:+Math.max(CHIP.y0+1,Math.min(CHIP.y1-1,y)).toFixed(1),lx:2,ly:2,q:300};S.hs.push(h);selHs=S.hs.length-1;shSync();
  shToast(`H${S.hs.length} 핫스팟을 (${h.x}, ${h.y})에 추가했습니다.`,()=>{const i=S.hs.indexOf(h);if(i>=0){S.hs.splice(i,1);shSync()}})});
shEl('shRail').addEventListener('click',e=>{const b=e.target.closest('[data-pick]');if(!b)return;SH.pick=DESIGNS.find(d=>d.k===b.dataset.pick);shRes()});
function shSel(){const i=DESIGNS.indexOf(SH.pick);if(i>=0&&i!==sel){sel=i;SH.inSel=true;render();SH.inSel=false}}

function shMoreFill(){
  const cp=id=>{const e=$(id);return e?e.outerHTML.replace(/ id="[^"]*"/,''):''};
  const old=RFILT;RFILT=S.mode;drawProfile();if(sweep.length)drawSweep();
  shEl('shG1').innerHTML=cp('pfLegend')+cp('profile');shEl('shG2').innerHTML=swTabs()+cp('swLegend')+cp('sweep');
  RFILT=old;drawProfile();if(sweep.length)drawSweep();shEl('shSim').textContent=$('sim').textContent;
}
shEl('shMore').addEventListener('toggle',()=>{if(shEl('shMore').open)shMoreFill()});
shEl('shCsv').onclick=()=>$('xCsv').click();shEl('shCopy').onclick=()=>{$('xCopy').click();shEl('shCopy').textContent='복사했습니다';setTimeout(()=>shEl('shCopy').textContent='결과표 복사',1500)};
/* ---------- 자세히 보기: 기존 도면과 3D를 잠시 이 화면으로 옮겨 온다 ---------- */
const SHM={};
function shPark(el){if(!el)return;if(!SHM[el.id||el.className]){const ph=document.createComment('park');el.parentNode.insertBefore(ph,el);SHM[el.id||el.className]={el,ph}}}
function shDetEnter(){
  const top=res.length?rankBy(S.mode)[0]:null,d=SH.pick||(top?top.r.d:(res[sel]?res[sel].d:DESIGNS[1]));SH.pick=d;   // 순위가 비어 있어도(발열 0 W 등) 오류 없이 현재 선택 구조로
  const st=$('stage').closest('section');st.id=st.id||'shStageSec';
  shPark(st);shPark($('legend'));shPark(document.querySelector('.v3wrap'));shPark(document.querySelector('.v3leg'));
  const B=shEl('shDetB');B.append(st,$('legend'),document.querySelector('.v3wrap'),document.querySelector('.v3leg'));
  const i=DESIGNS.indexOf(d);if(i>=0)sel=i;
  shTab(SH.tab||'temp');
}
function shDetLeave(){for(const k in SHM){const {el,ph}=SHM[k];ph.parentNode.insertBefore(el,ph);ph.remove();delete SHM[k]}
  const st=$('stage').closest('section');st.hidden=false;document.querySelector('.v3wrap').hidden=false;document.querySelector('.v3leg').hidden=false;if(res.length)render()}
function shTab(t){
  SH.tab=t;document.querySelectorAll('[data-tab]').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.tab===t)));
  const is3=t==='3d',st=$('stage').closest('section');
  shEl('shDetB').classList.toggle('is3d',t==='3d');
  st.hidden=is3;document.querySelector('.v3wrap').hidden=!is3;document.querySelector('.v3leg').hidden=!is3;shEl('v3abar').hidden=!is3;
  if(!is3){const vb=document.querySelector(`[data-view="${t}"]`);if(vb)vb.click();else render()}
  else{render();V3.r=null;requestAnimationFrame(()=>{v3Build();v3AnimStart()})}
  shDetHead();
}
function shDetHead(){const r=res[sel];if(r)shEl('shDetT').textContent=`${r.d.name} · ${r.Tmax.toFixed(1)} °C`}
document.querySelector('.sh-tabs').addEventListener('click',e=>{const b=e.target.closest('[data-tab]');if(b)shTab(b.dataset.tab)});

/* 결과 그림의 초기화: 핫스팟을 모두 지우고 핫스팟 단계로 */
function shClearHs(){if(!S.hs.length)return;const prev=S.hs.map(h=>({...h}));S.hs=[];selHs=0;shDrawInput();shSync();
  shToast('핫스팟을 모두 지웠습니다.',()=>{S.hs=prev;shDrawInput();shSync()})}
shEl('shReset').onclick=shClearHs;shEl('shDetReset').onclick=shClearHs;
shRoute();

/* 직상부 공급형 후보 체크 (PC 체크와 같은 값) */
shEl('shDirect').checked=!!S.direct;
shEl('shDirect').addEventListener('change',()=>{S.direct=shEl('shDirect').checked;$('autoDirect').checked=S.direct;schedule()});
$('autoDirect').addEventListener('change',()=>{shEl('shDirect').checked=$('autoDirect').checked});

/* 그래프 크게 보기: 세로 화면이면 가로로 돌려서 꽉 차게 */
let shZg=null;
function shZoomFill(){if(!shZg)return;shEl('shZb').innerHTML=shEl(shZg).innerHTML;shEl('shZt').textContent=shEl(shZg).previousElementSibling.querySelector('span').childNodes[0].textContent.trim()}
function shZoomLay(){const b=shEl('shZbox'),W=innerWidth,H=innerHeight;
  if(H>W){b.style.width=H+'px';b.style.height=W+'px';b.style.transform=`translateX(${W}px) rotate(90deg)`}
  else{b.style.width=W+'px';b.style.height=H+'px';b.style.transform='none'}}
function shZoomOpen(g){shZg=g;shZoomFill();shZoomLay();shEl('shZoom').hidden=false}
function shZoomClose(){shZg=null;shEl('shZoom').hidden=true;shEl('shZb').innerHTML=''}
document.addEventListener('click',e=>{const z=e.target.closest('[data-zoom]');if(z){shZoomOpen(z.dataset.zoom);return}
  if(e.target.closest('#shZx')||e.target.id==='shZoom'){shZoomClose();return}
  if(e.target.closest('#shZb [data-swm]'))setTimeout(shZoomFill)});
addEventListener('resize',()=>{if(shZg)shZoomLay()});
addEventListener('hashchange',()=>{if(shZg)shZoomClose()});

/* 큰 도면에서 핫스팟 지우기 */
var HSX=-1;function hsShowX(i){HSX=i;document.querySelectorAll('#stage .hsg').forEach((g,k)=>g.classList.toggle('showx',k===i))}
function hsDelete(i){if(!S.hs[i])return;HSX=-1;S.hs.splice(i,1);selHs=0;justDragged=true;drag=null;renderHs();schedule()}
$('stage').addEventListener('pointerdown',e=>{const x=e.target.closest&&e.target.closest('.hsx');if(!x)return;e.preventDefault();e.stopImmediatePropagation();hsDelete(+x.dataset.hsx)},true);
{let lp=null,p0=null;
  $('stage').addEventListener('pointerup',e=>{if(e.pointerType==='mouse'||!p0||p0[2]==null)return;const i=p0[2],now=performance.now();if(lp&&lp.i===i&&now-lp.t<400){lp=null;hsShowX(HSX===i?-1:i);try{navigator.vibrate&&navigator.vibrate(15)}catch(_){}}else lp={i,t:now}});
  $('stage').addEventListener('pointerdown',e=>{const d=e.target.dataset;p0=[e.clientX,e.clientY,d&&d.i!==undefined?+d.i:null]},true);
  $('stage').addEventListener('pointerdown',e=>{if(HSX>=0&&!(e.target.closest&&e.target.closest('.hsx'))&&+(e.target.dataset?.i??-1)!==HSX)hsShowX(-1)},true);
  $('stage').addEventListener('pointermove',e=>{if(p0&&Math.hypot(e.clientX-p0[0],e.clientY-p0[1])>12){lp=null;p0=null}});
  $('stage').addEventListener('pointercancel',()=>{lp=null;p0=null});
  $('stage').addEventListener('contextmenu',e=>{if(e.target.dataset?.i!==undefined)e.preventDefault()});}
