from os import makedirs, path
from random import randrange
from subprocess import DEVNULL, PIPE, Popen, run

from werkzeug.urls import url_unquote
from werkzeug.utils import escape, redirect
from werkzeug.wrappers import Response

from auth import AuthManager
from bakery import render_path
from config import config
from tantilla import create_app, HTMLResponse, static_redirect, status


MOUNT_POINT = config["mount_point"]

stamp = randrange(0, 1<<31)
stamp_mask = (1<<32) - 1
prev_stamp = 0

auth_mgr = AuthManager(MOUNT_POINT)


def commit_file(name):
    ret = run((
        'git', '--git-dir=repo/.git/', '--work-tree=repo/',
        'add', '--', name,
    ), stdin=DEVNULL, stdout=DEVNULL).returncode
    if ret != 0:
        return False

    ret = run((
        'git', '--git-dir=repo/.git/', '--work-tree=repo/',
        'commit', '-m' + name,
    ), stdin=DEVNULL, stdout=DEVNULL).returncode
    if ret != 0:
        return False

    return True


def login(req):
    if req.method == 'POST':
        if "username" not in req.form or "password" not in req.form:
            return status(req, 400)
        username = req.form["username"]
        password = req.form["password"]

        auth_result = auth_mgr.try_log_in(username, password)
        if auth_result == AuthManager.USER_NOT_FOUND:
            return HTMLResponse(
                render_path("tmpl/login.htmo", {
                    "base": MOUNT_POINT,
                    "bad_username": True,
                    "bad_password": False,
                }),
                status=403,  # This one is iffy.
            )
        elif auth_result == AuthManager.PW_WRONG:
            return HTMLResponse(
                render_path("tmpl/login.htmo", {
                    "base": MOUNT_POINT,
                    "bad_username": False,
                    "bad_password": True,
                }),
                status=403,  # This one is iffy.
            )
        else:
            id_, expiration = auth_result
            from_ = url_unquote(req.args.get("from", ""))

            resp = redirect(MOUNT_POINT + from_, code=303)
            resp.set_cookie("id", id_, expires=expiration, secure=True)
            return resp

    if auth_mgr.cookie_to_username(req.cookies.get("id")):
        # Already logged in.
        return redirect(MOUNT_POINT, code=303)
    else:
        resp = HTMLResponse(
            render_path("tmpl/login.htmo", {
                "base": MOUNT_POINT,
                "bad_username": False,
                "bad_password": False,
            }),
        )
        resp.delete_cookie("id")
        return resp


@auth_mgr.require_auth
def create(req, username):
    if req.method == 'POST':
        if 'name' not in req.form:
            return status(req, 400)
        name = path.relpath(req.form['name'].lstrip("/"))
        if name.startswith(".") or name.endswith("/"):
            return status(req, 400)
        filename = "repo/" + name
        makedirs(path.dirname(filename), exist_ok=True)
        try:
            with open(filename, "x") as f:
                pass
            if not commit_file(name):
                return status(req, 500)
        except FileExistsError:
            pass
        return redirect(MOUNT_POINT + "page/" + name + "?edit")

    return HTMLResponse(
        render_path("tmpl/create.htmo", {
            'base': MOUNT_POINT,
        })
    )


@auth_mgr.require_auth
def page_list(req, username):
    MAXLEN = 500

    ls = Popen((
        'git', '--git-dir=repo/.git/', '--work-tree=repo/',
        'ls-files', '-z',
    ), stdin=DEVNULL, stdout=PIPE, encoding='utf-8')
    out = ls.stdout.read(MAXLEN)
    if len(out) == MAXLEN:
        i = out.rfind('\0')
        if i == -1:  # not found
            i = 0
        out = out[:i]
    ls.terminate()  # We can trust Git with SIGTERM. Probably.

    names = map(
        lambda name: {'name': escape(name)},
        sorted(out.split('\0')),
    )
    return HTMLResponse(
        render_path('tmpl/page_list.htmo', {
            'base': MOUNT_POINT,
            'names': names,
        })
    )


@auth_mgr.require_auth
def page(req, username, name):
    assert not (name.startswith("./") or name.startswith("../"))
    if name.startswith(".") or name.endswith("/"):
        return status(req, 400)

    if req.method == 'POST':
        if 'stamp' not in req.form or 'text' not in req.form:
            return status(req, 400)
        global prev_stamp
        try:
            prev_stamp = int(req.form['stamp'])
        except ValueError:
            return status(req, 400)
        filename = "repo/" + name
        makedirs(path.dirname(filename), exist_ok=True)
        with open(filename, "w") as f:
            f.write(req.form['text'].rstrip() + "\n")

        if not commit_file(name):
            return status(req, 500)

        return redirect(req.full_path, code=303)

    if 'edit' in req.args:
        filename = "repo/" + name
        try:
            with open(filename, "r") as f:
                content = f.read().rstrip()
        except (FileNotFoundError, NotADirectoryError):
            return status(req, 404)
        global stamp
        resp = HTMLResponse(
            render_path('tmpl/page.htmo', {
                'base': MOUNT_POINT,
                'content': content,
                'name': name,
                'stamp': str(stamp),
                'prevstamp': str(prev_stamp),
                'title': "Edit \"{}\"".format(name),
            })
        )
        stamp = (stamp + 1) & stamp_mask
        return resp
    else:
        return redirect(req.path + '?edit')


application = create_app(MOUNT_POINT, (
    ('', static_redirect(MOUNT_POINT + 'list')),
    ('login', login),
    ('create', create),
    ('list', page_list),
    ('page/<path:name>', page),
))
