/* Shared, offline currency formatting. Amounts are never converted. */
(() => {
  'use strict';
  const cache=new Map();
  window.MenuPricing={format(value,pricing={currency:'USD',locale:'en-US'}){
    const amount=Number(value);
    if(!Number.isFinite(amount)||amount<=0)return '';
    try{
      const key=pricing.locale+'/'+pricing.currency;
      if(!cache.has(key))cache.set(key,new Intl.NumberFormat(pricing.locale,{style:'currency',currency:pricing.currency}));
      return cache.get(key).format(amount);
    }catch(_){return (pricing.currency||'USD')+' '+amount.toFixed(2);}
  }};
})();
