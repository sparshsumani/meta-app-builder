# attachments.py
import base64
import re
from typing import Dict, List
from schemas import Attachment

DATA_URI_RE = re.compile(r"^data:(?P<mime>[\w/+.-]+);base64,(?P<b64>[A-Za-z0-9+/=]+)$")

def decode_and_collect_attachments(atts: List[Attachment]) -> Dict[str, bytes]:
    """
    Convert data URIs to bytes. Returns {filename: bytes}.
    (Extend to support http(s) fetches if your tasks include external URLs.)
    """
    out: Dict[str, bytes] = {}
    for a in atts:
        if not a.name:
            continue
        url = a.url or ""
        if url.startswith("data:"):
            m = DATA_URI_RE.match(url)
            if not m:
                continue
            out[a.name] = base64.b64decode(m.group("b64"))
        # else: you can add http(s) download if needed
    return out
