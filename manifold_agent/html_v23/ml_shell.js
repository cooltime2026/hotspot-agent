/* ── [ML] 결과 화면(첫 화면 → 핫스팟 → 조건 → 결과)을 머신러닝 순위로 (2026-11-28, 사용자 요구) ──
   ① 1위 = 머신러닝 새 설계, 2~5위 = SimScale 로 돌려 본 모양(머신러닝이 고름)  ② 카드 숫자 = 이 에이전트의 간단 계산  ③ 3D 계산이 끝난 1·2위는 3D 값으로 바뀜.
   설계가 끝나기 전에는 '설계 중'만 보여 줌(기존 구조 순위를 대신 보여 주지 않음). 핫스팟이 없거나 발열이 0 이면 원래 화면 그대로. 계산식은 건드리지 않음. */
function mlShKey(){const H=(G&&G.p&&G.p.hs)||S.hs;return JSON.stringify([S.inl,!!S.direct,H.map(h=>[h.x,h.y,h.lx,h.ly,h.q])])}
function mlShList(){if(!AUTO||AUTO.key!==mlShKey())return null;const all=AUTO.cands.filter(c=>c.ml&&!c.hide);if(!all.length||all.some(c=>c.r===undefined))return null;
  const L=all.filter(c=>c.r).sort((a,b)=>a.ml-b.ml);return L.length?L:null}
function mlShView(c){   // 카드에 보일 값: 3D 값이 있으면 3D, 없으면 간단 계산
  const i=DESIGNS.indexOf(AUTOD),ra=(c===AUTO.best&&i>=0&&res.length===DESIGNS.length&&res[i]&&res[i].d===AUTOD)?res[i]:null,r=ra||c.r,nx=(AUTO.nsList||[]).find(x=>x.c===c),ns=r.ns||(nx&&nx.ns)||null;
  return {r,ns,T:r.ns?r.Tmax:(nx?nx.ns.Tmax:r.Tmax),dp:r.ns?r.dp:(nx?nx.ns.dp:r.dp)}}
function mlShName(c){const n=c.name.replace(/^\d위 /,'');let m=n.match(/^(머신러닝 새 설계(?: N\d+)?) ?\(?(.*?)\)?$/);if(m)return [m[1],m[2]];m=n.match(/^(실측 모양 \S+) · (.*)$/);if(m)return [m[1],m[2]];m=n.match(/^(머신러닝 최적) · (.*)$/);return m?[m[1],m[2]]:[n,'']}
function mlShRes(){
  const top=shEl('shTop'),rail=shEl('shRail');if(!top||!rail||!S.hs.length||!hasHeat()||!res.length)return false;
  const L=mlShList();
  shEl('shResSub').textContent=`머신러닝 순위 · 유량 ${S.Q} ml/min · 핫스팟 ${S.hs.length}개`;
  if(!L){shEl('shResBusy').hidden=true;rail.innerHTML='';
    top.innerHTML=`<div class="sh-tb"><b class="sh-tn">머신러닝이 매니폴드를 설계하는 중입니다</b><small>핫스팟 위치·크기·열유속에 맞춰 새 모양(1위)을 만들고, 지금까지 SimScale 로 돌려 본 모양 중 2~5위를 고른 뒤 간단 계산으로 온도를 냅니다. 보통 20초 안팎입니다.</small></div>`;return true}
  if(SH.mlKey!==AUTO.key||SH.mlPick==null||SH.mlPick>=L.length){SH.mlPick=0;SH.mlKey=AUTO.key}
  const V=L.map(mlShView),m=res.find(r=>r.d.ref),lo=Math.min(...V.map(v=>v.r.Tmin),m?m.Tmin:1e9),hi=Math.max(...V.map(v=>v.r.Tmax),m?m.Tmax:-1e9);
  const c=L[SH.mlPick],v=V[SH.mlPick],[nm,sub]=mlShName(c),dT=m?v.T-m.Tmax:0,busy3=!v.ns&&c.ml<=2&&NS_POOL&&!(NS_LIVE&&NS_LIVE.done);
  {const bz=shEl('shResBusy');bz.hidden=!SH.busy;if(SH.busy&&/조건이 바뀌어/.test(bz.textContent))bz.textContent='1~5위는 간단 계산값입니다. 이어서 1·2위를 3D로 다시 풀고 있습니다…'}   // 순위가 이미 나온 뒤의 '계산 중' 문구
  top.innerHTML=`<div class="sh-tw">${shTile(v.r,lo,hi,true)}<span class="sh-rk">${c.ml}위</span></div>
    <div class="sh-tb"><b class="sh-tn">${esc(nm)}</b><small>${esc(sub)}</small>${v.ns?`<small style="display:inline-block;margin-top:4px;padding:2px 8px;border-radius:10px;background:#E3F6EC;color:#0E7A43;font-weight:700">✓ 3D 나비에–스토크스 + 열전달 계산값${v.ns.sec?` (${(v.ns.sec/60).toFixed(1)}분)`:''}</small>`:`<small style="display:inline-block;margin-top:4px;padding:2px 8px;border-radius:10px;background:#FFF4D6;color:#8A5A00;font-weight:700">간이 계산값${busy3?' — 3D 계산 중이거나 대기 (1·2위만 3D 로 다시 풉니다)':''}</small>`}
    <div class="sh-kv"><div><span>칩 최고 온도</span><b>${v.T.toFixed(1)} °C</b></div><div><span>매니폴드 없음 대비</span><b class="${dT<0?'good':'bad'}">${(dT>0?'+':'')+dT.toFixed(1)+' °C'}</b></div><div><span>압력강하</span><b>${(v.dp/1e3).toFixed(1)} kPa</b></div></div>
    ${feas(v.r)?'':'<p class="sh-warn">한도(압력강하·레이놀즈 수·최고 온도)를 넘는 조건입니다.</p>'}</div>`;
  rail.innerHTML=L.map((c2,i)=>{const v2=V[i],[n2]=mlShName(c2);return `<button type="button" class="sh-card2 ${i===SH.mlPick?'on':''}" data-mlpick="${i}"><div class="sh-tw sm">${shTile(v2.r,lo,hi,false)}<span class="sh-rk">${c2.ml}</span></div><b>${esc(n2)}</b><span>${v2.T.toFixed(1)} °C · ${(v2.dp/1e3).toFixed(1)} kPa${v2.ns?' · 3D':''}</span></button>`}).join('');
  if(DESIGNS.indexOf(AUTOD)>=0)SH.pick=AUTOD;if(!SH.inSel)shSel();
  if(shEl('shMore').open)shMoreFill();
  return true}
{const r0=shRes;shRes=function(){try{if(mlShRes())return}catch(e){console.error('mlShRes',e)}return r0.apply(this,arguments)};
 const d0=drawAuto;drawAuto=function(){const x=d0.apply(this,arguments);try{if(SH.page==='res'||!shEl('sh-res').hidden)shRes();shCrit()}catch(e){}return x};
 const c0=shCrit;shCrit=function(){const x=c0.apply(this,arguments);try{if(S.hs.length&&hasHeat()){const L=mlShList(),t=L?(()=>{const v=mlShView(L[0]);return `머신러닝 1위 · ${mlShName(L[0])[0]} ${v.T.toFixed(1)} °C · ${(v.dp/1e3).toFixed(1)} kPa`})():'머신러닝이 설계하는 중…';document.querySelectorAll('[data-top]').forEach(e=>{e.textContent=t})}}catch(e){}return x};
 shEl('shRail').addEventListener('click',e=>{const b=e.target.closest('[data-mlpick]');if(!b)return;SH.mlPick=+b.dataset.mlpick;shRes()})}
