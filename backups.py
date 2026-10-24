"""Validated, portable JSON backups. No uploaded paths, code, or session keys."""
import copy
import re
import secrets
from models import (VERSION, THEMES, now, new_id, valid_username, validate_menu,
                    Forbidden, Conflict, validate_settings, validate_schedule)

FORMAT='maxs-menu-system-backup'


def menu_file(value):
    if isinstance(value,dict) and value.get('format')=='maxs-menu-menu-backup':
        if value.get('format_version')!=1:
            raise ValueError('Unsupported menu backup version.')
        value=value.get('menu')
    menu=copy.deepcopy(validate_menu(value))
    return {'menu':menu,'item_count':sum(len(s['items']) for s in menu['screens'])}


def export_menu(menu):
    return {'format':'maxs-menu-menu-backup','format_version':1,
            'app_version':VERSION,'created_at':now(),'menu':menu}


def metadata(record, menu=False):
    keys={'id','time','actor','action'}|({'menu'} if menu else set())
    if not isinstance(record,dict) or set(record)!=keys:
        raise ValueError('Invalid history record in system backup.')
    for key in ['id','time','actor','action']:
        if not isinstance(record[key],str) or not 1<=len(record[key])<=120:
            raise ValueError('Invalid history metadata in system backup.')
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}',record['id']):
        raise ValueError('Invalid history ID in system backup.')
    if menu:validate_menu(record['menu'])


def account(value):
    keys={'username','role','enabled','password_hash'}
    if not isinstance(value,dict) or set(value)!=keys:
        raise ValueError('Invalid account in system backup.')
    if valid_username(value['username'])!=value['username'] or type(value['enabled']) is not bool:
        raise ValueError('Invalid account name or enabled setting.')
    allowed={'admin','editor'}
    if not isinstance(value['role'],str) or value['role'] not in allowed:
        raise ValueError('Invalid account role in system backup.')
    match=re.fullmatch(r'pbkdf2:sha256:([0-9]{1,7})\$[a-zA-Z0-9]{1,64}\$[a-f0-9]{64}',value['password_hash']) if isinstance(value['password_hash'],str) else None
    if not match or not 10000<=int(match.group(1))<=1000000:
        raise ValueError('Unsupported account password hash in system backup.')
    return {**value,'token':secrets.token_hex(16)}


def hotspot(value):
    if not isinstance(value,dict) or set(value)!={'ssid','password'} or not isinstance(value['ssid'],str) or not re.fullmatch(r'[\x20-\x7e]{1,32}',value['ssid']) or not value['ssid'].strip():
        raise ValueError('Invalid hotspot settings in system backup.')
    if not isinstance(value['password'],str) or (value['password'] and not re.fullmatch(r'[\x20-\x7e]{8,63}',value['password'])):
        raise ValueError('Invalid hotspot password in system backup.')
    return copy.deepcopy(value)


def clean_account(value):
    return {key:value[key] for key in ['username','role','enabled','password_hash']}


def export_system(store, user, wifi):
    if user['role'] not in {'admin'}:
        raise Forbidden('Only an administrator can create a system backup.')
    with store.lock:
        state=store.state()
        result={'format':FORMAT,'format_version':2,'app_version':VERSION,'created_at':now(),
                'state':{key:copy.deepcopy(state[key]) for key in ['menu','history','audit','settings','schedule']},
                'users':[clean_account(u) for u in store.users()],
                'hotspot':hotspot(state.get('pending_hotspot') or state.get('initial_hotspot') or wifi)}
        result['state']['theme']=state.get('theme','classic-bagel-shop')
        return result


def revision(store):
    return store.revision({'state':store.state(),'users':store.users()})


def prepare_system(store, value, user):
    if user['role'] not in {'admin'}:
        raise Forbidden('Only an administrator can restore a system backup.')
    required={'format','format_version','app_version','created_at','state','users','hotspot'}
    if not isinstance(value,dict) or not required.issubset(value) or set(value)-required or value['format']!=FORMAT or type(value['format_version']) is not int or value['format_version']!=2:
        raise ValueError('Choose a Max’s Menu system backup (format version 2).')
    if not isinstance(value['app_version'],str) or not isinstance(value['created_at'],str) or len(value['created_at'])>120:
        raise ValueError('Invalid backup information.')
    state=copy.deepcopy(value['state'])
    if not isinstance(state,dict) or set(state)!={'menu','theme','history','audit','settings','schedule'}:
        raise ValueError('Invalid menu settings in system backup.')
    validate_menu(state['menu'])
    validate_settings(state['settings'])
    validate_schedule(state['schedule'])
    if not isinstance(state['theme'],str) or state['theme'] not in THEMES:
        raise ValueError('Unsupported theme in system backup.')
    if not isinstance(state['history'],list) or len(state['history'])>30 or not isinstance(state['audit'],list) or len(state['audit'])>200:
        raise ValueError('Invalid history in system backup.')
    for item in state['history']:metadata(item,True)
    for item in state['audit']:metadata(item)
    if len({x['id'] for x in state['history']})!=len(state['history']):
        raise ValueError('Duplicate history records in system backup.')
    if not isinstance(value['users'],list) or not 1<=len(value['users'])<=50:
        raise ValueError('Invalid user list in system backup.')
    users=[account(u) for u in value['users']]
    if len({u['username'] for u in users})!=len(users):
        raise ValueError('Duplicate users in system backup.')
    admins=[u for u in users if u['role']=='admin' and u['enabled']]
    if not admins:raise ValueError('The backup needs at least one enabled administrator.')
    # Network hardware choices belong to the replacement Pi. Site name and
    # timezone restore, while interface/country/feature availability stay local.
    local=store.state()['settings']
    for key in ['wifi_interface','country','hotspot_enabled','hotspot_ssid']:
        state['settings'][key]=local[key]
    state['pending_hotspot']=hotspot(value['hotspot'])
    files={'menu-state.json':state,'menu.json':state['menu'],
           'users.json':{'users':users}}
    summary={'created_at':value['created_at'],'theme':THEMES[state['theme']],
             'entries':sum(len(s['items']) for s in state['menu']['screens']),
             'users':len(users),'history':len(state['history']),
             'login_username':admins[0]['username'], 'login_password_source':'backup',
             'hotspot_saved':bool(state['pending_hotspot']['password']),
             'site_name':state['settings']['site_name'],'timezone':state['settings']['timezone'],
             'rules':len(state['schedule'])}
    return files,summary


def restore_system(store, value, user, expected):
    with store.lock:
        if expected!=revision(store):
            raise Conflict('Settings changed since preview. Preview this backup again before restoring.')
        files,summary=prepare_system(store,value,user)
        event={'id':new_id(),'time':now(),'actor':store.actor(user),'action':'system-restore'}
        files['menu-state.json']['audit'].insert(0,event)
        files['menu-state.json']['audit']=files['menu-state.json']['audit'][:200]
        store.commit_restore(files)
        return summary
