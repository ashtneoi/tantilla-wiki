from os import makedirs, path
from random import randrange

from werkzeug.utils import redirect
from werkzeug.wrappers import Response

from bakery import render_path
from config import config
from tantilla import create_app, HTMLResponse, status


MOUNT_POINT = config["mount_point"]

stamp = randrange(0, 1<<31)
stamp_mask = (1<<32) - 1
prev_stamp = 0


def create(req):
    if req.method == 'POST':
        if 'name' not in req.form:
            return status(req, 400)
        name = path.relpath(req.form['name'].lstrip("/"))
        if name.startswith(".") or name.endswith("/"):
            return status(req, 400)
        filename = "repo/" + name
        makedirs(path.dirname(filename), exist_ok=True)
        with open(filename, "w") as f:
            pass
        return redirect(MOUNT_POINT + "page/" + name + "?edit")

    return HTMLResponse(
        render_path("tmpl/create.htmo", {
            'base': MOUNT_POINT,
        })
    )



def page(req, name):
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
        return status(req, 400)


application = create_app(MOUNT_POINT, (
    ('create', create),
    ('page/<path:name>', page),
))
