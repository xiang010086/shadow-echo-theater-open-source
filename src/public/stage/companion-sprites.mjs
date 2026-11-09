// Generated leather-puppet pixels are unchanged; SVG masks isolate rigid plates.
const art={
  rabbit:{uri:'rabbit-v2.png',w:1536,h:1024,scale:.13,anchor:760,ground:902,
    head:{path:'M700 0H1410V738H1080L1012 719L949 685L894 626L919 544L889 497Z',pivot:[975,684]},
    legs:[
      {path:'M556 788H661L704 841L752 860V914H586L548 871Z',pivot:[610,780],sign:1},
      {path:'M988 734L1041 744L1045 808L1137 819L1156 858L1128 890H1025L994 851Z',pivot:[1010,750],sign:-1},
      {path:'M538 713L638 730L633 790L577 840L713 850L751 879L731 914H369L354 876L389 816L469 760Z',pivot:[602,752],sign:-1},
      {path:'M901 749L993 750L979 832L1031 875L1060 906H898L871 867V799Z',pivot:[958,764],sign:1}
    ]},
  deer:{uri:'deer-v2.png',w:1312,h:1199,scale:.14,anchor:650,ground:1119,
    head:{path:'M660 0H1250V428H950L914 428L883 398L866 369L694 344Z',pivot:[910,400]},
    legs:[
      {path:'M470 686L546 707L484 865L478 1040L532 1086V1130H443L425 1060L407 888Z',pivot:[505,714],sign:1},
      {path:'M804 640L874 640L895 814L885 1020L933 1084V1131H848L823 1040L819 893L796 802Z',pivot:[820,665],sign:-1},
      {path:'M331 566L431 592L407 711L338 851L316 1043L338 1089V1130H249L231 1080L241 945L259 852L299 740Z',pivot:[365,570],sign:-1},
      {path:'M792 639L858 673L824 757L792 871L770 1047L802 1094V1132H714L691 1075L697 966L709 867L743 756Z',pivot:[820,665],sign:1}
    ]}
};

export function setCompanionTextures(rabbit,deer){art.rabbit.uri=rabbit;art.deer.uri=deer;}

export function companionSprite(type,x,floor,t,{flee=0,start=0,watch=0}={}){
  if(flee>=1)return '';
  const a=art[type],id=`companion-${type}`,active=flee>0;
  const turning=t>=start-.2&&start>0;
  const direction=active||turning?-1:1;
  const phase=(t-start)*11;
  const bob=active?Math.abs(Math.sin(phase))*(type==='rabbit'?6:2):0;
  const offset=flee*(type==='rabbit'?460:500);
  const source=()=>`<image href="${a.uri}" width="${a.w}" height="${a.h}" filter="url(#${id}-clean)"/>`;
  const plate=(name,path,angle,pivot)=>`<defs><clipPath id="${id}-${name}"><path d="${path}"/></clipPath></defs><g transform="rotate(${angle} ${pivot[0]} ${pivot[1]})"><g clip-path="url(#${id}-${name})">${source()}</g></g>`;
  const angles=a.legs.map(leg=>active?Math.sin(phase+(leg.sign<0?Math.PI:0))*(type==='rabbit'?7:11):0);
  const layers=a.legs.map((leg,i)=>plate(`leg${i}`,leg.path,angles[i],leg.pivot));
  const exclusions=[a.head.path,...a.legs.map(leg=>leg.path)];
  return `<g data-companion="${type}" data-flee="${flee.toFixed(3)}" transform="translate(${x-offset} ${floor-bob}) scale(${a.scale*direction} ${a.scale}) translate(${-a.anchor} ${-a.ground})">
    <defs><filter id="${id}-clean" color-interpolation-filters="sRGB"><feComponentTransfer><feFuncA type="linear" slope="7" intercept="-5.6"/></feComponentTransfer></filter>
    <mask id="${id}-body" maskUnits="userSpaceOnUse" x="0" y="0" width="${a.w}" height="${a.h}"><rect width="${a.w}" height="${a.h}" fill="white"/>${exclusions.map(path=>`<path d="${path}" fill="black"/>`).join('')}</mask></defs>
    <path d="M${a.anchor} ${a.ground-340}L${a.anchor+32} ${a.ground+380}" stroke="#412b1f" stroke-width="9" opacity=".65"/>
    ${layers.slice(0,2).join('')}<g mask="url(#${id}-body)">${source()}</g>${layers.slice(2).join('')}
    ${plate('head',a.head.path,-watch*(type==='rabbit'?5:7),a.head.pivot)}
  </g>`;
}
