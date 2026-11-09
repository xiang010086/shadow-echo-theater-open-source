const clamp=v=>Math.max(0,Math.min(1,v));

export function companionReaction(clip,t,data){
  if(clip==='question')return {rabbit:1,deer:1,watch:0,start:0};
  if(clip==='prediction'||clip==='alone'){
    const start=clip==='prediction'?Math.max(1,(data.lines[0]?.end||8)-2.4):
      (data.lines.find(line=>line.role==='host')?.start||6)+.7;
    const watch=clamp((t-start+1.2)/.6)*(1-clamp((t-start+.2)/.2));
    return {rabbit:clamp((t-start)/1.6),deer:clamp((t-start-.25)/1.9),watch,start};
  }
  const fox=data.lines.find(line=>line.role==='fox');
  const elapsed=fox?t-fox.start:0;
  const watch=elapsed>0&&elapsed<3?Math.sin(elapsed/3*Math.PI)*.5:0;
  return {rabbit:0,deer:0,watch,start:0};
}
