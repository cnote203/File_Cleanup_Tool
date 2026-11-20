/* ===== Map views: "Web" (animated bubbles) and "Structure" (cards) =====
   Inlined into explorer.html at build time. Runs inside the explorer's closure,
   so it shares S, select(), myEff(), visible(), fmtN(), fmtSize(), esc(), $(). */
const MAP={motion:0.5,settle:20,cardPos:null,drag:null,cdrag:null,mode:'current',metric:'files',paused:false,sim:null,sig:'',raf:0,hover:null,sel:null,w:0,h:0,dpr:1,col:null,ro:null,model:null,last:0,down:null};
window.__folderMap=MAP; /* exposed for the browser test */
const REDUCE=!!(window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches);
if(REDUCE) MAP.paused=true;
const PALETTE=['#2dd4bf','#60a5fa','#c084fc','#fbbf24','#fb7185','#a3e635','#38bdf8','#fb923c','#818cf8','#94a3b8'];
const hexRgb=h=>[parseInt(h.slice(1,3),16),parseInt(h.slice(3,5),16),parseInt(h.slice(5,7),16)];
const rgbaC=(c,a)=>`rgba(${c[0]},${c[1]},${c[2]},${a})`;

/* where would a file land if every decision were applied? null = deleted */
function plannedPath(n){
  const e=myEff(n);
  if(!e) return n.path;
  if(e.d==='delete') return null;
  if(e.d==='archive') return (S.archiveRoot||'Archive')+SEP+n.path;
  if(e.d==='move'){
    const anc=e.from||n;
    const rel=n.path.slice(anc.parent&&anc.parent.path?anc.parent.path.length+1:0);
    return (e.dest?e.dest+SEP:'')+rel;
  }
  return n.path;
}
function buildMapTree(){
  const mk=(name,path)=>({name,path,files:0,size:0,direct:0,dsize:0,kids:new Map()});
  const root=mk('','');let removed=0;
  for(const f of S.nodes){
    if(f.isFolder||!visible(f)) continue;
    const p=MAP.mode==='after'?plannedPath(f):MAP.mode==='plan'?(S.plan&&S.plan.has(f.path)?S.plan.get(f.path):null):f.path;
    if(p===null){removed++;continue}
    const segs=p.split(SEP);let cur=root;
    cur.files++;cur.size+=f.size;
    for(let i=0;i<segs.length-1;i++){
      let c=cur.kids.get(segs[i]);
      if(!c){c=mk(segs[i],cur.path?cur.path+SEP+segs[i]:segs[i]);cur.kids.set(segs[i],c)}
      c.files++;c.size+=f.size;cur=c;
    }
    cur.direct++;cur.dsize+=f.size;
  }
  root.removed=removed;
  return root;
}
const mval=t=>MAP.metric==='size'?t.size:t.files;
const mtext=t=>MAP.metric==='size'?fmtSize(t.size):fmtN(t.files)+(t.files===1?' file':' files');
function mapModel(){
  const root=buildMapTree();
  const byVal=(a,b)=>mval(b)-mval(a)||a.name.localeCompare(b.name);
  const nodeOf=p=>MAP.mode==='current'?(S.byPath.get(p)||null):null;
  const subOf=k=>({id:'s:'+k.path,name:k.name,path:k.path,t:k,node:nodeOf(k.path)});
  const hubFor=(t,idx)=>{
    const kids=[...t.kids.values()].sort(byVal);
    const show=kids.slice(0,10),rest=kids.slice(10);
    const subs=show.map(subOf);
    if(rest.length) subs.push({id:'m:'+t.path,name:rest.length+' more folders',path:null,t:{files:rest.reduce((a,k)=>a+k.files,0),size:rest.reduce((a,k)=>a+k.size,0)},virtual:true});
    if(t.direct>0) subs.push({id:'d:'+t.path,name:'(files in this folder)',path:null,t:{files:t.direct,size:t.dsize},virtual:true});
    return {id:'h:'+t.path,name:t.name,path:t.path,t,node:nodeOf(t.path),subs,color:hexRgb(PALETTE[idx%PALETTE.length])};
  };
  const tops=[...root.kids.values()].sort(byVal);
  const MAXH=9;
  let head=tops,tail=[];
  if(tops.length>MAXH+1){head=tops.slice(0,MAXH);tail=tops.slice(MAXH)}
  const hubs=head.map(hubFor);
  if(tail.length){
    const t={name:'Other folders ('+tail.length+')',path:'\u0000other',files:tail.reduce((a,k)=>a+k.files,0),size:tail.reduce((a,k)=>a+k.size,0),direct:0,dsize:0,kids:new Map(tail.map(k=>[k.name,k]))};
    const h=hubFor(t,hubs.length);h.virtual=true;h.node=null;hubs.push(h);
  }
  if(root.direct>0){
    const t={name:'Files at the top level',path:'\u0000top',files:root.direct,size:root.dsize,direct:0,dsize:0,kids:new Map()};
    const h=hubFor(t,hubs.length);h.virtual=true;h.node=null;hubs.push(h);
  }
  return {hubs,total:root.files,removed:root.removed};
}

/* ---------- plan loader (old path -> new path) ---------- */
S.plan=null;
function loadPlan(text){
  const rows=parseCSV(text);if(!rows.length) return 0;
  const head=rows.shift().map(h=>h.trim().toLowerCase());
  const iO=Math.max(head.indexOf('old_path'),head.indexOf('path')),iN=head.indexOf('new_path'),iA=head.indexOf('action'),iT=head.indexOf('type');
  if(iO<0||iN<0){toast('The plan CSV needs old_path (or path) and new_path columns');return 0}
  const m=new Map();
  for(const r of rows){
    const old=(r[iO]||'').trim();if(!old) continue;
    if(iT>=0&&(r[iT]||'').trim()==='folder') continue;
    const act=iA>=0?(r[iA]||'').trim().toLowerCase():'move';
    if(!['move','archive','keep'].includes(act)) continue;
    const nw=(r[iN]||'').trim()||(act==='keep'?old:'');
    if(nw) m.set(old,nw);
  }
  S.plan=m;return m.size;
}
if(window.__PLAN_CSV__&&loadPlan(window.__PLAN_CSV__)){MAP.mode='plan';S.tab='structure'}

/* ---------- shared bar ---------- */
function mapBarHtml(web){
  const b=(attr,val,cur,label)=>`<button class="segb" ${attr}="${val}" aria-pressed="${cur===val}">${label}</button>`;
  return `<div class="mapbar">
    <div class="seg" role="group" aria-label="Layout"><span class="segl">Layout</span>${b('data-mapmode','current',MAP.mode,'Current folders')}${b('data-mapmode','after',MAP.mode,'After my decisions')}${S.plan?b('data-mapmode','plan',MAP.mode,'Loaded plan'):''}<button class="segb" id="planLoad" title="Load a mapping or action-plan CSV that has old and new paths">Load plan CSV</button></div>
    <div class="seg" role="group" aria-label="Size circles by"><span class="segl">Size by</span>${b('data-mapmetric','files',MAP.metric,'Files')}${b('data-mapmetric','size',MAP.metric,'Disk size')}</div>
    ${web?`<span class="spacer"></span><label class="seg motion"><span class="segl">Motion</span><input type="range" id="webMotion" min="0" max="100" step="1" value="${Math.round(MAP.motion*100)}" aria-label="Bubble motion, from still to lively"></label><button class="btn" id="webPause">${MAP.paused?'Resume motion':'Pause motion'}</button><button class="btn" id="webShake">Shake</button>`:''}
  </div>`;
}

/* ---------- structure (cards) ---------- */
function renderStructureTab(){
  const m=mapModel();
  let h=mapBarHtml(false);
  if(MAP.mode==='plan') h+=`<p class="small mapnote">Layout from the loaded plan (${fmtN(S.plan.size)} files placed). ${m.removed?fmtN(m.removed)+' files are not in the plan, for example duplicates or deletions.':''}</p>`;
  if(MAP.mode==='after') h+=`<p class="small mapnote">Where files would land if every one of your decisions were applied.${m.removed?` ${fmtN(m.removed)} files marked Delete are left out.`:''} Undecided files stay where they are.</p>`;
  if(!m.hubs.length){$('tabBody').innerHTML=h+'<p class="small">No files to show.</p>';return}
  h+='<div class="cards">';
  m.hubs.forEach(hb=>{
    const c=hb.color,max=Math.max(1,...hb.subs.map(s=>mval(s.t)));
    const head=`<span class="cname">${esc(hb.name)}</span><span class="ctot">${esc(mtext(hb.t))}</span>`;
    h+=`<div class="ccard"><${hb.node?'button':'div'} class="chead" style="background:${rgbaC(c,0.92)}" ${hb.node?`data-mapnode="${esc(hb.path)}"`:''}>${head}</${hb.node?'button':'div'}><div class="crows">`;
    hb.subs.forEach(s=>{
      const w=Math.max(2,Math.round(mval(s.t)/max*100));
      const inner=`<span class="crow-top"><span class="cn">${esc(s.name)}</span><span class="cv">${esc(mtext(s.t))}</span></span><span class="cbar"><i style="width:${w}%;background:${rgbaC(c,1)}"></i></span>`;
      h+=s.node?`<button class="crow" data-mapnode="${esc(s.path)}">${inner}</button>`:`<div class="crow plain">${inner}</div>`;
    });
    h+='</div></div>';
  });
  $('tabBody').innerHTML=h+'</div>';
}

/* ---------- web (bubbles) ---------- */
function themeColors(){
  const cs=getComputedStyle(document.documentElement),g=k=>cs.getPropertyValue(k).trim();
  MAP.col={ink:g('--ink'),ink2:g('--ink2'),panel:g('--panel'),line:g('--line'),line2:g('--line2'),accent:g('--accent'),
    keep:g('--keep'),archive:g('--archive'),delete:g('--delete'),move:g('--move'),discuss:g('--discuss'),font:getComputedStyle(document.body).fontFamily};
}
function renderWebTab(){
  if(!$('webCanvas')){
    $('tabBody').innerHTML=`<div class="webroot">${mapBarHtml(true)}<div class="webwrap" id="webWrap"><canvas id="webCanvas" tabindex="-1" role="img" aria-label="Animated map of folders as circles sized by content. The Structure tab shows the same information as a list."></canvas><div class="webcard" id="webCard" hidden></div></div></div>`;
    webAttach();
  }else{
    document.querySelectorAll('#tabBody [data-mapmode],#tabBody [data-mapmetric]').forEach(b=>{
      const on=b.dataset.mapmode?b.dataset.mapmode===MAP.mode:b.dataset.mapmetric===MAP.metric;
      b.setAttribute('aria-pressed',on);
    });
  }
  themeColors();
  webSync();
}
function webStop(){if(MAP.raf){cancelAnimationFrame(MAP.raf);MAP.raf=0}if(MAP.ro){MAP.ro.disconnect();MAP.ro=null}}
function webAttach(){
  const wrap=$('webWrap'),cv=$('webCanvas');
  const size=()=>{
    const r=wrap.getBoundingClientRect();
    const w=Math.max(320,Math.floor(r.width)),h=Math.max(320,Math.floor(r.height));
    MAP.dpr=window.devicePixelRatio||1;
    const ow=MAP.w,oh=MAP.h,changed=w!==ow||h!==oh;MAP.w=w;MAP.h=h;
    cv.width=Math.round(w*MAP.dpr);cv.height=Math.round(h*MAP.dpr);cv.style.width=w+'px';cv.style.height=h+'px';
    if(changed&&MAP.sim&&ow) webRescale(ow,oh);
    webDraw();
  };
  size();
  MAP.ro=new ResizeObserver(size);MAP.ro.observe(wrap);
  cv.style.touchAction='none';
  cv.addEventListener('pointermove',e=>{
    const p=webPt(e),d=MAP.drag;
    if(d){
      if(!d.moved&&d.n&&Math.hypot(e.clientX-d.sx,e.clientY-d.sy)>5){d.moved=true;d.n.pinned=true;cv.style.cursor='grabbing';webLoop()}
      if(d.moved){
        const n=d.n;
        n.x=Math.max(n.r+4,Math.min(MAP.w-n.r-4,p.x-d.ox));n.y=Math.max(n.r+4,Math.min(MAP.h-n.r-4,p.y-d.oy));
        n.vx=0;n.vy=0;if(n.kind==='hub'){n.ax=n.x;n.ay=n.y}
        d.vx=(p.x-d.lx);d.vy=(p.y-d.ly);d.lx=p.x;d.ly=p.y;
      }
      return;
    }
    const b=webHit(p.x,p.y),id=b?b.id:null;
    if(id!==MAP.hover){MAP.hover=id;cv.style.cursor=b?'grab':'default';if(MAP.paused) webDraw()}
  });
  cv.addEventListener('pointerleave',()=>{if(MAP.hover&&!MAP.drag){MAP.hover=null;if(MAP.paused) webDraw()}});
  cv.addEventListener('pointerdown',e=>{
    const p=webPt(e),b=webHit(p.x,p.y);
    MAP.drag={n:b,sx:e.clientX,sy:e.clientY,ox:b?p.x-b.x:0,oy:b?p.y-b.y:0,moved:false,lx:p.x,ly:p.y,vx:0,vy:0};
    cv.setPointerCapture(e.pointerId);
  });
  const endDrag=(e,cancel)=>{
    const d=MAP.drag;MAP.drag=null;if(!d) return;
    if(d.moved){
      const n=d.n;n.pinned=false;n.vx=d.vx*0.5;n.vy=d.vy*0.5;
      if(n.kind==='hub'){n.ax=n.x;n.ay=n.y}
      cv.style.cursor='grab';MAP.settle=20;webLoop();return;
    }
    if(cancel) return;
    const p=webPt(e);webPick(webHit(p.x,p.y));
  };
  cv.addEventListener('pointerup',e=>endDrag(e,false));
  cv.addEventListener('pointercancel',e=>endDrag(e,true));

  /* the detail card can be dragged by its title bar */
  const card=$('webCard');
  const place=(x,y)=>{
    const cr=card.getBoundingClientRect(),wr=wrap.getBoundingClientRect();
    x=Math.max(0,Math.min(wr.width-cr.width,x));y=Math.max(0,Math.min(wr.height-cr.height,y));
    MAP.cardPos={x,y};card.style.left=x+'px';card.style.top=y+'px';card.style.bottom='auto';
  };
  card.addEventListener('pointerdown',e=>{
    if(!e.target.closest('.wc-head')||e.target.closest('[data-wcclose]')) return;
    const cr=card.getBoundingClientRect();MAP.cdrag={dx:e.clientX-cr.left,dy:e.clientY-cr.top};
    card.setPointerCapture(e.pointerId);e.preventDefault();
  });
  card.addEventListener('pointermove',e=>{
    if(!MAP.cdrag) return;
    const wr=wrap.getBoundingClientRect();place(e.clientX-wr.left-MAP.cdrag.dx,e.clientY-wr.top-MAP.cdrag.dy);
    if(MAP.paused) webDraw();
  });
  const cardUp=()=>{MAP.cdrag=null};
  card.addEventListener('pointerup',cardUp);card.addEventListener('pointercancel',cardUp);
}
function webPt(e){const r=$('webCanvas').getBoundingClientRect();return {x:e.clientX-r.left,y:e.clientY-r.top}}
function webHit(x,y){
  const N=MAP.sim?MAP.sim.nodes:[];
  for(let pass=0;pass<2;pass++){
    for(let i=N.length-1;i>=0;i--){
      const n=N[i];if((pass===0)!==(n.kind==='sub')) continue;
      if(Math.hypot(x-n.x,y-n.y)<=n.r*(n.id===MAP.sel?1.12:1)+2) return n;
    }
  }
  return null;
}
function webPick(b){
  if(!b){
    MAP.sel=null;
    if(MAP.mode==='current'&&S.selected!==S.root) select(S.root);else{webCard();webDraw()}
    return;
  }
  if(MAP.mode==='current'&&b.node){MAP.sel=b.id;select(b.node,{})}
  else{MAP.sel=b.id;webCard();webDraw()}
}
function webSig(){
  return [MAP.mode,MAP.metric,S.nodes.length,S.showSystem,S.datasetName,MAP.mode==='after'?(S.archiveRoot||'')+'|'+JSON.stringify(S.mine):MAP.mode==='plan'?'plan'+(S.plan?S.plan.size:0):''].join('~');
}
function webSync(){
  const sig=webSig();
  if(sig!==MAP.sig||!MAP.sim){
    MAP.sig=sig;MAP.model=mapModel();
    webBuild();
  }
  /* mirror the tree selection onto the deepest matching bubble */
  if(MAP.mode==='current'&&S.selected&&S.selected!==S.root){
    let best=null;
    for(const n of MAP.sim.nodes){
      if(!n.node) continue;
      const p=n.path;
      if(S.selected.path===p||S.selected.path.startsWith(p+SEP)){if(!best||p.length>best.path.length) best=n}
    }
    MAP.sel=best?best.id:null;
  }else if(MAP.mode==='current') MAP.sel=null;
  webCard();
  MAP.settle=20;webLoop();
}
function webStop2(){if(MAP.raf){cancelAnimationFrame(MAP.raf);MAP.raf=0}}
function webBuild(){
  const w=MAP.w,h=MAP.h,hubsM=MAP.model.hubs;
  const prev=new Map();if(MAP.sim) MAP.sim.nodes.forEach(n=>prev.set(n.id,{x:n.x/ w,y:n.y/h}));
  const u=Math.max(0.55,Math.min(w,h)/880);
  const maxH=Math.max(1e-9,...hubsM.map(x=>mval(x.t)));
  const maxS=Math.max(1e-9,...hubsM.flatMap(x=>x.subs.map(s=>mval(s.t))));
  let seed=11;const rnd=()=>{seed=(seed*16807)%2147483647;return seed/2147483647};
  const nodes=[],byId={},cx=w/2,cy=h/2,H=hubsM.length;
  hubsM.forEach((hb,i)=>{
    const ang=-Math.PI/2+i*2*Math.PI/Math.max(H,1);
    const rx=H===1?0:w*0.36,ry=H===1?0:h*0.34;
    const hub={id:hb.id,kind:'hub',hub:hb.id,name:hb.name,path:hb.path,node:hb.node,t:hb.t,color:hb.color,
      r:u*(36+36*Math.sqrt(mval(hb.t)/maxH)),ax:cx+rx*Math.cos(ang),ay:cy+ry*Math.sin(ang),m:6,ph:rnd()*6.28,vx:0,vy:0,virtual:!!hb.virtual};
    const pv=prev.get(hub.id);hub.x=pv?pv.x*w:hub.ax;hub.y=pv?pv.y*h:hub.ay;
    nodes.push(hub);byId[hub.id]=hub;
    hb.subs.forEach(s=>{
      const a=rnd()*6.28,r=u*(9+36*Math.sqrt(mval(s.t)/maxS));
      const n={id:s.id,kind:'sub',hub:hb.id,name:s.name,path:s.path,node:s.node,t:s.t,color:hb.color,r,m:1+r/(20*u),ph:rnd()*6.28,vx:0,vy:0,virtual:!!s.virtual};
      const ps=prev.get(n.id);n.x=ps?ps.x*w:hub.x+Math.cos(a)*(hub.r+70*u);n.y=ps?ps.y*h:hub.y+Math.sin(a)*(hub.r+70*u);
      nodes.push(n);byId[n.id]=n;
    });
  });
  /* shrink everything when the map is crowded, so clusters keep clear of each other */
  const area=nodes.reduce((a,n)=>a+Math.PI*n.r*n.r,0),k=Math.min(1,Math.sqrt(0.17*w*h/Math.max(area,1)));
  nodes.forEach(n=>{n.r=Math.max(n.kind==='hub'?46:7,n.r*k);if(n.kind==='sub') n.m=1+n.r/(20*u)});
  const radii=nodes.filter(n=>n.kind==='sub').map(n=>n.r).sort((a,b)=>b-a);
  MAP.sim={nodes,byId,t:0,u:u*Math.max(k,0.55),rnd,labelR:radii[Math.min(13,radii.length-1)]||0};
  if(MAP.hover&&!byId[MAP.hover]) MAP.hover=null;
  for(let i=0;i<(prev.size?80:500);i++) webStep(1);
}
function webRescale(ow,oh){
  if(!MAP.sim) return;
  const kx=MAP.w/ow,ky=MAP.h/oh;MAP.sim.nodes.forEach(n=>{n.x*=kx;n.y*=ky});
  webBuild();
}
function webStep(dt){
  const S2=MAP.sim,N=S2.nodes,u=S2.u,w=MAP.w,h=MAP.h,cx=w/2,cy=h/2,MF=MAP.motion*2; /* 0 = still, 1 = default, 2 = lively */
  S2.t+=dt/60;
  for(const n of N){n.fx=0;n.fy=0}
  for(const n of N){
    if(n.kind==='hub'){
      const tx=n.id===MAP.sel?cx:n.ax,ty=n.id===MAP.sel?cy:n.ay;
      n.fx+=(tx-n.x)*0.006;n.fy+=(ty-n.y)*0.006;
    }else{
      const hb=S2.byId[n.hub],dx=n.x-hb.x,dy=n.y-hb.y,d=Math.sqrt(dx*dx+dy*dy)||1,L=hb.r+n.r+34*u,f=(d-L)*0.012;
      n.fx-=f*dx/d;n.fy-=f*dy/d;hb.fx+=f*dx/d*0.08;hb.fy+=f*dy/d*0.08;
      if(n.id===MAP.sel){n.fx+=(cx-n.x)*0.004;n.fy+=(cy-n.y)*0.004}
    }
    n.fx+=Math.sin(S2.t*0.5+n.ph)*0.010*MF;n.fy+=Math.cos(S2.t*0.4+n.ph*1.7)*0.010*MF;
  }
  for(let i=0;i<N.length;i++)for(let j=i+1;j<N.length;j++){
    const a=N[i],b=N[j],dx=b.x-a.x,dy=b.y-a.y,d2=dx*dx+dy*dy,min=a.r+b.r+(a.hub===b.hub?10:46)*u;
    if(d2<min*min){
      const d=Math.sqrt(d2)||0.01,o=min-d,nx=dx/d,ny=dy/d,ma=a.pinned?1e6:a.m,mb=b.pinned?1e6:b.m,tm=ma+mb;
      a.x-=nx*o*0.5*mb/tm;a.y-=ny*o*0.5*mb/tm;b.x+=nx*o*0.5*ma/tm;b.y+=ny*o*0.5*ma/tm;
      a.vx-=nx*o*0.010*MF*mb/tm;a.vy-=ny*o*0.010*MF*mb/tm;b.vx+=nx*o*0.010*MF*ma/tm;b.vy+=ny*o*0.010*MF*ma/tm;
    }
  }
  for(const n of N){
    if(n.pinned){n.vx=0;n.vy=0;continue}
    n.vx=(n.vx+n.fx/n.m)*0.88;n.vy=(n.vy+n.fy/n.m)*0.88;n.x+=n.vx*dt;n.y+=n.vy*dt;
    const pad=n.r+8;
    if(n.x<pad){n.x=pad;n.vx=Math.abs(n.vx)*0.5}
    if(n.x>w-pad){n.x=w-pad;n.vx=-Math.abs(n.vx)*0.5}
    if(n.y<pad){n.y=pad;n.vy=Math.abs(n.vy)*0.5}
    if(n.y>h-pad){n.y=h-pad;n.vy=-Math.abs(n.vy)*0.5}
  }
}
function webLoop(){
  if(MAP.raf) return;
  MAP.last=performance.now();
  const tick=now=>{
    if(!$('webCanvas')||S.tab!=='web'){MAP.raf=0;return}
    const dt=Math.min(2,(now-MAP.last)/16.667);MAP.last=now;
    if(MAP.paused&&!MAP.drag){webDraw();if(--MAP.settle<=0){MAP.raf=0;return}}
    else{webStep(dt);webDraw()}
    MAP.raf=requestAnimationFrame(tick);
  };
  MAP.raf=requestAnimationFrame(tick);
}
function decCol(n){
  if(MAP.mode!=='current'||!n.node) return null;
  const e=myEff(n.node);return e?MAP.col[e.d]:null;
}
function wrapLines(ctx,text,maxW,maxLines){
  const words=text.split(/\s+/),lines=[];let cur='';
  for(const w of words){
    const t=cur?cur+' '+w:w;
    if(ctx.measureText(t).width<=maxW||!cur) cur=t;else{lines.push(cur);cur=w}
  }
  if(cur) lines.push(cur);
  if(lines.length>maxLines){lines.length=maxLines;lines[maxLines-1]=lines[maxLines-1].replace(/.{0,2}$/,'')+'…'}
  return lines.map(l=>{while(ctx.measureText(l).width>maxW&&l.length>3) l=l.slice(0,-2)+'…';return l});
}
function webDraw(){
  const cv=$('webCanvas');if(!cv||!MAP.sim||!MAP.col) return;
  const ctx=cv.getContext('2d'),w=MAP.w,h=MAP.h,C=MAP.col,S2=MAP.sim,N=S2.nodes;
  ctx.setTransform(MAP.dpr,0,0,MAP.dpr,0,0);
  ctx.clearRect(0,0,w,h);ctx.fillStyle=C.panel;ctx.fillRect(0,0,w,h);
  const selNode=MAP.sel?S2.byId[MAP.sel]:null,fam=n=>!selNode||n.id===selNode.id||n.hub===selNode.hub&&(selNode.kind==='hub'||n.kind==='hub');
  const cx=w/2,cy=h/2;
  ctx.lineWidth=1;ctx.strokeStyle=C.line2;
  [0.16,0.33,0.5].forEach(k=>{ctx.beginPath();ctx.arc(cx,cy,Math.min(w,h)*k*1.05,0,6.2832);ctx.stroke()});
  const hubs=N.filter(n=>n.kind==='hub');
  ctx.globalAlpha=selNode?0.35:1;ctx.strokeStyle=C.line;
  hubs.forEach((a,i)=>{
    const b=hubs[(i+1)%hubs.length];
    ctx.setLineDash([5,5]);ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();
    ctx.setLineDash([]);ctx.beginPath();ctx.moveTo(cx,cy);ctx.lineTo(a.x,a.y);ctx.stroke();
  });
  ctx.globalAlpha=1;ctx.setLineDash([]);
  for(const n of N){
    if(n.kind!=='sub') continue;
    const hb=S2.byId[n.hub];ctx.globalAlpha=fam(n)?1:0.15;
    ctx.strokeStyle=rgbaC(n.color,0.6);ctx.lineWidth=1.5;ctx.beginPath();ctx.moveTo(hb.x,hb.y);ctx.lineTo(n.x,n.y);ctx.stroke();
  }
  const font=C.font||'system-ui,sans-serif';
  for(const n of N){
    ctx.globalAlpha=fam(n)?1:0.2;
    const sc=n.id===MAP.sel?1.12:1,r=n.r*sc;
    ctx.beginPath();ctx.arc(n.x,n.y,r,0,6.2832);
    ctx.fillStyle=rgbaC(n.color,n.kind==='hub'?0.92:0.5);ctx.fill();
    ctx.lineWidth=2;ctx.strokeStyle=rgbaC(n.color,1);ctx.stroke();
    if(MAP.hover===n.id){ctx.fillStyle='rgba(255,255,255,0.22)';ctx.fill()}
    const dc=decCol(n);
    if(dc){ctx.beginPath();ctx.arc(n.x,n.y,r+4,0,6.2832);ctx.lineWidth=3;ctx.strokeStyle=dc;ctx.stroke()}
    if(n.id===MAP.sel){ctx.beginPath();ctx.arc(n.x,n.y,r+(dc?9:5),0,6.2832);ctx.lineWidth=2;ctx.strokeStyle=C.accent;ctx.stroke()}
    if(n.kind==='hub'){
      const fs=Math.max(10.5,Math.min(14,r*0.2));
      ctx.font=`600 ${fs}px ${font}`;ctx.fillStyle='#0b1220';ctx.textAlign='center';ctx.textBaseline='middle';
      const lines=wrapLines(ctx,n.name,r*1.8,4);
      const sub=mtext(n.t),total=(lines.length+1)*(fs+2);
      let y=n.y-total/2+(fs+2)/2;
      lines.forEach(l=>{ctx.fillText(l,n.x,y);y+=fs+2});
      ctx.font=`500 ${Math.max(10,fs-1)}px ${font}`;ctx.fillText(sub,n.x,y);
    }
  }
  /* labels: placed largest first on a free side of their circle; hidden (faded) when no clear spot exists */
  ctx.textBaseline='middle';ctx.lineJoin='round';
  const placed=[],card=$('webCard');
  if(card&&!card.hidden){
    const wr=$('webWrap').getBoundingClientRect(),cr=card.getBoundingClientRect();
    placed.push({x:cr.left-wr.left-4,y:cr.top-wr.top-4,w:cr.width+8,h:cr.height+8});
  }
  const hitRC=(rc,c)=>{const px=Math.max(rc.x,Math.min(c.x,rc.x+rc.w)),py=Math.max(rc.y,Math.min(c.y,rc.y+rc.h));return Math.hypot(px-c.x,py-c.y)<c.r+3};
  const hitRR=(a,b)=>a.x<b.x+b.w+3&&a.x+a.w+3>b.x&&a.y<b.y+b.h+3&&a.y+a.h+3>b.y;
  const order=N.filter(n=>n.kind==='sub').sort((a,b)=>((b.id===MAP.sel||b.id===MAP.hover)-(a.id===MAP.sel||a.id===MAP.hover))||b.r-a.r);
  for(const n of order){
    const focus=n.id===MAP.sel||n.id===MAP.hover||(selNode&&n.hub===selNode.hub);
    const label=n.name.length>30?n.name.slice(0,29)+'…':n.name,cnt=mtext(n.t);
    ctx.font=`500 12px ${font}`;const w1=ctx.measureText(label).width;
    ctx.font=`400 11px ${font}`;const w2=ctx.measureText(cnt).width;
    const lw=w1+w2+8,lh=18,r=n.r*(n.id===MAP.sel?1.12:1),hb=S2.byId[n.hub];
    const right={x:n.x+r+7,y:n.y-9},left={x:n.x-r-7-lw,y:n.y-9},top={x:n.x-lw/2,y:n.y-r-6-lh},bot={x:n.x-lw/2,y:n.y+r+6};
    const pref=n.x>=hb.x?[right,left,top,bot]:[left,right,top,bot];
    const cands=n.lside!==undefined?[[right,left,top,bot][n.lside]].concat(pref):pref;
    let pick=null;
    for(const c of cands){
      const rc={x:c.x,y:c.y,w:lw,h:lh};
      if(rc.x<4||rc.y<4||rc.x+lw>w-4||rc.y+lh>h-4) continue;
      if(placed.some(q=>hitRR(rc,q))) continue;
      if(N.some(o=>o!==n&&hitRC(rc,o))) continue;
      pick=rc;n.lside=[right,left,top,bot].indexOf(c);break;
    }
    let vis=!!pick&&!(selNode&&!fam(n)&&!focus);
    if(!pick&&focus){const c=cands[0];pick={x:Math.max(4,Math.min(w-lw-4,c.x)),y:Math.max(4,Math.min(h-lh-4,c.y)),w:lw,h:lh};vis=true}
    if(pick&&vis){n.lrc=pick;placed.push(pick)}
    n.la=(n.la||0)+((vis?1:0)-(n.la||0))*0.25;
    if(!n.lrc||n.la<0.03) continue;
    ctx.globalAlpha=n.la*(fam(n)?1:0.25);
    const x=n.lrc.x,y=n.lrc.y+lh/2;ctx.textAlign='left';
    ctx.font=`500 12px ${font}`;ctx.lineWidth=4;ctx.strokeStyle=C.panel;ctx.strokeText(label,x,y);ctx.fillStyle=C.ink;ctx.fillText(label,x,y);
    ctx.font=`400 11px ${font}`;ctx.strokeText(cnt,x+w1+8,y);ctx.fillStyle=C.ink2;ctx.fillText(cnt,x+w1+8,y);
  }
  ctx.globalAlpha=1;
}
function webCard(){
  const el=$('webCard');if(!el) return;
  const n=MAP.sel&&MAP.sim?MAP.sim.byId[MAP.sel]:null;
  if(!n){el.hidden=true;return}
  const hb=MAP.sim.byId[n.hub],parentVal=Math.max(1,mval(hb.t));
  const pct=n.kind==='sub'?Math.round(mval(n.t)/parentVal*100)+'% of '+esc(hb.name):'Top-level folder';
  const t=n.t,kids=t.kids?[...t.kids.values()].sort((a,b)=>mval(b)-mval(a)).slice(0,5):[];
  const mx=Math.max(1,...kids.map(mval));
  let h=`<div class="wc-head" title="Drag to move"><div class="wc-title">${esc(n.name)}</div><button class="wc-x" data-wcclose aria-label="Close details">×</button></div><div class="wc-sub">${pct}</div>
    <div class="wc-big">${esc(mtext(t))}</div>`;
  if(MAP.metric==='files'&&t.size!==undefined) h+=`<div class="wc-sub">${esc(fmtSize(t.size))} on disk</div>`;
  if(kids.length){
    h+='<div class="wc-h">Inside</div>';
    kids.forEach(k=>{h+=`<div class="wc-row"><span>${esc(k.name)}</span><b>${esc(mtext(k))}</b></div><div class="cbar"><i style="width:${Math.max(2,Math.round(mval(k)/mx*100))}%;background:${rgbaC(n.color,1)}"></i></div>`});
  }
  if(MAP.mode==='current'&&n.node) h+=`<button class="btn" data-webopen="${esc(n.path)}">Open in folder view</button>`;
  else if(MAP.mode==='current') h+='<div class="wc-sub">A group of items, not a single folder.</div>';
  el.innerHTML=h;el.hidden=false;
  if(MAP.cardPos){
    const wr=$('webWrap').getBoundingClientRect();
    const x=Math.max(0,Math.min(wr.width-el.offsetWidth,MAP.cardPos.x)),y=Math.max(0,Math.min(wr.height-el.offsetHeight,MAP.cardPos.y));
    el.style.left=x+'px';el.style.top=y+'px';el.style.bottom='auto';
  }else{el.style.left='10px';el.style.top='';el.style.bottom='10px'}
}

/* ---------- events for both map tabs ---------- */
$('filePlan').addEventListener('change',async e=>{
  const f=e.target.files[0];e.target.value='';if(!f) return;
  const n=loadPlan(await f.text());
  if(n){MAP.mode='plan';MAP.sel=null;renderTab();toast(n+' files placed by the loaded plan')}
});
$('tabBody').addEventListener('input',e=>{
  if(e.target.id!=='webMotion') return;
  MAP.motion=Math.max(0,Math.min(1,e.target.value/100));
  if(MAP.paused){MAP.paused=false;const b=$('webPause');if(b) b.textContent='Pause motion'}
  webLoop();
});
$('tabBody').addEventListener('click',e=>{
  if(e.target.id==='planLoad'){$('filePlan').click();return}
  const mm=e.target.closest('[data-mapmode]');
  if(mm){MAP.mode=mm.dataset.mapmode;MAP.sel=null;renderTab();return}
  const mt=e.target.closest('[data-mapmetric]');
  if(mt){MAP.metric=mt.dataset.mapmetric;renderTab();return}
  const mn=e.target.closest('[data-mapnode]');
  if(mn){const n=S.byPath.get(mn.dataset.mapnode);if(n) select(n,{openFolder:true});return}
  if(e.target.closest('[data-wcclose]')){
    MAP.sel=null;
    if(MAP.mode==='current'&&S.selected!==S.root) select(S.root);else{webCard();webDraw()}
    return;
  }
  const wo=e.target.closest('[data-webopen]');
  if(wo){const n=S.byPath.get(wo.dataset.webopen);if(n) select(n,{openFolder:true,tab:'folder'});return}
  if(e.target.id==='webPause'){MAP.paused=!MAP.paused;e.target.textContent=MAP.paused?'Resume motion':'Pause motion';MAP.settle=20;webLoop();return}
  if(e.target.id==='webShake'&&MAP.sim){
    MAP.sim.nodes.forEach(n=>{n.vx+=(MAP.sim.rnd()-0.5)*6/n.m;n.vy+=(MAP.sim.rnd()-0.5)*6/n.m});
    if(MAP.paused&&!REDUCE){MAP.paused=false;const b=$('webPause');if(b) b.textContent='Pause motion';webLoop()}
    else if(REDUCE){for(let i=0;i<120;i++) webStep(1);webDraw()}
  }
});
if(window.matchMedia) window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>{themeColors();if($('webCanvas')) webDraw()});
