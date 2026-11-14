"""Click script and oracle of LabConstrictor_Demo's Image_Preview.ipynb (an ipywidgets FileUpload, a status line and an inline preview).

The browser's file dialog cannot be driven headless (HUMAN); the upload is simulated by setting the FileUpload value to what ipywidgets 8 puts there after
an upload (a tuple of {name, type, size, content, last_modified}), which fires the notebook's observer exactly as a real upload does. Files of known content
are built in the kernel with Pillow:
* gray16.png, 1200x900, 16-bit grayscale ramp: status "Loaded gray16.png (1200x900px, mode I...)", preview a PNG thumbnail of 800x600 (max 800x800, aspect kept);
* rgb.png, 300x200 RGB: status names 300x200 and RGB, preview 300x200 (no upscaling);
* notes.txt (not an image): status "Could not read the image", no preview;
* the upload cleared (empty value): status "Upload cleared.".

Oracle (in the kernel, oracle_* rows): the status texts above and the decoded preview PNG sizes.
"""

AFTER_CELL = {3: "upload"}
STAGES = {
    "upload": """
import base64 as _b64, datetime as _dt, re as _re
from io import BytesIO as _BytesIO
import numpy as _np
from PIL import Image as _Image

_up = lcnb.find(var="uploader")
_status = lcnb.find(var="status_out")
_preview = lcnb.find(var="preview_out")
lcnb.human("upload_dialog", "the 'Upload image' button opens the browser's file dialog: the upload is simulated by setting the FileUpload value")

def _png(array, mode=None):
    buffer = _BytesIO()
    (_Image.fromarray(array, mode) if mode else _Image.fromarray(array)).save(buffer, format="PNG")
    return buffer.getvalue()

def _upload(name, kind, data):
    lcnb.set_value(_up, ({"name": name, "type": kind, "size": len(data), "content": memoryview(data),
                          "last_modified": _dt.datetime.now(_dt.timezone.utc)},))

def _preview_size():
    found = _re.search(r"data:image/png;base64,([A-Za-z0-9+/=]+)", str(_preview.value))
    return _Image.open(_BytesIO(_b64.b64decode(found.group(1)))).size if found else None

_ramp = (_np.arange(1200, dtype=_np.uint32)[None, :] * 50 + _np.arange(900, dtype=_np.uint32)[:, None] * 3).astype(_np.uint16)
lcnb.guarded("click_upload_gray16", lambda: _upload("gray16.png", "image/png", _png(_ramp)))
lcnb.check("oracle_gray16_status", _re.search(r"Loaded gray16\\.png \\(1200x900px, mode I", str(_status.value)) is not None, "status: %s" % _status.value)
lcnb.check("oracle_gray16_preview", _preview_size() == (800, 600), "preview thumbnail size %s (expected (800, 600))" % (_preview_size(),))

_rgb = _np.zeros((200, 300, 3), dtype=_np.uint8)
_rgb[..., 0], _rgb[..., 1], _rgb[..., 2] = 200, 20, 30
lcnb.guarded("click_upload_rgb", lambda: _upload("rgb.png", "image/png", _png(_rgb)))
lcnb.check("oracle_rgb_status", "Loaded rgb.png (300x200px, mode RGB)" in str(_status.value), "status: %s" % _status.value)
lcnb.check("oracle_rgb_preview", _preview_size() == (300, 200), "preview size %s (expected (300, 200): no upscaling)" % (_preview_size(),))

lcnb.guarded("click_upload_text", lambda: _upload("notes.txt", "text/plain", b"not an image"))
lcnb.check("oracle_text_refused", "Could not read the image" in str(_status.value) and not str(_preview.value), "status: %s; preview %r" % (_status.value, str(_preview.value)[:40]))

lcnb.guarded("click_upload_clear", lambda: lcnb.set_value(_up, ()))
lcnb.check("oracle_upload_cleared", "Upload cleared." in str(_status.value), "status after clearing: %s" % _status.value)
""",
}
NO_ORACLE = ""
