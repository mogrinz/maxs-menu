(() => {
  'use strict';
  const api=window.MenuAPI, el=api.element, list=document.getElementById('history'), feedback=document.getElementById('history-status');
  const admin=['admin'].includes(document.body.dataset.role);
  let busy=false,revision;
  async function load(){
    try{
      const [data,current]=await Promise.all([api.request('/api/admin/history'),api.request('/api/admin/menu')]);revision=current.revision;
      list.replaceChildren();
      if(!data.history.length)list.append(el('p','History will appear after the first publish.'));
      for(const entry of data.history){
        const row=el('div',undefined,'history-row');
        row.append(el('span',new Date(entry.time).toLocaleString()+' · '+entry.actor+' · before '+entry.action));
        const actions=el('div',undefined,'history-actions');const download=el('a','Download');download.href='/api/admin/history/'+encodeURIComponent(entry.id)+'/download';download.setAttribute('download','');actions.append(download);if(admin){const button=el('button','Restore');button.type='button';button.addEventListener('click',async()=>{
          if(busy||!confirm('Restore this saved menu? This replaces the currently published items and prices.'))return;
          busy=true;button.disabled=true;
          try{await api.request('/api/admin/history/restore',{method:'POST',body:JSON.stringify({id:entry.id,revision})});api.feedback(feedback,'Previous menu restored. Connected displays will update automatically.');await load();}
          catch(error){api.feedback(feedback,error.message,true);}
          finally{busy=false;button.disabled=false;}
        });actions.append(button);}row.append(actions);list.append(row);
      }
    }catch(error){api.feedback(feedback,error.message,true);}
  }
  document.getElementById('load-history').addEventListener('click',load);load();
})();
