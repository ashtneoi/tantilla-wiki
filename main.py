from werkzeug.exceptions import abort

from bakery import render_path
from config import config
from tantilla import create_app, HTMLResponse


MOUNT_POINT = config["mount_point"]


def page(req, name):
    if req.method == 'POST':
        return abort(400)
    return HTMLResponse(
        render_path("tmpl/page.htmo", {
            "base": MOUNT_POINT,
            "title": "Edit page",
        })
    )


application = create_app(MOUNT_POINT, (
    ("<path:name>", page),
))
