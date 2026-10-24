(() => {
  'use strict';
  const api=window.MenuAPI, status=document.getElementById('backup-status');
  const input=document.getElementById('system-backup-file'), preview=document.getElementById('preview-system-backup');
  const panel=document.getElementById('system-backup-preview'), confirmation=document.getElementById('backup-confirmation');
  const restore=document.getElementById('restore-system-backup');
  let backup, revision, busy=false, completed=false;
  function clearPreview(){backup=undefined;revision=undefined;panel.hidden=true;confirmation.value='';restore.disabled=true;}
  input.addEventListener('change',()=>{clearPreview();preview.disabled=!input.files.length;api.feedback(status,'');});
  confirmation.addEventListener('input',()=>{restore.disabled=busy||completed||!backup||confirmation.value!=='RESTORE';});
  preview.addEventListener('click',async()=>{
    if(busy||!input.files.length)return;
    clearPreview();busy=true;preview.disabled=true;input.disabled=true;
    try{
      const file=input.files[0];if(file.size>24*1024*1024)throw new Error('System backup files must be smaller than 24 MB.');
      let candidate;try{candidate=JSON.parse(await file.text());}catch(_){throw new Error('Choose a valid system backup JSON file.');}
      const result=await api.request('/api/admin/system/restore/preview',{method:'POST',body:JSON.stringify({backup:candidate})});
      backup=candidate;revision=result.revision;const s=result.summary;
      document.getElementById('backup-summary').textContent='Created: '+s.created_at+'\nTheme: '+s.theme+'\nMenu entries: '+s.entries+'\nAccounts: '+s.users+'\nHistory versions: '+s.history+'\nSite: '+s.site_name+'\nTimezone: '+s.timezone+'\nSchedule rules: '+s.rules+'\nHotspot password: '+(s.hotspot_saved?'Saved for separate application':'None in this backup')+'\nSign-in account after restore: '+s.login_username+'\nSign-in password: '+(s.login_password_source==='backup'?'Use the password from the backup':'Use your current password');
      panel.hidden=false;api.feedback(status,'Backup validated. Review the summary before restoring.');
    }catch(error){api.feedback(status,error.message,true);}finally{busy=false;preview.disabled=false;input.disabled=false;}
  });
  restore.addEventListener('click',async()=>{
    if(busy||completed||!backup||confirmation.value!=='RESTORE')return;
    busy=true;restore.disabled=true;input.disabled=true;preview.disabled=true;
    try{
      const result=await api.request('/api/admin/system/restore',{method:'POST',body:JSON.stringify({backup,revision,confirmation:confirmation.value})});
      completed=true;api.feedback(status,result.message);
      const link=api.element('a','Sign in as '+result.summary.login_username);link.href=result.login_url;status.append(' ',link);
      confirmation.disabled=true;
    }catch(error){api.feedback(status,error.message,true);clearPreview();}
    finally{busy=false;if(!completed){input.disabled=false;preview.disabled=false;}}
  });
})();
