import mimetypes
import os
import smtplib
from email.message import EmailMessage

_MIME = {
    ".pdf": "application/pdf",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


def send_mail(subject: str, body: str, attachments: str | list[str]) -> None:
    user = os.environ["GMAIL_USER"]
    pwd = os.environ["GMAIL_APP_PASSWORD"]
    to = os.environ.get("TO_EMAIL") or user

    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = user, to, subject
    msg.set_content(body)

    paths = [attachments] if isinstance(attachments, str) else list(attachments)
    for path in paths:
        ext = os.path.splitext(path)[1].lower()
        ctype = _MIME.get(ext) or mimetypes.guess_type(path)[0] or "application/octet-stream"
        maintype, subtype = ctype.split("/", 1)
        with open(path, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype=maintype,
                subtype=subtype,
                filename=os.path.basename(path),
            )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(user, pwd)
        s.send_message(msg)
    print("Mail sent to", to)