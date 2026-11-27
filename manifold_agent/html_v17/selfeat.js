// [ML 고르기] 관통층 마스크(120×120, 1 = 공급망) → 모양 특징 → 순위 점수. ml/shape_features.py · ml/select_model.py 와 같은 식
const SEL_CHX=Array.from({length:22},(_,j)=>.75+.5*j);
function selOpenings(P,lo,hi){const out=[];
  for(const x of SEL_CHX){const ix=Math.round(x/.1),segs=[];let s=0;
    for(let i=1;i<=120;i++){if(i===120||P[i*120+ix]!==P[s*120+ix]){const v=P[s*120+ix];if(v){const y0=s*.1,y1=i*.1;if(y1>lo-1&&y0<hi+1)segs.push([v===1?'S':'C',Math.max(y0,lo-1),Math.min(y1,hi+1)])}s=i}}
    out.push(segs)}return out}
function selSummary(P,lo,hi){const ops=selOpenings(P,lo,hi),segs=ops.map(o=>{o=o.slice().sort((a,b)=>a[1]-b[1]);const r=[];
    for(let k=0;k+1<o.length;k++){const a=o[k],b=o[k+1];if(a[0]!==b[0]){const ya=(a[1]+a[2])/2,yb=(b[1]+b[2])/2,[ys,yc]=a[0]==='S'?[ya,yb]:[yb,ya];r.push([ys,yc,Math.max(Math.abs(yb-ya),.3)])}}return r});
  let G=0;for(const ch of segs)for(const s of ch)G+=1/s[2];return {G,segs,ops,lo,hi}}
function selCell(S,cell){const [r,c]=cell.split('_').map(Number),x0=(c-1)*3,x1=c*3,y0=(r-1)*3,y1=r*3,ycc=(y0+y1)/2;const fl=[],de=[],fr=[],pa=[];
  SEL_CHX.forEach((x,j)=>{if(!(x>=x0&&x<x1))return;let cov=0,f=0;const pth=[];
    for(const [ys,yc,L] of S.segs[j]){const a=Math.min(ys,yc),b=Math.max(ys,yc),ov=Math.max(0,Math.min(b,y1)-Math.max(a,y0));if(ov>0){cov+=ov;f+=(1/L)/S.G*ov/3;pth.push(Math.abs((Math.max(a,y0)+Math.min(b,y1))/2-ys))}}
    const chl=Math.max(Math.min(S.hi,y1)-Math.max(S.lo,y0),.1);fl.push(f);de.push(1-Math.min(cov,chl)/chl);
    const sup=S.ops[j].filter(o=>o[0]==='S').map(o=>(o[1]+o[2])/2);fr.push(sup.length?Math.min(...sup.map(s=>Math.abs(ycc-s))):12);
    pa.push(pth.length?pth.reduce((a,b)=>a+b,0)/pth.length:12)});
  const mean=a=>a.reduce((p,q)=>p+q,0)/a.length;return {flow:mean(fl),dead:mean(de),fresh:mean(fr),path:mean(pa)}}
function selHsPos(cells){const cs=cells.map(c=>c.split('_').map(Number)),ys=cs.map(([r])=>(r-.5)*3),xs=cs.map(([,c])=>(c-.5)*3);
  const ey=Math.min(...ys.map(y=>Math.min(y,12-y)))/12,xc=xs.reduce((a,b)=>a+b,0)/xs.length/12,vert=cs.length>1&&cs[0][1]===cs[1][1]?1:0;return [ey,xc,vert,ey*xc]}
// 점수 = log(Tmax − 20) 예측 (낮을수록 시원할 것). P: 120×120 (1 = 공급망), head: 헤더형이면 채널 1.5~10.5, 아니면 0.6~11.4
function selScore(M,P,head,cells,Q){const [lo,hi]=head?[1.5,10.5]:[.6,11.4],S=selSummary(P,lo,hi),cf=cells.map(c=>selCell(S,c)),eps=1e-4;
  const f={log_flow_worst:Math.log(Math.min(...cf.map(c=>c.flow))+eps),log_flow_mean:Math.log(cf.reduce((a,c)=>a+c.flow,0)/cf.length+eps),dead_max:Math.max(...cf.map(c=>c.dead)),
    dfresh_max:Math.max(...cf.map(c=>c.fresh))/12,dfresh_mean:cf.reduce((a,c)=>a+c.fresh,0)/cf.length/12,path_max:Math.max(...cf.map(c=>c.path))/12,logG:Math.log(S.G)};
  const H=selHsPos(cells),lq=Math.log(Math.max(30,Math.min(100,Q))/55),X=[...H,lq,...H.map(h=>h*lq),...M.sfeats.map(k=>f[k])];
  let m=M.intercept;for(let i=0;i<X.length;i++)m+=M.coef[i]*(X[i]-M.mu[i])/M.sd[i];
  // 학습 범위 밖: 특징이 학습 데이터 최소~최대를 (폭의 10 % 넘게) 벗어난 개수
  let out=0;if(M.xmin)for(let i=0;i<X.length;i++){const w=(M.xmax[i]-M.xmin[i])*.1;if(X[i]<M.xmin[i]-w||X[i]>M.xmax[i]+w)out++}
  return {m,X,out}}
if(typeof module!=='undefined')module.exports={selScore};
