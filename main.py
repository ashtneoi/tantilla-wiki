from random import randrange

from werkzeug.exceptions import abort
from werkzeug.utils import redirect
from werkzeug.wrappers import Response

from bakery import render_path
from config import config
from tantilla import create_app, HTMLResponse


MOUNT_POINT = config["mount_point"]

stamp = randrange(0, 1<<31)
stamp_mask = (1<<32) - 1
prev_stamp = 0


def page(req, name):
    if req.method == 'POST':
        if 'stamp' not in req.form or 'text' not in req.form:
            return abort(400)
        global prev_stamp
        try:
            prev_stamp = int(req.form["stamp"])
            print(req.form["text"])
        except ValueError:
            return abort(400)
        return redirect(req.full_path, code=303)
    if 'edit' in req.args:
        global stamp
        resp = HTMLResponse(
            render_path('tmpl/page.htmo', {
                'base': MOUNT_POINT,
                'content': "HOI!",
                'stamp': str(stamp),
                'prevstamp': str(prev_stamp),
                'title': "Edit page",
            })
        )
        stamp = (stamp + 1) & stamp_mask
        return resp
    else:
        return abort(400)


application = create_app(MOUNT_POINT, (
    ('<path:name>', page),
))
