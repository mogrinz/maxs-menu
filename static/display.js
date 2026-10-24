(() => {
  'use strict';
  const screenId=document.body.dataset.screen,board=document.getElementById('board'),container=document.getElementById('items'),warning=document.getElementById('food-safety');
  const key='maxs-menu-v3-'+screenId+'-'+document.body.dataset.direct;let revision=null,rotation=0;
  const warningText='*CONSUMING RAW OR UNDERCOOKED MEATS, POULTRY, SEAFOOD, SHELLFISH, OR EGGS MAY INCREASE YOUR RISK OF FOODBORNE ILLNESS, ESPECIALLY IF YOU HAVE CERTAIN MEDICAL CONDITIONS.';
  function el(tag,className,text){const node=document.createElement(tag);if(className)node.className=className;if(text!==undefined)node.textContent=text;return node;}
  function fit(){
    const sideways=rotation===90||rotation===270;
    const width=sideways?innerHeight:innerWidth,height=sideways?innerWidth:innerHeight;
    board.style.width=(width*.94)+'px';board.style.height=(height*.95)+'px';
    board.style.padding=(height*.02)+'px '+(width*.03)+'px';
    board.style.transform='translate(-50%,-50%) rotate('+rotation+'deg)';
    let size=Math.min(64,Math.max(24,(rotation===90||rotation===270?innerWidth:innerHeight)*.05));
    function setSize(){board.style.setProperty('--type',size+'px');if(!warning.hidden){const nodes=container.querySelectorAll('.menu-header,.item-name,.item-price,.description,.menu-option');let smallest=Infinity;for(const node of nodes)if(node.textContent)smallest=Math.min(smallest,parseFloat(getComputedStyle(node).fontSize));warning.style.fontSize=(Number.isFinite(smallest)?smallest:size)+'px';}}
    setSize();while(container.scrollHeight>container.clientHeight+1&&size>12){size-=1;setSize();}
    board.dataset.fontSize=String(size);board.dataset.crowded=String(size<Math.max(18,innerHeight*.022));board.dataset.overflow=String(container.scrollHeight>container.clientHeight+1||warning.offsetHeight>board.clientHeight);
  }
  function render(data){
    if(!data||!data.content||typeof data.revision!=='string')return false;
    const screen=data.content;rotation=screen.rotation||0;document.body.dataset.menu=data.menu_id;board.dataset.rotation=String(rotation);
    document.body.dataset.theme=document.body.dataset.previewTheme||data.theme||'classic-bagel-shop';
    const fragment=document.createDocumentFragment();let layout='full',block=null,columns=[],headings=[];
    function start(next){layout=next;block=el('section','menu-section'+(layout==='two'?' two-columns':''));columns=layout==='two'?[el('div','menu-column'),el('div','menu-column')]:[block];headings=layout==='two'?[el('div','column-heading'),el('div','column-heading')]:[];if(layout==='two')block.append(...headings,...columns);fragment.append(block);}
    for(const item of screen.items){
      if(item.kind==='header'&&item.starts_section)start(item.layout);
      if(!item.available)continue;if(!block)start('full');
      const destination=layout==='two'?columns[item.column-1]:columns[0];
      if(item.kind==='header'){const heading=el('h2','menu-header',item.name);heading.dataset.entryId=item.id;const headingDestination=layout==='two'&&destination.children.length===0?headings[item.column-1]:destination;headingDestination.append(heading);}
      else if(item.kind==='option'){const option=el('div','menu-option',item.name);option.dataset.entryId=item.id;destination.append(option);}
      else{
        const wrapper=el('div','menu-item');wrapper.dataset.entryId=item.id;const row=el('div','item-row');row.append(el('span','item-name',item.name));
        if(item.price!==null&&item.price!==undefined&&String(item.price).trim()!==''&&Number.isFinite(Number(item.price))&&Number(item.price)>0)row.append(el('span','item-price','$'+Number(item.price).toFixed(2)));
        else row.classList.add('no-price');
        wrapper.append(row);if(item.description)wrapper.append(el('div','description',item.description));destination.append(wrapper);
      }
    }
    container.replaceChildren(fragment);warning.hidden=!screen.food_safety_warning;warning.textContent=warning.hidden?'':warningText;
    revision=data.revision;fit();if(document.fonts)document.fonts.ready.then(fit);return true;
  }
  try{render(JSON.parse(localStorage.getItem(key)));}catch(_){}
  async function refresh(){const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),4000);try{const response=await fetch('/api/display/'+screenId+(document.body.dataset.direct==='1'?'?direct=1':''),{cache:'no-store',signal:controller.signal});if(!response.ok)throw Error('Unavailable');const data=await response.json();if(data.revision!==revision&&render(data)){try{localStorage.setItem(key,JSON.stringify(data));}catch(_){}}board.dataset.connected='true';}catch(_){board.dataset.connected='false';}finally{clearTimeout(timer);setTimeout(refresh,5000);}}
  addEventListener('resize',fit);if(document.fonts)document.fonts.ready.then(fit);refresh();
})();
