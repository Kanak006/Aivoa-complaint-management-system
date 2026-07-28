import io
import email
from email import policy

from fastapi import UploadFile, HTTPException


def extract_text_from_upload(file: UploadFile, raw_bytes: bytes) -> str:
    """
    Best-effort text extraction. Per assignment spec, production-grade OCR/parsing
    is NOT required — this handles the common demo cases: .txt, .eml, .pdf (text layer).
    """
    filename = (file.filename or "").lower()

    if filename.endswith(".pdf"):
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(raw_bytes))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            if not text.strip():
                raise ValueError("empty")
            return text
        except Exception:
            raise HTTPException(
                status_code=422,
                detail="Could not extract text from this PDF (it may be a scanned image without a text layer).",
            )

    if filename.endswith(".eml"):
        msg = email.message_from_bytes(raw_bytes, policy=policy.default)
        parts = [f"Subject: {msg['subject']}", f"From: {msg['from']}"]
        body = msg.get_body(preferencelist=("plain",))
        if body:
            parts.append(body.get_content())
        return "\n".join(parts)

    # .txt, .docx-saved-as-plain-text, or anything else: best-effort decode
    try:
        return raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return raw_bytes.decode("latin-1", errors="ignore")
