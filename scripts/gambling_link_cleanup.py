"""Collector-only link cleanup. Keep human-readable anchor labels and tree shape."""
import re

# Explicit web/FTP URLs, www URLs, and common bare web domains. Avoid matching
# email addresses as bare domains; mailto: links themselves are removed.
_TLD = r"(?:com|org|net|edu|gov|mil|int|info|biz|name|pro|io|app|dev|xyz|online|site|tech|me|tv|uk|au|us|ca|cn|jp|de|fr|in|nz|ie|eu|co|ru|tw|hk|sg|ai|top|club|shop|store|cc|gg|ly|link|website|blog|xn--[a-z0-9-]+)"
_DOMAIN = r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+" + _TLD
_TAIL = r"""[^\s<>"'“”‘’。，、；！？：）】》」』]+"""
_LINK = re.compile(
    r"(?<![A-Za-z0-9_@])(?:(?:https?|ftp)://" + _TAIL +
    r"|mailto:" + _TAIL + r"|www\." + _TAIL +
    r"|" + _DOMAIN + r"(?![A-Za-z0-9_-])(?::[0-9]{1,5})?(?:[/?#]" + _TAIL + r")?)",
    re.I,
)
_ANCHOR = re.compile(r"<a\b[^>]*>(.*?)</a\s*>", re.I | re.S)
# Markdown inline link labels remain text. Balanced one-level URL parentheses.
_MARKDOWN = re.compile(
    r"!?(\[([^\]\n]*)\])\(\s*(?:<[^>\n]+>|(?:[^()\s]|\([^()\n]*\))+)(?:\s+[\"'][^\"'\n]*[\"'])?\s*\)"
)
_AUTOLINK = re.compile(r"<((?:https?://|ftp://|mailto:|www\.)[^<>\s]+)>", re.I)
_SOURCE_LINE = re.compile(
    r"^[ \t]*(?:source|original (?:post|article|link|url)|来源|來源|出处|出處|原文链接|原文連結|转载自|轉載自)\s*[:：]\s*$",
    re.I,
)

def _replace_url(match):
    value = match.group()
    # Preserve sentence punctuation and unmatched closing brackets, but not
    # brackets that genuinely belong to a URL path.
    suffix = ""
    while value and (
        value[-1] in ".,;:!?" or
        (value[-1] == ")" and value.count(")") > value.count("(")) or
        (value[-1] == "]" and value.count("]") > value.count("[")) or
        (value[-1] == "}" and value.count("}") > value.count("{"))
    ):
        suffix = value[-1] + suffix
        value = value[:-1]
    return suffix

def remove_links(text):
    if not isinstance(text, str):
        raise ValueError("invalid_link_cleanup_text")
    if not text:
        return text
    original = text
    text = _ANCHOR.sub(lambda m: m.group(1), text)
    text = _MARKDOWN.sub(lambda m: m.group(2), text)
    text = _AUTOLINK.sub("", text)
    text = _LINK.sub(_replace_url, text)
    # No changes to whitespace or source labels on lines without removed links.
    if text == original:
        return text
    lines = []
    before = original.splitlines()
    after = text.splitlines()
    for i, line in enumerate(after):
        changed = len(before) != len(after) or line != before[i]
        if changed:
            line = re.sub(r"[ \t]{2,}", " ", line)
            line = re.sub(r"[ \t]+([.,;:!?。，、；！？])", r"\1", line)
            line = re.sub(r"\(\s*\)|\[\s*\]|<\s*>", "", line)
            if _SOURCE_LINE.fullmatch(line.strip()) or not line.strip(" \t.,;:!?。，、；！？()[]<>"):
                line = ""
            line = line.rstrip()
        lines.append(line)
    return "\n".join(lines).strip()

def clean_collected_draft(draft):
    """In-place cleanup before validation/serialization, including every reply."""
    if not isinstance(draft, dict):
        raise ValueError("invalid_topic_fields")
    for field in ("title", "body"):
        draft[field] = remove_links(draft.get(field))
        if not draft[field].strip():
            raise ValueError("empty_" + field + "_after_link_cleanup")
    def visit(items, depth=1):
        if not isinstance(items, list) or depth > 8:
            raise ValueError("reply_depth_exceeded")
        for node in items:
            if not isinstance(node, dict):
                raise ValueError("invalid_reply")
            node["body"] = remove_links(node.get("body"))
            if not node["body"].strip():
                raise ValueError("empty_reply_after_link_cleanup")
            if node.get("replies"):
                visit(node["replies"], depth + 1)
    visit(draft.get("comments"))
    return draft
