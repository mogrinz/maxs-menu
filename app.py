"""Max's Menu: a local menu publisher for independent display players."""
from datetime import timedelta
import hmac
import os
import secrets
from flask import Flask, g, jsonify, redirect, render_template, request, session, url_for
from network_client import request_network
from models import THEMES, ALIASES, SCREEN_IDS, VERSION, Conflict, Forbidden, Store, read_json, validate_menu
import backups


def create_app(data_dir=None):
    store = Store(data_dir)
    app = Flask(__name__)
    app.secret_key = read_json(store.root / "session-secret.json")["key"]
    app.config.update(MAX_CONTENT_LENGTH=32*1024*1024, SESSION_COOKIE_NAME="maxs_menu_session",
                      SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Strict",
                      PERMANENT_SESSION_LIFETIME=timedelta(hours=12))
    app.extensions["store"] = store

    @app.before_request
    def permissions():
        if "csrf" not in session:
            session["csrf"] = secrets.token_hex(24)
        g.user = None
        username = session.get("username")
        if username:
            account = store.user(username)
            if account and account["enabled"] and hmac.compare_digest(account["token"], session.get("token", "")):
                g.user = account
            else:
                session.clear()
                session["csrf"] = secrets.token_hex(24)
        protected = request.path in {"/admin", "/history", "/account", "/theme", "/system", "/users", "/schedule"} or request.path.startswith("/api/admin/")
        if protected and not g.user:
            if request.path.startswith("/api/"):
                return jsonify(error="Please sign in again.", login_required=True), 401
            return redirect(url_for("login_page"))
        if (request.path in {"/users", "/theme", "/system", "/schedule"} or request.path.startswith("/api/admin/users") or request.path.startswith("/api/admin/schedule") or request.path.startswith("/api/admin/theme") or request.path.startswith("/api/admin/system") or request.path == "/api/admin/history/restore") and g.user and g.user["role"] not in {"admin"}:
            return jsonify(error="Administrator access required."), 403
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            token = request.headers.get("X-CSRF-Token", "") or request.form.get("csrf", "")
            if not hmac.compare_digest(token, session.get("csrf", "")):
                return jsonify(error="Reload this page and try again."), 403
            origin = request.headers.get("Origin")
            if origin and origin != request.host_url.rstrip("/"):
                return jsonify(error="Cross-origin request rejected."), 403

    @app.after_request
    def headers(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'self'; base-uri 'none'; form-action 'self'"
        return response

    @app.errorhandler(ValueError)
    def invalid(error):
        return jsonify(error=str(error)), 400

    @app.errorhandler(OSError)
    def storage_error(error):
        return jsonify(error='The Pi could not save settings. Check its available storage before retrying.'),503

    @app.errorhandler(413)
    def oversized(error):
        return jsonify(error='The uploaded file is too large. Menu imports support 1 MB and system backups support 24 MB.'),413

    @app.errorhandler(Conflict)
    def conflict(error):
        return jsonify(error=str(error)), 409

    @app.errorhandler(Forbidden)
    def forbidden(error):
        return jsonify(error=str(error)), 403

    @app.context_processor
    def context():
        return {"csrf":session.get("csrf", ""), "user":g.user, "version":VERSION,
                "screen_ids":SCREEN_IDS, "site_name":store.state()["settings"]["site_name"], "is_admin":bool(g.user and g.user["role"] in {"admin"})}

    def payload():
        value = request.get_json(silent=True)
        if not isinstance(value, dict):
            raise ValueError("Send a JSON object.")
        return value

    def download(value, filename):
        response=jsonify(value)
        response.headers['Content-Disposition']='attachment; filename="'+filename+'"'
        return response

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/login")
    def login_page():
        if g.user:
            return redirect(url_for("admin"))
        return render_template("login.html", error=None)

    @app.post("/login")
    def login():
        account = store.authenticate(request.form.get("username", ""), request.form.get("password", ""))
        if not account:
            return render_template("login.html", error="Username or password is incorrect."), 401
        session.clear()
        session.update(username=account["username"], token=account["token"], csrf=secrets.token_hex(24))
        session.permanent = True
        return redirect(url_for("admin"))

    @app.post("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login_page"))

    @app.get("/admin")
    def admin():
        return render_template("admin.html")

    @app.get("/history")
    def history_page():
        return render_template("history.html")

    @app.get("/account")
    def account_page():
        return render_template("account.html")

    @app.get("/theme")
    def theme_page():
        return render_template("theme.html", themes=THEMES)

    @app.get("/api/admin/theme")
    def theme_settings():
        data = store.menu()
        return jsonify(theme=data["theme"], revision=data["theme_revision"], themes=THEMES)

    @app.post("/api/admin/theme")
    def save_theme():
        body = payload()
        if set(body) != {"theme", "revision"}:
            raise ValueError("Theme settings need theme and revision.")
        data = store.set_theme(body["theme"], body["revision"], g.user)
        return jsonify(theme=data["theme"], revision=data["theme_revision"], message="Theme saved. Connected displays update within about 5 seconds.")

    @app.get("/system")
    def system_page():
        from zoneinfo import available_timezones
        return render_template("system.html",timezones=sorted(available_timezones()))

    @app.get("/api/admin/system/settings")
    def site_settings():
        return jsonify(store.site_settings())

    @app.post("/api/admin/system/settings")
    def save_site_settings():
        body=payload()
        if set(body)!={"timezone","revision"}:
            raise ValueError("Send timezone and revision.")
        return jsonify(store.set_timezone(body["timezone"],body["revision"],g.user))

    @app.get("/api/admin/clock")
    def server_clock():
        return jsonify(store.site_settings())

    @app.get("/api/admin/system")
    def system_status():
        try:
            return jsonify(request_network({"action":"status"}))
        except RuntimeError as error:
            return jsonify(error=str(error)), 503

    @app.post("/api/admin/system")
    def system_action():
        body = payload()
        try:
            return jsonify(request_network(body))
        except RuntimeError as error:
            return jsonify(error=str(error)), 503

    @app.get("/api/admin/system/password")
    def system_password():
        try:
            return jsonify(request_network({"action":"credentials"}))
        except RuntimeError as error:
            return jsonify(error=str(error)), 503

    @app.get('/api/admin/system/backup')
    def system_backup():
        try:
            if store.state()['settings']['hotspot_enabled']:
                secret=request_network({'action':'credentials'})
            else:
                secret={'password':''}
            value=backups.export_system(store,g.user,{'ssid':secret.get('ssid',store.state()['settings']['hotspot_ssid']),'password':secret['password']})
            return download(value,'maxs-menu-system-backup.json')
        except RuntimeError as error:
            return jsonify(error=str(error)),503

    @app.post('/api/admin/system/restore/preview')
    def system_restore_preview():
        value=payload().get('backup')
        with store.lock:
            _,summary=backups.prepare_system(store,value,g.user)
            current=backups.revision(store)
        session['backup_preview']=store.revision(value)
        return jsonify(summary=summary,revision=current)

    @app.post('/api/admin/system/restore')
    def system_restore():
        body=payload()
        if body.get('confirmation')!='RESTORE' or session.get('backup_preview')!=store.revision(body.get('backup')):
            raise ValueError('Preview the selected backup and confirm RESTORE before applying it.')
        summary=backups.restore_system(store,body.get('backup'),g.user,body.get('revision'))
        session.clear()
        return jsonify(message='System settings restored. Sign in again using the password indicated in the preview. Wi-Fi has not switched.',summary=summary,login_url='/login')

    @app.get('/api/admin/system/restored-hotspot')
    def restored_hotspot():
        with store.lock:
            value=store.state().get('pending_hotspot')
        return jsonify(pending=bool(value),has_password=bool(value and value['password']))

    @app.post('/api/admin/system/restored-hotspot/apply')
    def apply_restored_hotspot():
        from models import atomic_json
        with store.lock:
            state=store.state()
            settings=state.get('pending_hotspot')
            if settings is None:raise ValueError('There are no restored hotspot settings to apply.')
            if settings['password']:
                try:request_network({'action':'configure','password':settings['password'],'ssid':settings['ssid']})
                except RuntimeError as error:return jsonify(error=str(error)),503
            if settings['password']:state['settings']['hotspot_ssid']=settings['ssid']
            state.pop('pending_hotspot')
            atomic_json(store.state_path,state)
        return jsonify(message='Restored hotspot password saved. Your current connection has not changed.' if settings['password'] else 'This backup had no hotspot password. Your current hotspot settings were kept.')

    @app.get("/users")
    def users_page():
        return render_template("users.html")

    @app.get("/display/<screen>")
    def display(screen):
        sid = ALIASES.get(screen.lower(), screen.lower())
        if sid not in SCREEN_IDS:
            return "Unknown screen", 404
        preview_theme = request.args.get("theme", "")
        if preview_theme and preview_theme not in THEMES:
            return "Unknown theme", 400
        return render_template("display.html", screen=sid, screen_number=SCREEN_IDS.index(sid)+1, preview_theme=preview_theme, direct=request.args.get("direct") == "1")

    @app.get("/api/admin/menu")
    def menu():
        return jsonify(store.menu())

    @app.post("/api/admin/menu")
    def publish():
        body = payload()
        candidate = validate_menu(body.get("menu"))
        if g.user["role"] != "admin" and isinstance(candidate,dict):
            previous={r["id"]:r.get("rotation",0) for r in store.menu()["menu"]["screens"]}
            if any(r.get("rotation",0)!=previous.get(r.get("id"),0) for r in candidate.get("screens",[]) if isinstance(r,dict)):
                raise Forbidden("Only an administrator can change display rotation.")
        return jsonify(store.publish(candidate, body.get("revision"), g.user))

    @app.post('/api/admin/menu/import/preview')
    def import_menu():
        return jsonify(backups.menu_file(payload().get('backup')))

    @app.get("/api/admin/me")
    def me():
        return jsonify(username=g.user["username"], role=g.user["role"], version=VERSION)

    @app.post("/api/admin/password")
    def change_password():
        body = payload()
        if body.get("new_password") != body.get("confirm_password"):
            raise ValueError("The two passwords do not match.")
        updated = store.change_own_password(g.user, body.get("new_password"))
        session["token"] = updated["token"]
        return jsonify(message="Password changed.")

    @app.get("/api/admin/users")
    def users():
        return jsonify(users=store.visible_users())

    @app.post("/api/admin/users")
    def user_action():
        body = payload()
        # Only administrators can reach this endpoint.
        if set(body) - {"username", "operation", "password", "enabled", "role"}:
            raise ValueError("Unknown user fields.")
        store.manage_user(g.user, body.get("username"), body.get("operation"), body.get("password"), body.get("enabled"), body.get("role"))
        return jsonify(users=store.visible_users())

    @app.get("/api/admin/history")
    def history():
        with store.lock:
            state = store.state()
            entries = [{k:v[k] for k in ("id", "time", "actor", "action")} for v in state["history"]]
        return jsonify(history=entries, audit=state["audit"])

    @app.post("/api/admin/history/restore")
    def restore():
        body = payload()
        return jsonify(store.restore(body.get("id"), body.get("revision"), g.user))

    @app.get('/api/admin/history/<version_id>/download')
    def history_download(version_id):
        with store.lock:
            record=next((v for v in store.state()['history'] if v['id']==version_id),None)
            if record is None:raise ValueError('That history entry is no longer available.')
            return download(backups.export_menu(record['menu']),'maxs-menu-history-'+record['id']+'.json')

    @app.get("/schedule")
    def schedule_page():
        return render_template("schedule.html")

    @app.get("/api/admin/schedule")
    def schedule_settings():
        return jsonify(store.schedule())

    @app.post("/api/admin/schedule")
    def save_schedule():
        body=payload()
        if set(body)!={"rules","revision"}:raise ValueError("Send rules and revision.")
        return jsonify(store.set_schedule(body["rules"],body["revision"],g.user))

    @app.get("/api/display/<screen>")
    def public_display(screen):
        sid=ALIASES.get(screen.lower(),screen.lower())
        if sid not in SCREEN_IDS:return jsonify(error="Unknown screen"),404
        return jsonify(store.display(sid,direct=request.args.get("direct")=="1"))

    @app.get("/health")
    def health():
        return jsonify(status="ok", version=VERSION, revision=store.menu()["revision"])

    return app


if __name__ == "__main__":
    from waitress import serve
    serve(create_app(), host="0.0.0.0", port=int(os.environ.get("MENU_PORT", "8080")), threads=4)
