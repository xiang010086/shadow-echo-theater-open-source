// Original editable digital shadow figures. Rigid pieces rotate at visible pins.
// This is a production prototype, not a reconstruction of a named regional style.
import {animalSprite,hostSprite} from './sprites.mjs';
import {companionSprite} from './companion-sprites.mjs';
import {companionReaction} from './companion-actions.mjs';
const paper = '#ecd5a0';
const ink = '#3c241b';
const clamp = (v, a=0, b=1) => Math.min(b, Math.max(a,v));
const smooth = v => {v=clamp(v);return v*v*(3-2*v);};
const mix = (a,b,v) => a+(b-a)*smooth(v);

function companions(t,reaction){
  return companionSprite('deer',265,515,t,{flee:reaction.deer,start:reaction.start?reaction.start+.25:0,watch:reaction.watch})+
    companionSprite('rabbit',170,520,t,{flee:reaction.rabbit,start:reaction.start,watch:reaction.watch});
}
function tree(x,flip=1) {
  return `<g transform="translate(${x} 480) scale(${flip} 1)"><path d="M-30 45L-14-103L-65-163L-58-174L-13-139L-10-243L8-246L14-160L58-196L65-181L14-121L31 45Z" fill="#69543c" stroke="${ink}" stroke-width="3"/><path d="M0-160Q-108-176-99-225Q-109-260-62-268Q-61-312-12-291Q32-317 49-274Q96-275 91-231Q124-189 58-174Z" fill="#526650" stroke="${ink}" stroke-width="3"/><path d="M-58-237l35-20 18 35 27-28 36 24M-9-142l5 160" stroke="${paper}" stroke-width="2" opacity=".7" fill="none"/></g>`;
}

let timeline;
const animal=animalSprite;
const host=hostSprite;
export function setTimeline(value){timeline=value;}
export function renderAt(clip,t) {
  const data=timeline[clip], duration=data.duration;
  const line=data.lines.find(l=>t>=l.start && t<l.end);
  const speaker=line?.role;
  const reveal=smooth(t/.6), closing=clip==='ending'||clip==='curtain'?1-smooth((t-duration+.7)/.7):
    clip==='alone'?1-smooth((t-duration+.35)/.35):1;
  let actors='', props='';
  let fx=490, tx=900;
  const addFox=(x=fx,options={})=>animal('fox',x,options.y??382,options.size??.95,t,{talk:speaker==='fox',...options});
  const addTiger=(x=tx,options={})=>animal('tiger',x,options.y??309,options.size??1.25,t,{talk:speaker==='tiger',...options});
  if(clip==='idle') {
    const enter=smooth((t-.3)/1.8), exit=smooth((t-duration+2.5)/2);
    const x=mix(-220,625,enter)-exit*850;
    const beckon=speaker==='host'?.5+.4*Math.sin(t*1.5):.15;
    actors=host(x,119,1.65,t,{talk:speaker==='host',bow:Math.sin(clamp((t-1.5)/1.1)*Math.PI)*.6,gesture:beckon});
  } else if(['welcome','prediction_reply','method_reply','method_reply_alone'].includes(clip)) {
    const enter=clip==='welcome'?smooth(t/1.8):1;
    const exit=clip==='welcome'?smooth((t-duration+1.7)/1.5):0;
    actors=host(mix(-220,625,enter)-exit*850,119,1.65,t,{talk:speaker==='host',bow:Math.sin(clamp((t-1.5)/1.2)*Math.PI)*.7,gesture:.55});
  } else if(clip==='opening') {
    fx=mix(-220,490,t/2.4);tx=mix(1530,900,t/2.4);
    actors=addFox(fx,{walk:t<2.4?1:0,facing:t<2.4?'right':'left',head:speaker==='fox'?-5:0})+addTiger(tx,{walk:t<2.4?1:0,head:speaker==='tiger'?-6:0});
  } else if(clip==='prediction_wait'||clip==='method_wait') {
    actors=addFox(490)+addTiger(900)+host(165,301,.9,t,{gesture:.35+.12*Math.sin(t*1.1)});
  } else if(clip==='question'||clip==='prediction') {
    actors=companions(t,companionReaction(clip,t,data))+addFox(490)+addTiger(900);
    const hostLine=data.lines.filter(l=>l.role==='host').at(-1);
    if(t>hostLine.start-1)actors+=host(mix(-180,165,(t-hostLine.start+1)/1),301,.9,t,{talk:speaker==='host',gesture:.65});
  } else if(clip==='hide') {
    fx=mix(490,465,t/2);tx=mix(900,1490,t/2);
    const prey=companions(t,companionReaction(clip,t,data));
    actors=prey+addTiger(tx,{walk:t<2?1:0})+addFox(fx,{walk:t<2?1:0});
    props=tree(1050,-1);
    // Bring both figures back to the shared ending marks during the final pause.
    if(t>duration-2){const a=smooth((t-duration+2)/2);actors=prey+addTiger(mix(tx,900,a),{walk:1})+addFox(mix(fx,490,a),{walk:1});props=`<g opacity="${1-a}">${tree(1050,-1)}</g>`;}
  } else if(clip==='alone') {
    const actionStart=data.lines.find(l=>l.role==='host')?.start ?? 1.5;
    const onward=smooth((t-actionStart)/2);
    tx=mix(700,430,onward);
    actors=companions(t,companionReaction(clip,t,data))+addFox(1035)+addTiger(tx,{walk:onward>0&&onward<1});
  } else if(clip==='ending') {
    const exit=data.lines.find(l=>l.role==='fox');
    const leaving=smooth((t-exit.end+.8)/1.8);
    const hostLine=data.lines.find(l=>l.role==='host');
    const tigerExit=smooth((t-hostLine.start-2)/2);
    actors=addFox(mix(490,-220,leaving),{walk:leaving>0&&leaving<1?1:0})+addTiger(mix(900,1530,tigerExit),{walk:tigerExit>0&&tigerExit<1?1:0,facing:tigerExit>0?'right':'left'});
    if(t>hostLine.start-.7)actors+=host(mix(-180,550,(t-hostLine.start+.7)/1),301,.95,t,{talk:speaker==='host',gesture:.55,bow:smooth((t-duration+2)/1.2)});
  } else if(clip==='curtain') {
    const entry=smooth(t/1.7),exit=smooth((t-7.5)/2);
    const bow=Math.sin(clamp((t-2.4)/1.3)*Math.PI)+Math.sin(clamp((t-4.2)/1.3)*Math.PI);
    actors=addFox(mix(-220,280,entry)-exit*650,{size:.85,y:408.2,walk:t<1.7||t>7.5?1:0,facing:t<1.7?'right':'left',bow,head:-bow*9})+
      addTiger(mix(1530,970,entry)+exit*650,{size:1,y:359.5,walk:t<1.7||t>7.5?1:0,facing:t>7.5?'right':'left',bow,head:-bow*8})+
      host(mix(1490,600,entry)-exit*850,293,.95,t,{bow,gesture:.6});
  }
  return `<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
    <defs><radialGradient id="light"><stop stop-color="#f8e7bb"/><stop offset=".72" stop-color="${paper}"/><stop offset="1" stop-color="#c7a46c"/></radialGradient><linearGradient id="wood" x2="0" y2="1"><stop stop-color="#643c28"/><stop offset=".5" stop-color="#2e211b"/><stop offset="1" stop-color="#563522"/></linearGradient><pattern id="weave" width="5" height="5" patternUnits="userSpaceOnUse"><path d="M0 0h5M0 0v5" stroke="#886d3b" stroke-width=".35" opacity=".17"/></pattern><clipPath id="window"><rect x="26" y="26" width="1228" height="668"/></clipPath></defs>
    <rect width="1280" height="720" fill="url(#wood)"/>
    <rect x="26" y="26" width="1228" height="668" fill="url(#light)" stroke="#a47c40" stroke-width="3"/>
    <rect x="26" y="26" width="1228" height="668" fill="url(#weave)"/>
    <path d="M13 13H1267V707H13Z" stroke="#b18a4a" stroke-width="2" fill="none"/>
    <g clip-path="url(#window)" opacity="${reveal*closing}">
      <g transform="translate(640 650) scale(1.12) translate(-640 -532)">
      <path d="M65 519Q340 510 590 521T1215 519v32H65Z" fill="#9c8055" opacity=".32"/>
      ${['welcome','idle','curtain'].includes(clip)?'':`<g opacity=".55">${tree(111,-1)}${tree(1170,1)}</g>`}
      ${actors}${props}
      <rect x="-100" y="532" width="1500" height="60" fill="#261d16"/>
      </g>
    </g>
  </svg>`;
}
