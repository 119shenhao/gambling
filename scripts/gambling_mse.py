"""Strict MoneySavingExpert Vanilla forum parser; public HTML only.

May be used only after source permission and parser verification gates pass.
The returned payload retains public text and media references; no media is downloaded.
"""
import re
from urllib.parse import urljoin, urlsplit
from bs4 import BeautifulSoup, NavigableString

HOST = "forums.moneysavingexpert.com"
TOPIC_RE = re.compile(r"^/discussion/(\d{4,12})/([a-z0-9][a-z0-9-]{0,160})/?$")
PAGE_RE = re.compile(r"^/discussion/(\d{4,12})/([a-z0-9][a-z0-9-]{0,160})/p(\d{1,4})/?$")
GAMBLING = re.compile(r"\b(?:gambl(?:e|ing|er|ers)|betting|casino|slots?|roulette|"
                      r"relaps(?:e|ed)|quit(?:ting)?|recovery|debt|lost|losses)\b", re.I)
GAMBLING_TITLE = re.compile(r"\b(?:gambl\w*|betting|casino|slots?|roulette|bookmaker\w*)\b", re.I)
PRIVATE = re.compile(r"(?<!\d)(?:[+]?\d[ -]?){10,15}(?!\d)|"
                     r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", re.I)
INCOMPLETE = re.compile(r"\b(?:load more replies|show more replies|view hidden replies)\b", re.I)
EXCLUDED = "blockquote, .Quote, .Signature, .UserSignature, .User-Signature, .PostSignature"
MAX_REPLIES = 500


def source_id(url):
    parsed = urlsplit(url)
    match = TOPIC_RE.fullmatch(parsed.path)
    if (parsed.scheme != "https" or parsed.netloc != HOST or
            parsed.query or parsed.fragment or not match):
        raise ValueError("invalid_mse_topic_url")
    return match[1]


def discover(listing_url, html, excluded=(), maximum=60):
    root = urlsplit(listing_url)
    if root.scheme != "https" or root.netloc != HOST:
        raise ValueError("invalid_mse_listing_host")
    doc = BeautifulSoup(html, "html.parser")
    found = {}
    for node in doc.select("a[href*='/discussion/']"):
        if node.find_parent(["nav", "footer"]):
            continue
        target = urljoin(listing_url, node.get("href", ""))
        try:
            original_id = source_id(target)
        except ValueError:
            continue
        title = node.get_text(" ", strip=True)
        # Debt free diaries is broad. Never offer unrelated financial discussions.
        if not title or not GAMBLING_TITLE.search(title):
            continue
        if original_id not in excluded and original_id not in found:
            found[original_id] = target
        if len(found) >= maximum:
            break
    return found


def _text(node):
    # Copy rather than mutate the parsed document, so later structure checks
    # observe exactly the HTML downloaded from the source.
    clone = BeautifulSoup(str(node), "html.parser")
    for skipped in clone.select(EXCLUDED + ", script, style, noscript, button, svg"):
        skipped.decompose()
    # Vanilla renders emojis as images and user-embedded screenshots on its CDN.
    # Preserve the emoji's alt text and the full https image URL rather than
    # dropping the reply or silently discarding content. No media is downloaded.
    for media in clone.select("img, video, iframe, audio, .attachment, [data-attachment]"):
        if media.parent is None:
            continue  # an enclosing media wrapper has already been replaced
        kind = media.name
        is_emoji = kind == "img" and "emoji" in media.get("class", [])
        alt = (media.get("alt") or "").strip()
        caption = (media.get("title") or "").strip()
        if is_emoji and alt:
            representation = alt[:80]
        else:
            uri = (media.get("src") or media.get("data-src") or
                   media.get("href") or
                   (media.find("a", href=True) or {}).get("href") or "")
            absolute = urlsplit(urljoin("https://" + HOST + "/", uri))
            if not uri or absolute.scheme != "https" or not absolute.hostname or absolute.username or absolute.password:
                raise ValueError("unsupported_media_url")
            url = absolute.geturl()
            if len(url) > 1500:
                raise ValueError("media_url_too_long")
            label = {"img": "Image", "video": "Video", "audio": "Audio",
                     "iframe": "Embedded content"}.get(kind, "Attachment")
            description = (alt or caption)[:100]
            representation = f"[{label}{': ' + description if description else ''}: {url}]"
        media.replace_with(NavigableString(" " + representation + " "))
    parts = []
    def visit(n):
        if isinstance(n, NavigableString):
            if str(n).strip():
                parts.append(str(n).strip())
        elif getattr(n, "name", None):
            if n.name == "br":
                parts.append("\n")
            else:
                for child in n.children:
                    visit(child)
                if n.name in ("p", "div", "li"):
                    parts.append("\n")
    visit(clone)
    value = re.sub(r" *\n *", "\n", " ".join(parts)).strip()
    if not value:
        raise ValueError("empty_post_or_reply")
    if PRIVATE.search(value):
        raise ValueError("personal_identifier")
    if INCOMPLETE.search(value):
        raise ValueError("hidden_reply_expansion")
    return value


def _comments(doc):
    # Verified against public pages on 2026-11-22:
    # one li.ItemComment[id=Comment_...] per comment, 10 comments per full page.
    nodes = doc.select("li.ItemComment[id^='Comment_']")
    if not nodes:
        raise ValueError("mse_comment_structure_missing")
    ids = [node.get("id") for node in nodes]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate_mse_comment_id")
    return nodes


def _original_message(doc):
    messages = [node for node in doc.select(".Message")
                if not node.find_parent("li", class_="ItemComment")]
    if len(messages) != 1:
        raise ValueError("mse_original_message_ambiguous")
    return messages[0]


def _page_count(doc, base):
    # Use only the topic-specific numbered pager (never links in quoted posts).
    max_page = 1
    for a in doc.select(".NumberedPager a[href], .Pager a[href]"):
        dest = urlsplit(urljoin(base, a["href"]))
        if dest.netloc != HOST or dest.scheme != "https":
            continue
        if dest.path.rstrip("/") == urlsplit(base).path.rstrip("/"):
            max_page = max(max_page, 1)
        m = PAGE_RE.fullmatch(dest.path)
        if m and m[1] == source_id(base):
            max_page = max(max_page, int(m[3]))
    return max_page


def _load_page(base, page_num, html, fetch):
    requested = base if page_num == 1 else base.rstrip("/") + "/p" + str(page_num)
    raw = html if page_num == 1 else fetch(requested)
    doc = BeautifulSoup(raw, "html.parser")
    canonical = doc.select_one("link[rel='canonical'][href]")
    if not canonical:
        raise ValueError("missing_mse_canonical")
    canonical_url = urlsplit(urljoin(requested, canonical["href"]))
    if canonical_url.scheme != "https" or canonical_url.netloc != HOST:
        raise ValueError("mse_canonical_origin_mismatch")
    normal = canonical_url.path.rstrip("/")
    expected = urlsplit(requested).path.rstrip("/")
    if normal != expected:
        raise ValueError("mse_canonical_page_mismatch")
    return doc


def parse_topic_pages(expected_id, base, first_html, fetch):
    if source_id(base) != expected_id:
        raise ValueError("mse_source_id_mismatch")
    first = _load_page(base, 1, first_html, fetch)
    title_node = first.select_one("h1")
    if title_node is None:
        raise ValueError("mse_title_missing")
    title = _text(title_node)
    if len(title) > 200:
        raise ValueError("title_too_long")
    original = _text(_original_message(first))
    if len(original) > 30000 or not GAMBLING.search(title + " " + original):
        raise ValueError("not_problem_gambling")
    total_pages = _page_count(first, base)
    if total_pages > 1000:
        raise ValueError("mse_page_count_exceeded")
    first_comments = _comments(first)
    per_page = len(first_comments)
    if total_pages > 1 and per_page != 10:
        # Avoid deriving total from an unverified nonstandard page size.
        raise ValueError("mse_page_size_changed")
    if total_pages == 1:
        source_total = per_page
    else:
        # A tail request determines the source's actual reply count. The
        # stable 10-reply page size is then verified for every captured page.
        last = _load_page(base, total_pages, None, fetch)
        if _page_count(last, base) != total_pages:
            raise ValueError("mse_tail_pagination_changed")
        tail_count = len(_comments(last))
        if not 1 <= tail_count <= per_page:
            raise ValueError("mse_tail_count_invalid")
        source_total = (total_pages - 1) * per_page + tail_count
    target = min(source_total, MAX_REPLIES)
    if target < 1:
        raise ValueError("mse_no_replies")
    comments = []
    ids = set()
    pages_read = 0
    pages_needed = (target + per_page - 1) // per_page
    for index in range(1, pages_needed + 1):
        page = first if index == 1 else _load_page(base, index, None, fetch)
        if _page_count(page, base) != total_pages:
            raise ValueError("mse_pagination_changed")
        posts = first_comments if index == 1 else _comments(page)
        expected_n = per_page if index < total_pages else source_total - (total_pages - 1) * per_page
        if len(posts) != expected_n:
            raise ValueError("mse_page_comment_count_mismatch")
        for post in posts:
            ident = post.get("id")
            if ident in ids:
                raise ValueError("mse_duplicate_comment_across_pages")
            ids.add(ident)
            body_node = post.select_one(".Item-Body .Message, .Comment .Message")
            if body_node is None:
                raise ValueError("mse_reply_body_missing")
            body = _text(body_node)
            if len(body) > 12000:
                raise ValueError("reply_too_long")
            if len(comments) < target:
                comments.append({"body": body, "source_lang": "en"})
        pages_read = index
    if len(comments) != target:
        raise ValueError("mse_reply_count_mismatch")
    return ({"title": title, "body": original, "source_lang": "en",
             "comments": comments},
            {"source_total": source_total, "captured": target,
             "capped": source_total > MAX_REPLIES, "pages": pages_read})
