/* ── [ML] 결과 화면(첫 화면 → 핫스팟 → 조건 → 결과)을 머신러닝 순위로 (2026-11-28, 사용자 요구) ──
   ① 1위 = 머신러닝 새 설계, 2~5위 = SimScale 로 돌려 본 모양(머신러닝이 고름)  ② 카드 숫자 = 이 에이전트의 간단 계산  ③ 3D 계산이 끝난 1·2위는 3D 값으로 바뀜.
   설계가 끝나기 전에는 '설계 중'만 보여 줌(기존 구조 순위를 대신 보여 주지 않음). 핫스팟이 없거나 발열이 0 이면 원래 화면 그대로. 계산식은 건드리지 않음. */
function mlShKey(){const H=(G&&G.p&&G.p.hs)||S.hs;return JSON.stringify([S.inl,!!S.direct,H.map(h=>[h.x,h.y,h.lx,h.ly,h.q])])}
function mlShList(){if(!AUTO||AUTO.key!==mlShKey()||(ML_CALC&&AUTO.calcKey!==AUTO.key))return null;const all=AUTO.cands.filter(c=>c.ml&&!c.hide);if(!all.length||all.some(c=>c.r===undefined))return null;
  const L=all.filter(c=>c.r).sort((a,b)=>a.ml-b.ml);return L.length?L:null}
function mlShView(c){   // 카드에 보일 값: 3D 값이 있으면 3D, 없으면 간단 계산
  const ra=c===AUTO.best?mlAutoRes():null,r=ra||c.r,nx=(AUTO.nsList||[]).find(x=>x.c===c),ns=r.ns||(nx&&nx.ns)||null;
  return {r,ns,T:r.ns?r.Tmax:(nx?nx.ns.Tmax:r.Tmax),dp:r.ns?r.dp:(nx?nx.ns.dp:r.dp)}}
function mlShName(c){return c.nice||mlNiceOf(c)}   // [모양 이름, 설명] — 새 설계 = '자동 최적화 모양', 나머지 = 형상 이름
function mlBusyText(st){st=st||'';   // 떠 있는 알림 문구: 설계가 끝나기 전에는 '최적화 매니폴드 형성 중', 그 뒤에는 단계 이름
  let done=false;try{done=!S.hs.length||!!mlShList()}catch(e){}if(!done)return '최적화 매니폴드 형성 중';
  if(/선택 설계/.test(st))return '고른 모양 정밀 계산 중';if(/구조별 유량장/.test(st))return '기존 구조 비교 계산 중';if(/유량 스윕/.test(st))return '유량별 비교 계산 중';return '마무리 계산 중'}
// 2~5위도 '온도·흐름·3D 자세히 보기'에서 볼 수 있게: 고른 후보의 간단 계산 결과를 '자동 설계' 자리에 끼워 넣어 그림·흐름·3D 가 그 모양을 그림 (다시 계산하지 않음)
var ML_VIEW=null,ML_VIEW_SAVE=null;
function mlAutoRes(){const i=DESIGNS.indexOf(AUTOD);if(i<0||res.length!==DESIGNS.length||!res[i])return null;return res[i].d===AUTOD?res[i]:(ML_VIEW_SAVE&&ML_VIEW_SAVE.d===AUTOD?ML_VIEW_SAVE:null)}
function mlViewApply(){const i=DESIGNS.indexOf(AUTOD);if(i<0||res.length!==DESIGNS.length||!res[i])return;
  const c=(ML_VIEW&&AUTO.cands.includes(ML_VIEW)&&ML_VIEW.r&&ML_VIEW!==AUTO.best)?ML_VIEW:null;
  if(c){if(res[i].d===AUTOD)ML_VIEW_SAVE=res[i];if(!c._vr||c._vr.src!==c.r){const t=mlShName(c);c._vr={...c.r,src:c.r,d:{...c.d,name:t[0],note:`${c.ml}위 · ${t[1]}`}}}res[i]=c._vr}
  else if(res[i].d!==AUTOD&&ML_VIEW_SAVE&&ML_VIEW_SAVE.d===AUTOD)res[i]=ML_VIEW_SAVE}
// 한도 경고: 어떤 한도를 얼마나 넘는지 구체적으로 (원본 문구 '한도(압력강하·레이놀즈 수·최고 온도)를 넘는 조건입니다'는 뜻이 안 통한다는 사용자 지적)
function mlWhyOver(v){const r=v.r,w=[],Tl=S.Tlim??85;if(v.T>Tl)w.push(`칩 최고 온도 ${v.T.toFixed(1)} °C가 정해 둔 한도 ${Tl} °C보다 높습니다`);if(S.dpMax!=null&&v.dp>S.dpMax*1e3)w.push(`압력강하 ${(v.dp/1e3).toFixed(1)} kPa가 한도 ${S.dpMax} kPa보다 큽니다`);if(r.ReMax>2300)w.push(`레이놀즈 수 ${r.ReMax.toFixed(0)}이 2300을 넘어 층류 계산 범위 밖입니다`);
  if(!w.length&&!validR(r))w.push('이 모양은 간단 계산이 범위를 벗어나(예: 물 온도 95 °C 초과) 값이 정확하지 않을 수 있습니다');return w.length?`<p class="sh-warn">${w.join(' · ')}</p>`:''}
function mlShRes(){
  const top=shEl('shTop'),rail=shEl('shRail');if(!top||!rail||!S.hs.length||!hasHeat()||!res.length)return false;
  const L=mlShList();
  shEl('shResSub').textContent=`유량 ${S.Q} ml/min · 핫스팟 ${S.hs.length}개`;
  if(!L){shEl('shResBusy').hidden=true;rail.innerHTML='';
    if(SH.mlWaitKey!==mlShKey()+'|'+S.Q){SH.mlWaitKey=mlShKey()+'|'+S.Q;SH.mlT0=Date.now()}   // 설계 중 카드: 흐르는 시간과 진행 막대(100초 기준, 끝나기 전에는 95 %에서 멈춤)
    if(!top.querySelector('#mlWait'))top.innerHTML=`<div class="sh-tb" id="mlWait"><b class="sh-tn">핫스팟 에이전트가 매니폴드를 설계하는 중입니다</b><small>최대 100초까지 걸립니다 · <b id="mlWaitT" style="color:#0B4BD6;font-variant-numeric:tabular-nums">0초</b> 지남</small><div style="height:8px;border-radius:4px;background:#DCE5F5;margin-top:12px;overflow:hidden"><i id="mlWaitB" style="display:block;height:100%;width:0;background:#0B4BD6;border-radius:4px;transition:width .9s linear"></i></div></div>`;
    mlWaitTick();return true}
  if(SH.mlKey!==AUTO.key||SH.mlPick==null||SH.mlPick>=L.length){SH.mlPick=0;SH.mlKey=AUTO.key;ML_VIEW=null}
  const V=L.map(mlShView),m=res.find(r=>r.d.ref),lo=Math.min(...V.map(v=>v.r.Tmin),m?m.Tmin:1e9),hi=Math.max(...V.map(v=>v.r.Tmax),m?m.Tmax:-1e9);
  const c=L[SH.mlPick],v=V[SH.mlPick],[nm,sub]=mlShName(c),dT=m?v.T-m.Tmax:0,busy3=!v.ns&&c.ml<=2&&NS_POOL&&!(NS_LIVE&&NS_LIVE.done);
  {const bz=shEl('shResBusy');bz.hidden=!SH.busy;if(SH.busy&&/조건이 바뀌어/.test(bz.textContent))bz.textContent='1~5위는 간단 계산값입니다. 이어서 1·2위를 3D로 다시 풀고 있습니다…'}   // 순위가 이미 나온 뒤의 '계산 중' 문구
  top.innerHTML=`<div class="sh-tw">${shTile(v.r,lo,hi,true)}<span class="sh-rk">${c.ml}위</span></div>
    <div class="sh-tb"><b class="sh-tn">${esc(nm)}</b><small>${esc(sub)}</small>${v.ns?`<small style="display:inline-block;margin-top:4px;padding:2px 8px;border-radius:10px;background:#E3F6EC;color:#0E7A43;font-weight:700">✓ 3D 나비에–스토크스 + 열전달 계산값${v.ns.sec?` (${(v.ns.sec/60).toFixed(1)}분)`:''}</small>`:`<small style="display:inline-block;margin-top:4px;padding:2px 8px;border-radius:10px;background:#FFF4D6;color:#8A5A00;font-weight:700">간이 계산값${busy3?' — 3D 계산 중이거나 대기 (1·2위만 3D 로 다시 풉니다)':''}</small>`}
    <div class="sh-kv"><div><span>칩 최고 온도</span><b>${v.T.toFixed(1)} °C</b></div><div><span>매니폴드 없음 대비</span><b class="${dT<0?'good':'bad'}">${(dT>0?'+':'')+dT.toFixed(1)+' °C'}</b></div><div><span>압력강하</span><b>${(v.dp/1e3).toFixed(1)} kPa</b></div></div>
    ${mlWhyOver(v)}</div>`;
  rail.innerHTML=L.map((c2,i)=>{const v2=V[i],[n2]=mlShName(c2);return `<button type="button" class="sh-card2 ${i===SH.mlPick?'on':''}" data-mlpick="${i}"><div class="sh-tw sm">${shTile(v2.r,lo,hi,false)}<span class="sh-rk">${c2.ml}</span></div><b>${esc(n2)}</b><span>${v2.T.toFixed(1)} °C · ${(v2.dp/1e3).toFixed(1)} kPa${v2.ns?' · 3D':''}</span></button>`}).join('');
  if(DESIGNS.indexOf(AUTOD)>=0)SH.pick=AUTOD;if(!SH.inSel)shSel();
  if(shEl('shMore').open)shMoreFill();
  return true}
function mlWaitTick(){const t=document.getElementById('mlWaitT'),b=document.getElementById('mlWaitB');if(!t||!b)return;const s=Math.max(0,(Date.now()-(SH.mlT0||Date.now()))/1000);t.textContent=Math.floor(s)+'초';b.style.width=Math.min(95,s/100*100).toFixed(1)+'%'}
setInterval(mlWaitTick,1000);
{const r0=shRes;shRes=function(){try{if(mlShRes())return}catch(e){console.error('mlShRes',e)}return r0.apply(this,arguments)};
 const d0=drawAuto;drawAuto=function(){const x=d0.apply(this,arguments);
  // 자동 설계가 방금 목록에 들어온 직후에는 결과 배열(res)에 그 자리가 아직 없음(정밀 풀이 뒤에 채워짐) → 그 몇 초 동안 '자세히 보기'가 다른 구조를 그리지 않게 간단 계산 결과를 먼저 넣어 둠
  try{const i=DESIGNS.indexOf(AUTOD);if(i>=0&&res.length===DESIGNS.length-1&&AUTO.best&&AUTO.best.r){res.splice(i,0,{...AUTO.best.r,d:AUTOD});render()}}catch(e){}
  try{if(SH.page==='res'||!shEl('sh-res').hidden)shRes();shCrit()}catch(e){}return x};
 const c0=shCrit;shCrit=function(){const x=c0.apply(this,arguments);try{if(S.hs.length&&hasHeat()){const L=mlShList(),t=L?(()=>{const v=mlShView(L[0]);return `머신러닝 1위 · ${mlShName(L[0])[0]} ${v.T.toFixed(1)} °C · ${(v.dp/1e3).toFixed(1)} kPa`})():'머신러닝이 설계하는 중…';document.querySelectorAll('[data-top]').forEach(e=>{e.textContent=t})}}catch(e){}return x};
 shEl('shRail').addEventListener('click',e=>{const b=e.target.closest('[data-mlpick]');if(!b)return;SH.mlPick=+b.dataset.mlpick;const L=mlShList();ML_VIEW=L&&L[SH.mlPick]!==AUTO.best?L[SH.mlPick]:null;if(res.length)render();shRes()});
 const h0=shDetHead;shDetHead=function(){h0.apply(this,arguments);try{const r=res[sel];if(r&&r.d===AUTOD&&AUTO.best&&AUTO.best.nice)shEl('shDetT').textContent=`${AUTO.best.nice[0]} · ${r.Tmax.toFixed(1)} °C`}catch(e){}}}
