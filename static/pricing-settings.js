(() => {
  'use strict';
  const api=window.MenuAPI,currency=document.getElementById('currency'),locale=document.getElementById('price-locale'),
    status=document.getElementById('pricing-status'),save=document.getElementById('save-pricing');
  let revision,saved,dirty=false,busy=false;
  function value(){return {currency:currency.value,locale:locale.value};}
  function preview(){document.getElementById('pricing-preview').textContent='Example: '+window.MenuPricing.format(1234.5,value());}
  function enable(enabled){currency.disabled=!enabled;locale.disabled=!enabled;save.disabled=!enabled;}
  async function load(){
    if(busy||(dirty&&!confirm('Discard unsaved currency settings?')))return;
    try{const data=await api.request('/api/admin/system/pricing');currency.value=data.pricing.currency;locale.value=data.pricing.locale;revision=data.revision;saved=JSON.stringify(value());dirty=false;enable(true);preview();api.feedback(status,'Saved pricing settings loaded.');}
    catch(error){api.feedback(status,error.message,true);}
  }
  for(const input of [currency,locale])input.addEventListener('change',()=>{dirty=JSON.stringify(value())!==saved;preview();api.feedback(status,dirty?'Unsaved pricing settings.':'Saved pricing settings selected.');});
  document.getElementById('pricing-form').addEventListener('submit',async event=>{
    event.preventDefault();if(busy||!revision)return;busy=true;enable(false);
    try{const data=await api.request('/api/admin/system/pricing',{method:'POST',body:JSON.stringify({pricing:value(),revision})});revision=data.revision;saved=JSON.stringify(value());dirty=false;api.feedback(status,'Pricing settings saved. Connected displays update within about 5 seconds. Reload an open editor to update its price labels.');}
    catch(error){api.feedback(status,error.message,true);}
    finally{busy=false;enable(true);}
  });
  document.getElementById('reload-pricing').addEventListener('click',load);
  addEventListener('beforeunload',event=>{if(dirty){event.preventDefault();event.returnValue='';}});
  load();
})();
