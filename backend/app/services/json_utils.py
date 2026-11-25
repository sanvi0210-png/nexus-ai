import json
import re


def parse_json(text: str, default):
    """Parse JSON from an LLM reply, tolerating code fences and surrounding text."""
    t = re.sub(r"^```(?:json)?|```$", "", (text or "").strip(), flags=re.M).strip()
    try:
        return json.loads(t)
    except Exception:
        match = re.search(r"[\[{].*[\]}]", t, re.S)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
    return default
