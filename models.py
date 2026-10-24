"""Menu schema, durable storage, migrations and account permissions."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import tempfile
import threading
import uuid
from werkzeug.security import check_password_hash, generate_password_hash

VERSION = "1.0.0-rc2"
ROOT = Path(__file__).resolve().parent
SCREEN_IDS = tuple("screen" + str(i) for i in range(1, 11))
THEMES = {"classic-bagel-shop": "Classic Bagel Shop", "modern-minimalistic": "Modern Minimalistic", "golden-chalk": "Golden Chalk", "coffeehouse-chalkboard": "Coffeehouse Chalkboard", "rose-cafe": "Rose Café", "retro-diner": "Retro Diner", "starlight-cafe":"Starlight Café", "seaside-cafe":"Seaside Café", "autumn-harvest":"Autumn Harvest", "winter-hearth":"Winter Hearth", "spring-garden":"Spring Garden"}
ALIASES = {"breakfast":"screen1", "lunch":"screen2", "baked":"screen3"}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id():
    return uuid.uuid4().hex


def valid_password(value):
    if not isinstance(value, str) or not re.fullmatch(r"[\x20-\x7e]{4,64}", value) or len(value.strip()) < 4:
        raise ValueError("Use 4–64 characters: letters, numbers, spaces or punctuation.")
    return value


def valid_username(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,40}", value):
        raise ValueError("Usernames use 1–40 letters, numbers, underscores or hyphens.")
    return value.lower()


def make_user(username, password, role):
    return {"username":valid_username(username), "role":role, "enabled":True,
            "password_hash":generate_password_hash(valid_password(password), method="pbkdf2:sha256:200000"),
            "token":secrets.token_hex(16)}


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.stem+"-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        if os.name == "posix":
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        Path(temporary).unlink(missing_ok=True)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_menu(menu):
    if not isinstance(menu, dict) or set(menu) != {"schema_version", "screens"} or menu["schema_version"] != 3:
        raise ValueError("Expected a version-3 collection of ten menus.")
    screens = menu["screens"]
    if not isinstance(screens, list) or len(screens) != 10:
        raise ValueError("The collection must contain Menu 1 through Menu 10.")
    seen_screens, seen_items = set(), set()
    count = 0
    for screen in screens:
        if not isinstance(screen, dict) or not {"id", "items"}.issubset(screen) or set(screen) - {"id", "items", "food_safety_warning", "rotation"}:
            raise ValueError("Each screen needs id and items, with an optional food safety warning setting.")
        if type(screen.get("rotation", 0)) is not int or screen.get("rotation", 0) not in {0,90,180,270}:
            raise ValueError("Choose a rotation of 0, 90, 180 or 270 degrees.")
        if "food_safety_warning" in screen and not isinstance(screen["food_safety_warning"], bool):
            raise ValueError("Food safety warning must be checked or unchecked.")
        if not isinstance(screen["id"], str) or screen["id"] not in SCREEN_IDS or screen["id"] in seen_screens:
            raise ValueError("Menu IDs must be unique: screen1 through screen10.")
        seen_screens.add(screen["id"])
        if not isinstance(screen["items"], list):
            raise ValueError("Each screen needs an ordered list of entries.")
        for item in screen["items"]:
            count += 1
            if not isinstance(item, dict):
                raise ValueError("Invalid entry.")
            base = {"id", "kind", "name", "available", "column"}
            kind = item.get("kind")
            required = base | ({"layout", "starts_section"} if kind == "header" else {"description"} if kind == "item" else set())
            if not isinstance(kind, str) or kind not in {"header", "item", "option"} or not required.issubset(item) or set(item) - (required | ({"price"} if kind == "item" else set())):
                raise ValueError("Entry type must be header, menu item, or included option.")
            iid = item["id"]
            if not isinstance(iid, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", iid) or iid in seen_items:
                raise ValueError("Entry IDs must be unique.")
            seen_items.add(iid)
            if not isinstance(item["name"], str) or not 1 <= len(item["name"].strip()) <= 120:
                raise ValueError("Every entry needs a name of 1–120 characters.")
            if not isinstance(item["available"], bool) or type(item["column"]) is not int or item["column"] not in {1, 2}:
                raise ValueError("Choose Column 1 or Column 2 and an availability setting.")
            if kind == "header":
                if not isinstance(item["layout"], str) or item["layout"] not in {"full", "two"} or not isinstance(item["starts_section"], bool):
                    raise ValueError("Headers need Full Width or 2 Columns and a header role.")
            elif kind == "item":
                if not isinstance(item["description"], str) or len(item["description"]) > 400:
                    raise ValueError("Descriptions must be at most 400 characters.")
                price = item.get("price")
                if price is not None and price != "" and (not isinstance(price, str) or not re.fullmatch(r"-?(?:0|[1-9][0-9]{0,3})\.[0-9]{2}", price)):
                    raise ValueError("Price is optional. Use a number such as 5.50 between -9999.99 and 9999.99, or leave it blank.")
    if count > 500:
        raise ValueError("Use at most 500 entries across all menus.")
    return menu


def migrate_menu(legacy):
    """Upgrade a public data schema without replacing existing entries."""
    import copy
    result = copy.deepcopy(legacy)
    if isinstance(result, dict) and result.get("schema_version") == 2:
        rows = result.get("screens", [])
        if not isinstance(rows, list) or len(rows) != 3:
            raise ValueError("Unrecognized older menu collection.")
        rows.extend({"id":sid,"items":[],"rotation":0} for sid in SCREEN_IDS[3:])
        result["schema_version"] = 3
    return validate_menu(result)


class Conflict(Exception):
    pass


class Forbidden(Exception):
    pass


class Store:
    def __init__(self, directory=None):
        self.root = Path(directory or os.environ.get("MENU_DATA_DIR", ROOT / "data"))
        self.root.mkdir(parents=True, exist_ok=True)
        if not (self.root/'users.json').exists():
            raise RuntimeError('Run .venv/bin/python configure.py before starting the server.')
        self.restore_journal = self.root / 'restore-transaction.json'
        if self.restore_journal.exists():
            self._restore_files(read_json(self.restore_journal)['before'])
            self._clear_restore_journal()
        self.lock = threading.RLock()
        self.menu_path = self.root / "menu.json"
        self.users_path = self.root / "users.json"
        self.state_path = self.root / "menu-state.json"
        if not self.menu_path.exists():
            atomic_json(self.menu_path, read_json(ROOT / "sample_menu.json"))
        menu = read_json(self.menu_path)
        if menu.get("schema_version") != 3:
            migrated = migrate_menu(menu)
            if not (self.root / "menu-before-v1.json").exists():
                atomic_json(self.root / "menu-before-v1.json", menu)
            atomic_json(self.menu_path, migrated)
        validate_menu(read_json(self.menu_path))
        if not self.state_path.exists():
            atomic_json(self.state_path, {"menu":read_json(self.menu_path), "history":[], "audit":[]})
        existing = read_json(self.state_path)
        if existing["menu"].get("schema_version") != 3:
            existing["menu"] = migrate_menu(existing["menu"])
            for record in existing["history"]: record["menu"] = migrate_menu(record["menu"])
            atomic_json(self.state_path, existing)
        state = self.state()
        # menu-state.json is the transaction source; menu.json remains an export mirror.
        if read_json(self.menu_path) != state["menu"]:
            atomic_json(self.menu_path, state["menu"])
        if not self.users_path.exists():
            raise RuntimeError("Run .venv/bin/python configure.py before starting the server.")
        if not any(u["role"] == "admin" and u["enabled"] for u in self.users()):
            raise RuntimeError("No enabled administrator. Run reset_admin.py locally.")
        state = read_json(self.state_path)
        if "settings" not in state:
            raise RuntimeError("Run configure.py to create site settings.")
        validate_settings(state["settings"])
        if state["menu"].get("schema_version") != 3:
            state["menu"] = migrate_menu(state["menu"])
            for record in state["history"]:
                record["menu"] = migrate_menu(record["menu"])
            atomic_json(self.state_path, state)
        if not (self.root / "session-secret.json").exists():
            atomic_json(self.root / "session-secret.json", {"key":secrets.token_hex(32)})

    def _restore_files(self, files):
        names={'menu-state.json','users.json','menu.json'}
        if not isinstance(files,dict) or set(files)!=names:
            raise ValueError('Invalid restore transaction. Recover from a local backup.')
        for name in sorted(names):
            atomic_json(self.root/name,files[name])

    def _clear_restore_journal(self):
        self.restore_journal.unlink()
        if os.name=='posix':
            directory=os.open(self.root,os.O_RDONLY)
            try:os.fsync(directory)
            finally:os.close(directory)

    def commit_restore(self, files):
        """Journal a multi-file restore; interruption reverts it at next startup."""
        with self.lock:
            names={'menu-state.json','users.json','menu.json'}
            before={name:read_json(self.root/name) for name in names}
            backup_dir=self.root/'pre-restore-backups'
            backup_dir.mkdir(mode=0o700,exist_ok=True)
            backup_dir.chmod(0o700)
            atomic_json(backup_dir/(new_id()+'.json'),before)
            atomic_json(self.restore_journal,{'before':before})
            try:
                self._restore_files(files)
                self._clear_restore_journal()
            except OSError:
                self._restore_files(before)
                self._clear_restore_journal()
                raise

    def state(self):
        state = read_json(self.state_path)
        validate_menu(state["menu"])
        if not isinstance(state.get("history"), list) or not isinstance(state.get("audit"), list):
            raise ValueError("Saved history is invalid.")
        validate_schedule(state.get("schedule", []))
        if "settings" in state: validate_settings(state["settings"])
        return state

    @staticmethod
    def revision(menu):
        return hashlib.sha256(json.dumps(menu, ensure_ascii=False, sort_keys=True).encode()).hexdigest()

    def menu(self):
        with self.lock:
            state = self.state()
            menu = state["menu"]
            theme = state.get("theme", "classic-bagel-shop")
            if theme not in THEMES:
                raise ValueError("Saved theme is invalid.")
            return {"menu":menu, "revision":self.revision(menu), "theme":theme, "theme_revision":self.revision(theme)}

    def set_theme(self, theme, revision, user):
        if user["role"] not in {"admin"}:
            raise Forbidden("Only an administrator can change the theme.")
        if not isinstance(theme, str) or theme not in THEMES:
            raise ValueError("Choose a supported theme.")
        with self.lock:
            state = self.state()
            current = state.get("theme", "classic-bagel-shop")
            if revision != self.revision(current):
                raise Conflict("Someone else changed the theme. Reload the theme page before saving.")
            state["theme"] = theme
            atomic_json(self.state_path, state)
            return self.menu()

    def publish(self, menu, revision, user, action="publish"):
        validate_menu(menu)
        with self.lock:
            state = self.state()
            if revision != self.revision(state["menu"]):
                raise Conflict("Someone else published changes. Reload the saved menu before publishing again.")
            event = {"id":new_id(), "time":now(), "actor":self.actor(user), "action":action}
            state["history"].insert(0, {**event, "menu":state["menu"]})
            state["history"] = state["history"][:30]
            state["audit"].insert(0, event)
            state["audit"] = state["audit"][:200]
            state["menu"] = menu
            atomic_json(self.state_path, state)
            try:
                atomic_json(self.menu_path, menu)
            except OSError:
                # The committed state is already durable; startup repairs this export.
                pass
            return self.menu()

    def restore(self, version_id, revision, user):
        if user["role"] not in {"admin"}:
            raise Forbidden("Only an administrator can restore menu history.")
        with self.lock:
            record = next((v for v in self.state()["history"] if v["id"] == version_id), None)
            if record is None:
                raise ValueError("That history entry is no longer available.")
            return self.publish(record["menu"], revision, user, "restore")

    @staticmethod
    def actor(user):
        return user["username"]

    def users(self):
        users = read_json(self.users_path)["users"]
        if not isinstance(users, list):
            raise ValueError("Users file is invalid.")
        return users

    def user(self, username):
        username = valid_username(username)
        with self.lock:
            return next((u for u in self.users() if u["username"] == username), None)

    def authenticate(self, username, password):
        try:
            account = self.user(username)
            if account and account["enabled"] and isinstance(password, str) and len(password) <= 64 and check_password_hash(account["password_hash"], password):
                return account
        except (ValueError, KeyError, TypeError):
            pass
        return None

    def change_own_password(self, user, password):
        if user["role"] not in {"admin"}:
            raise Forbidden("Employee accounts cannot change passwords.")
        with self.lock:
            current = self.user(user["username"])
            if not current or current["token"] != user["token"]:
                raise Forbidden("Sign in again before changing the password.")
            updated = make_user(current["username"], password, current["role"])
            rows = [updated if u["username"] == current["username"] else u for u in self.users()]
            atomic_json(self.users_path, {"users":rows})
            return updated

    def manage_user(self, actor, username, operation, password=None, enabled=None, role=None):
        if actor["role"] != "admin":
            raise Forbidden("Only an administrator can manage users.")
        username = valid_username(username)
        with self.lock:
            rows = self.users()
            current = next((u for u in rows if u["username"] == username), None)
            if operation == "create":
                if current:
                    raise ValueError("Username is unavailable.")
                if len(rows) >= 50:
                    raise ValueError("At most 50 accounts are supported.")
                if role not in {"admin", "editor"}:
                    raise ValueError("Choose Administrator or Employee.")
                rows.append(make_user(username, password, role))
            elif not current:
                raise ValueError("User does not exist.")
            elif operation == "password":
                replacement = make_user(username, password, current["role"])
                replacement["enabled"] = current["enabled"]
                current.update(replacement)
            elif operation == "enabled":
                if type(enabled) is not bool:
                    raise ValueError("Enabled must be true or false.")
                current["enabled"] = enabled
                current["token"] = secrets.token_hex(16)
            elif operation == "role":
                if role not in {"admin", "editor"}:
                    raise ValueError("Choose Administrator or Employee.")
                current["role"] = role
                current["token"] = secrets.token_hex(16)
            elif operation == "delete":
                rows = [u for u in rows if u["username"] != username]
            else:
                raise ValueError("Unknown user action.")
            if not any(u["role"] == "admin" and u["enabled"] for u in rows):
                raise ValueError("Keep at least one enabled administrator.")
            atomic_json(self.users_path, {"users":rows})

    def visible_users(self):
        return [{k:u[k] for k in ("username", "role", "enabled")} for u in self.users()]

    def schedule(self):
        with self.lock:
            state = self.state()
            rules = state.get("schedule", [])
            from zoneinfo import ZoneInfo
            local=datetime.now(timezone.utc).astimezone(ZoneInfo(state["settings"]["timezone"]))
            return {"rules":rules,"revision":self.revision(rules),"timezone":state["settings"]["timezone"],"server_time":format_clock(local,state["settings"]["timezone"])}

    def set_schedule(self, rules, revision, user):
        if user["role"] != "admin":
            raise Forbidden("Only an administrator can change schedules.")
        validate_schedule(rules)
        with self.lock:
            state = self.state()
            if revision != self.revision(state.get("schedule", [])):
                raise Conflict("The schedule changed. Reload it before saving.")
            state["schedule"] = rules
            atomic_json(self.state_path, state)
            return self.schedule()

    def site_settings(self):
        from zoneinfo import ZoneInfo
        with self.lock:
            zone = self.state()["settings"]["timezone"]
        local = datetime.now(timezone.utc).astimezone(ZoneInfo(zone))
        return {"timezone":zone,"revision":self.revision(zone),"server_time":format_clock(local,zone)}

    def set_timezone(self, zone, revision, user):
        if user["role"] != "admin":
            raise Forbidden("Only an administrator can change the schedule timezone.")
        with self.lock:
            state = self.state()
            settings = {**state["settings"],"timezone":zone}
            validate_settings(settings)
            if revision != self.revision(state["settings"]["timezone"]):
                raise Conflict("The timezone changed. Reload the saved timezone before saving.")
            state["settings"] = settings
            atomic_json(self.state_path,state)
            return self.site_settings()

    def display(self, screen, instant=None, direct=False):
        from zoneinfo import ZoneInfo
        with self.lock:
            state = self.state()
        data = {"menu":state["menu"],"theme":state.get("theme","classic-bagel-shop")}
        local = (instant or datetime.now(timezone.utc)).astimezone(ZoneInfo(state["settings"]["timezone"]))
        minute = local.hour * 60 + local.minute
        selected = screen
        if not direct:
            for rule in state.get("schedule", []):
                if rule["screen"] == screen and minute in rule_minutes(rule):
                    selected = rule["menu"]
                    break
        content = next(row for row in data["menu"]["screens"] if row["id"] == selected)
        public = {"content":content,"menu_id":selected,"theme":data["theme"]}
        public["revision"] = self.revision(public)
        return public


def format_clock(local, zone):
    """English wall-clock text; keep the IANA identifier separate for settings."""
    days = ("Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday")
    months = ("Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec")
    return (f"{days[local.weekday()]}, {months[local.month-1]} {local.day} {local.year} "
            f"{local.hour%12 or 12}:{local.minute:02d}{'AM' if local.hour<12 else 'PM'} "
            + zone.replace("_"," "))


def validate_settings(value):
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    if not isinstance(value,dict) or set(value)!={"site_name","timezone","hotspot_enabled","hotspot_ssid","wifi_interface","country"}:
        raise ValueError("Invalid site settings.")
    if not isinstance(value["site_name"],str) or not 1<=len(value["site_name"].strip())<=100:
        raise ValueError("Site name needs 1–100 characters.")
    if not isinstance(value["timezone"],str):raise ValueError("Choose an IANA timezone.")
    try: ZoneInfo(value["timezone"])
    except (ZoneInfoNotFoundError,ValueError): raise ValueError("Choose an IANA timezone, such as America/New_York.") from None
    if type(value["hotspot_enabled"]) is not bool:raise ValueError("Choose whether to enable hotspot support.")
    if not isinstance(value["hotspot_ssid"],str) or not re.fullmatch(r"[\x20-\x7e]{1,32}",value["hotspot_ssid"]) or not value["hotspot_ssid"].strip():
        raise ValueError("Hotspot name needs 1–32 printable ASCII characters.")
    if not isinstance(value["wifi_interface"],str) or not re.fullmatch(r"[a-zA-Z0-9_.-]{1,15}",value["wifi_interface"]):
        raise ValueError("Invalid Wi-Fi interface.")
    if not isinstance(value["country"],str) or not re.fullmatch(r"[A-Z]{2}",value["country"]):
        raise ValueError("Use a two-letter Wi-Fi country code.")
    return value


def rule_minutes(rule):
    start,end = rule["start"],rule["end"]
    return set(range(start,end)) if start<end else set(range(start,1440)) | set(range(0,end))


def validate_schedule(rules):
    if not isinstance(rules,list) or len(rules)>200:
        raise ValueError("Use at most 200 schedule rules.")
    occupied = {sid:set() for sid in SCREEN_IDS}
    ids = set()
    for rule in rules:
        if not isinstance(rule,dict) or set(rule)!={"id","start","end","screen","menu"}:
            raise ValueError("Invalid schedule rule.")
        if not isinstance(rule["id"],str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}",rule["id"]) or rule["id"] in ids:
            raise ValueError("Schedule rule IDs must be unique.")
        ids.add(rule["id"])
        if not isinstance(rule["screen"],str) or rule["screen"] not in SCREEN_IDS or not isinstance(rule["menu"],str) or rule["menu"] not in SCREEN_IDS:
            raise ValueError("Choose Screen 1–10 and Menu 1–10.")
        if any(type(rule[k]) is not int or rule[k]%30 or not 0<=rule[k]<1440 for k in ["start","end"]) or rule["start"]==rule["end"]:
            raise ValueError("Choose different start and end times in 30-minute increments.")
        minutes = rule_minutes(rule)
        if occupied[rule["screen"]] & minutes:
            raise ValueError("Schedule rules overlap on " + rule["screen"] + ".")
        occupied[rule["screen"]].update(minutes)
    return rules
