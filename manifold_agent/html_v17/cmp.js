const fs=require('fs');const A=require('./run.js');
A.loadDesigns(JSON.parse(fs.readFileSync('hsdata.json','utf8')));
const meta=JSON.parse(fs.readFileSync('design_meta.json','utf8'));
const near=(a,b)=>Math.hypot(a[0]-b[0],a[1]-b[1])<.3;
const sw=a=>Uint8Array.from(a,v=>v===1?2:v===2?1:v);
const USE={};
for(const d of A.DESIGNS){if(d.ref){USE[d.k]=d;continue}const m=meta[d.k];if(!m)continue;
  const same=m.inlets.every(p=>d.ports.slice(0,2).some(q=>near(p,q)));
  USE[d.k]=same?d:{...d,k:d.k,ports:[d.ports[2],d.ports[3],d.ports[0],d.ports[1]],P:sw(d.P),U:sw(d.U),layers:d.layers.map(l=>({...l,M:l.M})),flow:null,rev:true}}
const M1=A.DESIGNS.find(x=>x.k==='M1'),SM=JSON.parse(fs.readFileSync('strip_masks.json','utf8'));
for(const k in SM){const P=Uint8Array.from(SM[k].P),U=Uint8Array.from(SM[k].U);
  USE[k]={k,name:k,T:M1.T,P,U,ports:[[9,1],[9,11],[3,1],[3,11]],head:1,layers:[{h:.15,M:Uint8Array.from(P,v=>v?1:0)},{h:.4,M:Uint8Array.from(U,v=>v?1:0)}]}}
const n=A.attachPresetFlow(Object.values(USE));
const cell=c=>{const [r,k]=c.split('_').map(Number);return {x:(k-.5)*3,y:(r-.5)*3,lx:3,ly:3,q:300}};
const rows=[];
for(const [des,hs,Q,Ts,pmax,pmin] of JSON.parse(fs.readFileSync('runs.json','utf8'))){
  const d=USE[des];if(!d)continue;const hsl=hs.split('+').map(cell);A.setS({hs:hsl,Q});
  const G=A.setup({Tin:20,q0:50,ks:235,hs:hsl,inl:'q',wprop:'fixed',fl:'w',phi:0});
  let r;try{r=A.evaluate(G,d,Q,'0.5')}catch(e){console.error(des,hs,Q,e.message);continue}
  rows.push({des,hs,Q,Ts,Th:+r.Tmax.toFixed(1),Ps:pmax,Ph:Math.round(r.dp),rev:!!d.rev});
}
fs.writeFileSync('cmp.json',JSON.stringify(rows));console.log('done',rows.length);
