const fs=require('fs'),vm=require('vm');
const ctx={console,atob,Math,Float32Array,Float64Array,Uint8Array,Uint16Array,Int32Array,Uint32Array,Int8Array,Array,Object,JSON,Number,isFinite,Infinity,NaN,Set,Map,Promise,setTimeout,Error,RangeError};
vm.createContext(ctx);
const src=fs.readFileSync('calcA.js','utf8')+'\n'+fs.readFileSync('calcB.js','utf8')+`
var S={Q:55,t:'0.5',inl:'q',Tin:20,q0:50,ks:235,wprop:'fixed',fl:'w',phi:0,hs:[]};
this.API={DESIGNS,loadDesigns,setup,evaluate,attachPresetFlow,presetGeo,makeFlow,flowSolve,aGeo,aDesign,port_ok,setS:o=>{S=Object.assign(S,o)}};`;
vm.runInContext(src,ctx,{filename:'calc.js'});
module.exports=ctx.API;
if(require.main===module){
  const A=ctx.API;A.loadDesigns(JSON.parse(fs.readFileSync('hsdata.json','utf8')));
  const n=A.attachPresetFlow(A.DESIGNS);console.log('presets re-solved',n);
  const cell=c=>{const [r,k]=c.split('_').map(Number);return {x:(k-.5)*3,y:(r-.5)*3,lx:3,ly:3,q:300}};
  const cases=JSON.parse(process.argv[2]);
  for(const [des,hs,Q,Tsim] of cases){
    const hsl=hs.split('+').map(cell);A.setS({hs:hsl,Q});
    const G=A.setup({Tin:20,q0:50,ks:235,hs:hsl,inl:'q',wprop:'fixed',fl:'w',phi:0});
    const d=A.DESIGNS.find(x=>x.k===des);const t0=Date.now();
    const r=A.evaluate(G,d,Q,'0.5');
    console.log(des,hs,Q,'HTML Tmax',r.Tmax.toFixed(1),'SimScale',Tsim,'dp kPa',(r.dp/1e3).toFixed(2),'s',((Date.now()-t0)/1e3).toFixed(1));
  }
}
