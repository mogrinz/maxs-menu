(() => {
  'use strict';
  const api=window.MenuAPI, status=document.getElementById('network-status');
  const picker=document.getElementById('internet-profile'), password=document.getElementById('hotspot-password');
  const passwordStatus=document.getElementById('password-status');
  let state, busy=false, loading=false, savedPassword='', credentialsLoaded=false, scheduled=false;
  const port=location.port?':'+location.port:'';
  document.getElementById('reconnect-internet').textContent='Internet Wi-Fi: reconnect to your normal network and use this Pi’s hostname or its new IP address.';
  const dirty=()=>credentialsLoaded && password.value!==savedPassword;
  function controls(){
    if(!state)return;
    const locked=busy||scheduled||state.busy||!!state.pending;
    picker.disabled=locked||!state.internet_profiles.length;
    document.getElementById('enable-hotspot').disabled=locked||!state.hotspot_ready||state.mode==='hotspot'||!state.capabilities.hotspot_supported||!state.can_switch||!credentialsLoaded||dirty();
    document.getElementById('enable-internet').disabled=locked||!state.can_switch||!state.internet_profiles.length||picker.value===state.active_profile;
    document.getElementById('configure-hotspot').disabled=locked||state.mode==='hotspot'||!credentialsLoaded||!dirty();
    password.readOnly=locked||state.mode==='hotspot'||!credentialsLoaded;
    passwordStatus.textContent=!credentialsLoaded?'Loading saved password…':dirty()?'Unsaved password. Click Save password before switching.':state.hotspot_ready?'Password saved. You can switch to Menu Hotspot without saving it again.':'Enter a Wi-Fi password and click Save password before the first switch.';
    if(state.mode==='hotspot' && credentialsLoaded)passwordStatus.textContent='Password saved. Switch to Internet Wi-Fi before changing it.';
    document.getElementById('keep-network').disabled=busy || scheduled || state.busy || !state.pending?.active || state.pending?.remaining===0;
    document.getElementById('cancel-network').disabled=busy||scheduled||state.busy;
  }
  function draw(data){
    state=data;
    document.getElementById('hotspot-ssid').textContent=data.ssid;
    document.getElementById('reconnect-hotspot').textContent='Menu Hotspot: join '+data.ssid+', then open http://'+data.hotspot_address+port+'/system. SSH uses your Pi operating-system username at that address.';
    const caps=data.capabilities;
    document.getElementById('hotspot-panel').hidden=!caps.hotspot_supported;
    document.getElementById('wifi-panel').hidden=!caps.wifi_control||!caps.network_enabled;
    document.getElementById('reconnect-panel').hidden=!caps.wifi_control||!caps.network_enabled;
    const info=document.getElementById('network-capability-info');
    info.hidden=caps.hotspot_supported;
    info.textContent=!caps.wifi_control?'Wi-Fi hotspot controls are unavailable on this Pi. Menus, editing, SSH, and backups work through the connected network.':caps.hotspot_reason;

    document.getElementById('network-mode').textContent='Mode: '+({hotspot:'Menu Hotspot',internet:'Internet Wi-Fi',ethernet:'Ethernet (wired)',disconnected:'Disconnected'})[data.mode];
    document.getElementById('network-addresses').textContent='Pi address: '+(data.addresses.join(', ')||'not assigned');
    document.getElementById('network-message').textContent=data.message||'';
    const selected=picker.value;
    picker.replaceChildren();
    for(const profile of data.internet_profiles){const option=api.element('option',profile.name);option.value=profile.uuid;picker.append(option);}
    if(data.internet_profiles.some(p=>p.uuid===selected))picker.value=selected;
    else if(data.internet_profile)picker.value=data.internet_profile;
    document.getElementById('network-trial').hidden=!data.pending;
    if(data.pending)document.getElementById('trial-status').textContent='Requested mode: '+(data.pending.mode==='hotspot'?'Menu Hotspot':'Internet Wi-Fi')+'. Time remaining: '+data.pending.remaining+' seconds.';
    controls();
  }
  async function load(){
    if(busy||loading)return;
    loading=true;
    try{
      const data=await api.request('/api/admin/system');
      scheduled=false;
      draw(data);
      if(data.capabilities.hotspot_supported&&!credentialsLoaded){
        const secret=await api.request('/api/admin/system/password');
        savedPassword=secret.password;
        password.value=savedPassword;
        credentialsLoaded=true;
        controls();
      }
      const restored=await api.request('/api/admin/system/restored-hotspot');
      document.getElementById('restored-hotspot-panel').hidden=!restored.pending||!data.capabilities.hotspot_supported;
      document.getElementById('restored-hotspot-info').textContent=restored.has_password?'A system backup contains a hotspot name and password. Apply it while on Internet Wi-Fi; this will not switch your current connection.':'The restored backup contained no hotspot password. Apply to acknowledge it and keep your current hotspot settings.';
      document.getElementById('apply-restored-hotspot').disabled=busy||scheduled||state.busy||!!state.pending||state.mode==='hotspot';
      api.feedback(status,'Network status loaded.');
    }catch(error){api.feedback(status,error.message,true);}
    finally{loading=false;status.classList.remove('network-loading');status.setAttribute('aria-busy','false');}
  }
  async function action(body){
    if(busy)return;
    busy=true;controls();
    try{
      const data=await api.request('/api/admin/system',{method:'POST',body:JSON.stringify(body)});
      if(body.action==='configure'){savedPassword=body.password;credentialsLoaded=true;}
      scheduled=!!data.scheduled;
      busy=false;
      if(!scheduled)await load();
      api.feedback(status,data.message);
    }catch(error){api.feedback(status,error.message,true);}
    finally{busy=false;controls();}
  }
  function switchMode(mode){
    if(mode==='hotspot' && dirty()){
      api.feedback(status,'Save the changed password before switching.',true);return;
    }
    if(!confirm('Switch Wi-Fi mode? This disconnects this page and SSH. Reconnect and choose Keep this mode within three minutes, or the Pi returns to its previous network.'))return;
    action({action:'switch',mode,profile:mode==='hotspot'?'':picker.value});
  }
  document.getElementById('refresh-network').addEventListener('click',load);
  picker.addEventListener('change',controls);
  password.addEventListener('input',controls);
  document.getElementById('show-hotspot-password').addEventListener('change',event=>{password.type=event.target.checked?'text':'password';});
  document.getElementById('hotspot-form').addEventListener('submit',event=>{
    event.preventDefault();
    if(!dirty())return;
    action({action:'configure',password:password.value,ssid:state.ssid});
  });
  document.getElementById('enable-hotspot').addEventListener('click',()=>switchMode('hotspot'));
  document.getElementById('enable-internet').addEventListener('click',()=>switchMode('internet'));
  document.getElementById('keep-network').addEventListener('click',()=>{if(state?.pending)action({action:'confirm',id:state.pending.id});});
  document.getElementById('cancel-network').addEventListener('click',()=>{if(state?.pending)action({action:'cancel',id:state.pending.id});});
  document.getElementById('apply-restored-hotspot').addEventListener('click',async()=>{
    if(busy)return;
    busy=true;controls();document.getElementById('apply-restored-hotspot').disabled=true;
    try{
      const result=await api.request('/api/admin/system/restored-hotspot/apply',{method:'POST',body:'{}'});
      credentialsLoaded=false;busy=false;await load();api.feedback(status,result.message);
    }catch(error){api.feedback(status,error.message,true);}finally{busy=false;controls();}
  });
  load();setInterval(load,10000);
})();
