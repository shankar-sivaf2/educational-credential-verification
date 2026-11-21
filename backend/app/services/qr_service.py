"""QR codes. They contain ONLY a verification URL with the certificate ID, never personal data."""
import io

import qrcode


def make_qr_png(url: str) -> bytes:
    image = qrcode.make(url, box_size=8, border=2)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()