// Rigging an original generated leather-puppet atlas in SVG. The source pixels
// stay unchanged; masks separate rigid plates for deterministic offline filming.
let uri='characters-v1.png';
export function setSpriteURI(value){uri=value;}
const image=()=>`<image href="${uri}" width="1920" height="819"/>`;
const rotate=(angle,x,y)=>`rotate(${angle} ${x} ${y})`;
const segment=(id,path,angle,x,y)=>`<defs><clipPath id="${id}"><path d="${path}"/></clipPath></defs><g transform="${rotate(angle,x,y)}"><g clip-path="url(#${id})">${image()}</g></g>`;
const body=(id,box,exclusions)=>`<defs><mask id="${id}" maskUnits="userSpaceOnUse" x="0" y="0" width="1920" height="1200"><rect x="${box[0]}" y="${box[1]}" width="${box[2]}" height="${box[3]}" fill="white"/>${exclusions.map(d=>`<path d="${d}" fill="black"/>`).join('')}</mask></defs><g mask="url(#${id})">${image()}</g>`;
const rod=(x,y,bx,by)=>`<path d="M${x} ${y}L${bx} ${by}" fill="none" stroke="#412b1f" stroke-width="4.4" opacity=".55"/>`;

export function animalSprite(type,x,y,scale,t,{walk=0,talk=0,head=0,opacity=1,bow=0,facing='left'}={}) {
  const fox=type==='fox', prefix=fox?'f':'t';
  const anchor=fox?[800,450]:[1500,400], factor=scale*.44;
  const headPath=fox?'M880 235H1110V435L987 570L906 567L893 481L862 410Z':'M1642 210H1920V548L1786 562L1715 511L1640 442Z';
  const hp=fox?[923,442]:[1666,435];
  const tailPath=fox?'M442 300H682L680 426L642 488L626 583L578 668H440Z':'M1130 220H1357V371L1292 424L1270 465L1196 480L1130 412Z';
  const tp=fox?[608,610]:[1248,440];
  const legs=fox?[
    {path:'M687 482L772 482L758 602L733 659L736 721L779 745L780 779H691L680 717L685 654L692 586Z',p:[756,470],sign:-1},
    {path:'M937 530H983L977 642L990 727L1004 752V781H944L931 718L925 643Z',p:[961,550],sign:1},
    {path:'M692 533L743 551L688 632L671 664L663 717L677 747V781H612L607 748L614 700L627 647Z',p:[704,565],sign:1},
    {path:'M883 525H937L926 648L927 723L948 751V781H866L861 747L872 701L878 645Z',p:[914,550],sign:-1}
  ]:[
    {path:'M1324 484L1420 505L1393 629L1382 671L1409 717L1454 739V786H1350L1327 747L1317 675L1300 607Z',p:[1316,435],sign:-1},
    {path:'M1692 491H1763L1745 629L1754 710L1797 743V789H1701L1678 733L1680 650Z',p:[1666,435],sign:1},
    {path:'M1205 534L1300 560L1269 647L1262 704L1297 739V792H1172L1161 749L1165 696L1177 629Z',p:[1248,440],sign:1},
    {path:'M1585 519L1673 542L1647 641L1651 704L1671 740V791H1560L1547 745L1554 686L1564 622Z',p:[1666,435],sign:-1}
  ];
  const a=(sign)=>walk*Math.sin(t*7.5+(sign<0?Math.PI:0))*5;
  const legLayers=legs.map((leg,i)=>segment(`${prefix}leg${i}`,leg.path,a(leg.sign),...leg.p));
  return `<g transform="translate(${x} ${y}) scale(${facing==='right'?factor:-factor} ${factor}) translate(${-anchor[0]} ${-anchor[1]})" opacity="${opacity}"><g transform="rotate(${bow*7} ${anchor[0]} 780)">
    ${rod(anchor[0],anchor[1]+15,anchor[0]+50,1150)}
    ${segment(prefix+'tail',tailPath,walk*Math.sin(t*3)*3,...tp)}
    ${legLayers.slice(0,2).join('')}
    ${body(prefix+'body',fox?[442,230,669,560]:[1130,210,790,590],[headPath,tailPath,...legs.map(l=>l.path)])}
    ${legLayers.slice(2).join('')}
    ${segment(prefix+'head',headPath,head+(talk?Math.sin(t*8)*1.8:0),...hp)}
  </g></g>`;
}

export function hostSprite(x,y,s,t,{talk=0,bow=0,gesture=0,opacity=1}={}) {
  const head='M55 0H337V222L263 247L181 232L48 260Z';
  const left='M181 218L218 248L171 351L143 405L133 444L87 496L70 550H0V430L64 400L112 299Z';
  const right='M277 316L322 327L392 393L445 443L444 493L411 489L351 452L295 418L280 383Z';
  const la=-gesture*4+Math.sin(t*2)*gesture*1.2, ra=gesture*4-Math.sin(t*2)*gesture*1.2;
  const point=(px,py,a,cx,cy)=>{const r=a*Math.PI/180;return [cx+(px-cx)*Math.cos(r)-(py-cy)*Math.sin(r),cy+(px-cx)*Math.sin(r)+(py-cy)*Math.cos(r)];};
  const l=point(28,495,la,196,245),r=point(420,465,ra,301,354);
  return `<g transform="translate(${x} ${y}) scale(${s*.36}) translate(-220 -120)" opacity="${opacity}"><g transform="${rotate(bow*13,220,760)}">
    ${rod(223,230,244,1150)}${rod(...l,-40,1150)}${rod(...r,490,1150)}
    ${body('hostbody',[0,0,445,819],[head,left,right])}
    ${segment('hostleft',left,la,196,245)}${segment('hostright',right,ra,301,354)}
    ${segment('hosthead',head,talk?Math.sin(t*7)*1.3:0,224,217)}
  </g></g>`;
}
