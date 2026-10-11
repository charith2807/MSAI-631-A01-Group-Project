"""Contact-detail detection and redaction (only redacted text goes to the model).

Owner: Charith Reddy Mummadireddy Reddivari.
"""
from __future__ import annotations

import re

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE = re.compile(r"(?<!\w)(?:\+?\d{1,2}[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}(?!\w)")
LINK = re.compile(r"(?:https?://|www\.)\S+|(?:linkedin\.com|github\.com)/\S+", re.I)
_NAME = re.compile(r"^[A-Z][A-Za-z'’.-]+(?: [A-Z][A-Za-z'’.-]+){1,3}$")

PLACEHOLDERS = {"name": "[NAME]", "email": "[EMAIL]", "phone": "[PHONE]", "link": "[LINK]"}


def detect_contacts(text: str) -> dict[str, str]:
    contacts: dict[str, str] = {}
    if m := EMAIL.search(text):
        contacts["email"] = m.group(0)
    if m := PHONE.search(text):
        contacts["phone"] = m.group(0).strip()
    if m := LINK.search(text):
        contacts["link"] = m.group(0).rstrip(".,;)")
    for ln in text.splitlines()[:5]:
        ln = ln.strip()
        if _NAME.match(ln) and not any(ch.isdigit() for ch in ln):
            contacts["name"] = ln
            break
    return contacts


def redact(text: str, contacts: dict[str, str]) -> str:
    out = text
    for kind, value in contacts.items():
        if value:
            out = out.replace(value, PLACEHOLDERS[kind])
    # catch additional emails / phones / links not first-seen
    out = EMAIL.sub(PLACEHOLDERS["email"], out)
    out = PHONE.sub(PLACEHOLDERS["phone"], out)
    out = LINK.sub(PLACEHOLDERS["link"], out)
    return out


def restore(text: str, contacts: dict[str, str]) -> str:
    for kind, value in contacts.items():
        out = PLACEHOLDERS[kind]
        text = text.replace(out, value)
    return text
