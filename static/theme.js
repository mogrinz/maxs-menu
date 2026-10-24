(() => {
  'use strict';const api=window.MenuAPI,picker=document.getElementById('theme-picker'),screen=document.getElementById('theme-screen'),save=document.getElementById('save-theme'),status=document.getElementById('theme-status');
  let revision,savedTheme,dirty=false,busy=false;
  function preview(){document.getElementById('theme-preview').src='/display/'+screen.value+'?direct=1&theme='+encodeURIComponent(picker.value);document.getElementById('theme-description').textContent=({
'classic-bagel-shop':'Cream, forest green and copper, with traditional serif headings.',
'modern-minimalistic':'Black and white with Jost, a clean sans-serif font.',
'golden-chalk':'Charcoal with golden handwritten item names and white chalk descriptions.',
'coffeehouse-chalkboard':'Black chalkboard with white lettering and a subtle coffee illustration.',
'rose-cafe':'Blush pink with elegant uppercase serif lettering and spaced headings.',
'retro-diner':'Warm white with coral script headings and blue condensed lettering.',
'starlight-cafe':'Midnight navy, subtle stars and warm gold headings.',
'seaside-cafe':'Sand, sea blue and clean lettering.',
'autumn-harvest':'Warm cream, copper headings and rich brown lettering.',
'winter-hearth':'Deep blue-green, cream lettering and warm gold headings.',
'spring-garden':'Soft cream, leafy green and plum script headings.'})[picker.value]||'' ;}
  async function load(){if(busy)return;if(dirty&&!confirm('Discard the unsaved theme selection?'))return;try{const data=await api.request('/api/admin/theme');picker.value=data.theme;savedTheme=data.theme;revision=data.revision;dirty=false;picker.disabled=false;save.disabled=false;preview();api.feedback(status,'Saved theme loaded.');}catch(error){api.feedback(status,error.message,true);}}
  picker.addEventListener('change',()=>{dirty=picker.value!==savedTheme;preview();api.feedback(status,dirty?'Preview only. Save theme to update the displays.':'Saved theme selected.');});screen.addEventListener('change',preview);
  document.getElementById('reload-theme').addEventListener('click',load);
  document.getElementById('theme-form').addEventListener('submit',async event=>{event.preventDefault();if(busy||!revision)return;busy=true;save.disabled=true;picker.disabled=true;try{const data=await api.request('/api/admin/theme',{method:'POST',body:JSON.stringify({theme:picker.value,revision})});revision=data.revision;savedTheme=data.theme;dirty=false;api.feedback(status,data.message);}catch(error){api.feedback(status,error.message,true);}finally{busy=false;save.disabled=false;picker.disabled=false;}});
  addEventListener('beforeunload',event=>{if(dirty){event.preventDefault();event.returnValue='';}});load();
})();
