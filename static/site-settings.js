(() => {
  'use strict';
  const api=window.MenuAPI,input=document.getElementById('timezone'),save=document.getElementById('save-timezone'),status=document.getElementById('timezone-status');
  let revision,savedZone,dirty=false,busy=false;
  function clock(data){document.getElementById('system-clock').textContent='Pi clock: '+data.server_time;}
  async function load(){
    if(busy||(dirty&&!confirm('Discard the unsaved timezone change?')))return;
    try{const data=await api.request('/api/admin/system/settings');input.value=data.timezone;savedZone=data.timezone;revision=data.revision;dirty=false;clock(data);input.disabled=false;save.disabled=false;api.feedback(status,'Saved timezone loaded.');}
    catch(error){api.feedback(status,error.message,true);}
  }
  input.addEventListener('input',()=>{dirty=input.value!==savedZone;api.feedback(status,dirty?'Unsaved timezone. Save to update scheduling.':'Saved timezone selected.');});
  document.getElementById('timezone-form').addEventListener('submit',async event=>{
    event.preventDefault();if(busy||!revision)return;
    busy=true;input.disabled=true;save.disabled=true;
    try{const data=await api.request('/api/admin/system/settings',{method:'POST',body:JSON.stringify({timezone:input.value,revision})});savedZone=data.timezone;revision=data.revision;dirty=false;clock(data);api.feedback(status,'Timezone saved. Connected displays use the new schedule timezone within about 5 seconds.');}
    catch(error){api.feedback(status,error.message,true);}
    finally{busy=false;input.disabled=false;save.disabled=false;}
  });
  document.getElementById('reload-timezone').addEventListener('click',load);
  addEventListener('beforeunload',event=>{if(dirty){event.preventDefault();event.returnValue='';}});
  load();
})();
