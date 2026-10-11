"""Tolerant JSON extraction for model output (handles ```json fences and surrounding prose).

Owner: Dathan Neal (model-output handling) / Charith Reddy Mummadireddy Reddivari.
"""
from __future__ import annotations

import json
import re


def parse_json_object(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I)
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            raise ValueError("no JSON object found")
        obj = json.loads(m.group(0))
    if not isinstance(obj, dict):
        raise ValueError("expected a JSON object")
    return obj
