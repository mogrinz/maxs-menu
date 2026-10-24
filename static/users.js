(() => {
  'use strict';
  const api=window.MenuAPI,el=api.element,list=document.getElementById('users'),status=document.getElementById('user-status');
  let busy=false;
  const message=(text,error=false)=>api.feedback(status,text,error);
  function button(text,action,className){const node=el('button',text,className);node.type='button';node.addEventListener('click',action);return node;}
  async function action(body){
    if(busy)return false;
    busy=true;
    try{const data=await api.request('/api/admin/users',{method:'POST',body:JSON.stringify(body)});draw(data.users);message('User settings saved.');return true;}
    catch(error){message(error.message,true);return false;}
    finally{busy=false;}
  }
  function draw(users){
    list.replaceChildren();
    for(const user of users){
      const row=el('section',undefined,'account');
      row.append(el('h2',user.username),el('p',(user.role==='admin'?'Administrator':'Employee')+' · '+(user.enabled?'Enabled':'Disabled')));
      const form=el('form'),toolbar=el('div',undefined,'toolbar'),label=el('label','New password for '+user.username),input=el('input');
      input.type='password';input.autocomplete='new-password';input.minLength=4;input.maxLength=64;input.required=true;
      label.append(input);const reset=el('button','Reset password');reset.type='submit';toolbar.append(label,reset);form.append(toolbar);
      form.addEventListener('submit',async event=>{event.preventDefault();if(await action({username:user.username,operation:'password',password:input.value}))input.value='';});
      row.append(form);
      const actions=el('div',undefined,'row-actions');
      actions.append(
        button(user.role==='admin'?'Make employee':'Make administrator',()=>action({username:user.username,operation:'role',role:user.role==='admin'?'editor':'admin'})),
        button(user.enabled?'Disable account':'Enable account',()=>action({username:user.username,operation:'enabled',enabled:!user.enabled})),
        button('Delete account',()=>{if(confirm('Delete account '+user.username+'?'))action({username:user.username,operation:'delete'});},'danger')
      );
      row.append(actions);list.append(row);
    }
  }
  document.getElementById('add-user').addEventListener('submit',async event=>{
    event.preventDefault();const name=document.getElementById('username'),password=document.getElementById('user-password');
    if(await action({username:name.value,operation:'create',password:password.value,role:document.getElementById('user-role').value})){name.value='';password.value='';}
  });
  api.request('/api/admin/users').then(data=>{draw(data.users);message('Users loaded.');}).catch(error=>message(error.message,true));
})();
