"""Independent gambling forum discovery and strict whole-thread HTML parser.

No request is issued on module import. Sites must be separately enabled for
collection only after content reuse permission and a live structural check.
"""
import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup, NavigableString

ORIGINS = {
    "gamcare": ("community.gamcare.org.uk", "/forum/"),
    "gamblingtherapy": ("gamblingtherapy.org", "/forum/topic/"),
}
GAMBLING = re.compile(r"\b(?:gambl(?:e|ing|er|ers)|betting|casino|slots?|roulette|"
                      r"relaps(?:e|ed)|quit(?:ting)?|recovery|debt|lost|losses)\b", re.I)
PRIVATE = re.compile(r"(?<!\d)(?:[+]?\d[ -]?){10,15}(?!\d)|"
                     r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", re.I)
INCOMPLETE = re.compile(r"\b(?:load more replies|show more replies|"
                        r"view hidden replies|read more replies)\b", re.I)
POST_SELECTOR = (
    ".wpforo-post, .wpf-post, article[id^='post-'], "
    ".bbp-reply, .bbp-topic, [id^='wpf-post-']"
)
CONTENT_SELECTOR = (
    ".wpforo-post-content, .wpf-post-content, .wpf-post-body, "
    ".bbp-reply-content, .bbp-topic-content"
)


def source_id(site, url):
    """Use the forum's canonical topic slug, never a generated random ID."""
    if site == "v2ex":
        from gambling_v2ex import source_id as v2ex_source_id
        return v2ex_source_id(url)
    if site == "moneysavingexpert":
        from gambling_mse import source_id as mse_source_id
        return mse_source_id(url)
    if site not in ORIGINS or not isinstance(url, str):
        raise ValueError("unsupported_source")
    parsed = urlsplit(url)
    host, prefix = ORIGINS[site]
    slug = parsed.path.rstrip("/").rsplit("/", 1)[-1]
    if (parsed.scheme != "https" or parsed.netloc != host or
            parsed.query or parsed.fragment or not parsed.path.startswith(prefix) or
            not re.fullmatch(r"[a-z0-9-]{1,128}", slug)):
        raise ValueError("invalid_topic_url")
    # Category/listing links aren't topics, even if their slugs look valid.
    if site == "gamcare":
        parts = parsed.path.strip("/").split("/")
        if len(parts) != 3 or parts[1] in {"paged", "page", "category"} or slug.isdigit():
            raise ValueError("not_topic_url")
    return slug


def discover(site, listing_url, html, excluded=(), maximum=60):
    """Return stable ID->canonical URL pairs without loading full thread bodies."""
    if site == "v2ex":
        from gambling_v2ex import discover as v2ex_discover
        return v2ex_discover(listing_url, html, excluded, maximum)
    if site == "moneysavingexpert":
        from gambling_mse import discover as mse_discover
        return mse_discover(listing_url, html, excluded, maximum)
    if site not in ORIGINS:
        raise ValueError("unsupported_source")
    root = urlsplit(listing_url)
    host, _ = ORIGINS[site]
    if root.scheme != "https" or root.netloc != host:
        raise ValueError("invalid_listing_host")
    page = BeautifulSoup(html, "html.parser")
    found = {}
    selectors = (
        ".wpforo-topic-title a[href], .wpf-topic-title a[href], "
        ".bbp-topic-title[href], a[href*='/forum/topic/'], "
        "a[href*='/forum/new-members-intros-forum/'], "
        "a[href*='/forum/recovery-diaries/']"
    )
    for a in page.select(selectors):
        if a.find_parent("nav") or a.find_parent("footer"):
            continue
        url = urljoin(listing_url, a.get("href", ""))
        try:
            key = source_id(site, url)
        except ValueError:
            continue
        if key in excluded or key in found:
            continue
        if (a.get_text(" ", strip=True) and len(found) < maximum):
            found[key] = url
    return found


def _visible_text(node):
    parts = []
    def walk(n):
        if isinstance(n, NavigableString):
            value = str(n)
            if value.strip():
                parts.append(value.strip())
        elif getattr(n, "name", None):
            if n.name in {"script", "style", "noscript", "button", "svg"}:
                return
            if n.name == "br":
                parts.append("\n")
                return
            for child in n.children:
                walk(child)
            if n.name in {"p", "div", "li", "blockquote"}:
                parts.append("\n")
    walk(node)
    return re.sub(r" *\n *", "\n", " ".join(parts)).strip()


def _required(node, reason):
    if node is None:
        raise ValueError(reason)
    if node.select_one("img, video, iframe, audio, [data-attachment], .attachment"):
        raise ValueError("uncollected_media")
    text = _visible_text(node)
    if not text:
        raise ValueError("empty_post_or_reply")
    if PRIVATE.search(text):
        raise ValueError("personal_identifier_in_public_content")
    if INCOMPLETE.search(text):
        raise ValueError("hidden_replies_or_expand_control")
    return text


def parse_topic(site, expected_id, page_url, html):
    """Fail closed on missing posts, unseen pagination or uncertain reply counts.

    The forum displays chronological flat replies. Mentions/quotes are *not*
    evidence of a parent reply; never invent a nested relationship.
    """
    if source_id(site, page_url) != expected_id:
        raise ValueError("source_id_mismatch")
    page = BeautifulSoup(html, "html.parser")
    canonical = page.select_one("link[rel='canonical'][href]")
    if canonical and source_id(site, canonical["href"]) != expected_id:
        raise ValueError("canonical_mismatch")
    title_node = page.select_one("h1.wpforo-topic-title, h1.wpf-topic-title, h1.entry-title, h1")
    if title_node is None:
        raise ValueError("title_missing")
    title = _required(title_node, "title_invalid")
    if len(title) > 200:
        raise ValueError("title_too_long")
    # A second page or an unexpanded 'load more' list is not a complete thread.
    if page.select_one("a.next.page-numbers, .wpf-next-page, .wpforo-pagination a.next, .bbp-pagination-links a.next"):
        raise ValueError("multipage_thread_not_supported")
    nodes = page.select(POST_SELECTOR)
    # Some themes wrap each wpForo post in another element matched by the
    # selector. Only use outermost containers to avoid duplicate replies.
    nodes = [n for n in nodes if not n.find_parent(lambda p: p in nodes)]
    if len(nodes) < 2:
        raise ValueError("missing_posts_or_replies")
    if len(nodes) > 50:
        raise ValueError("reply_limit_exceeded")
    bodies = []
    for node in nodes:
        content = node.select_one(CONTENT_SELECTOR)
        if content is None:
            raise ValueError("post_body_missing")
        bodies.append(_required(content, "post_body_invalid"))
    # Validate count when the theme exposes a count; refuse an incomplete tree.
    count_node = page.select_one(".wpforo-topic-stat, .wpf-topic-stat, .wpf-topic-posts")
    if count_node:
        match = re.search(r"\b(\d{1,4})\s+posts?\b", count_node.get_text(" ", strip=True), re.I)
        if match and int(match[1]) != len(nodes):
            raise ValueError("public_reply_count_mismatch")
    if len(bodies[0]) > 30000 or any(len(s) > 12000 for s in bodies[1:]):
        raise ValueError("text_length_exceeded")
    if not GAMBLING.search(title + " " + bodies[0]):
        raise ValueError("not_problem_gambling")
    return {
        "title": title,
        "body": bodies[0],
        "source_lang": "en",
        "comments": [{"body": content, "source_lang": "en"} for content in bodies[1:]],
    }


MAX_CAPTURED_REPLIES = 500
MAX_FORUM_PAGES = MAX_CAPTURED_REPLIES + 1  # allow a page with no replies plus 500 reply pages


def _post_nodes(page):
    nodes = page.select(POST_SELECTOR)
    return [node for node in nodes if not node.find_parent(lambda parent: parent in nodes)]


def _page_label(page):
    """wpForo displays 'Page N / M' for long threads, including page 2."""
    text = page.get_text(" ", strip=True)
    found = re.search(r"\bPage\s+(\d{1,4})\s*/\s*(\d{1,4})\b", text, re.I)
    return (int(found[1]), int(found[2])) if found else None


def _declared_post_count(page):
    """The topic-wide 'NN Posts' stat, not a user's individual post count."""
    stat = page.select_one(".wpforo-topic-stat, .wpf-topic-stat, .wpf-topic-posts")
    text = stat.get_text(" ", strip=True) if stat is not None else ""
    match = re.search(r"\b(\d{1,7})\s+posts?\b", text, re.I)
    if not match:
        # Some wpForo themes render the count in a standalone element.
        whole = page.get_text(" ", strip=True)
        match = re.search(r"\b(\d{1,7})\s+Posts\b", whole)
    return int(match[1]) if match else None


def parse_topic_pages(site, expected_id, page_url, first_html, fetch):
    """Walk stable GamCare forum pagination and return the first <=500 replies.

    The published response reports the original reply total and capped status
    separately. A missing/unavailable page before the 500th reply always fails.
    """
    if source_id(site, page_url) != expected_id:
        raise ValueError("source_id_mismatch")
    if site == "v2ex":
        from gambling_v2ex import parse_topic_pages as v2ex_pages
        return v2ex_pages(expected_id,page_url,first_html,fetch)
    if site == "moneysavingexpert":
        from gambling_mse import parse_topic_pages as mse_pages
        return mse_pages(expected_id, page_url, first_html, fetch)
    if site != "gamcare":
        raise ValueError("long_pagination_adapter_unavailable")
    base = page_url.rstrip("/") + "/"
    total_posts = None
    page_count = None
    replies = []
    seen_ids = set()
    title = first_body = None
    page_number = 1
    while page_number <= MAX_FORUM_PAGES:
        url = base if page_number == 1 else base + "paged/" + str(page_number) + "/"
        raw = first_html if page_number == 1 else fetch(url)
        page = BeautifulSoup(raw, "html.parser")
        label = _page_label(page)
        if label:
            if label[0] != page_number or label[1] < page_number:
                raise ValueError("pagination_number_mismatch")
            if page_count is not None and page_count != label[1]:
                raise ValueError("pagination_total_changed")
            page_count = label[1]
        elif page_number > 1:
            raise ValueError("pagination_label_missing")
        declared = _declared_post_count(page)
        if declared is None or declared < 2:
            raise ValueError("forum_total_posts_unavailable")
        if total_posts is None:
            total_posts = declared
        elif total_posts != declared:
            raise ValueError("source_reply_total_changed")
        nodes = _post_nodes(page)
        if not nodes:
            raise ValueError("empty_forum_page")
        if page_number == 1:
            title_node = page.select_one("h1.wpforo-topic-title, h1.wpf-topic-title, h1.entry-title, h1")
            if title_node is None:
                raise ValueError("title_missing")
            title = _required(title_node, "title_invalid")
            if len(title) > 200:
                raise ValueError("title_too_long")
            content = nodes[0].select_one(CONTENT_SELECTOR)
            first_body = _required(content, "post_body_invalid")
            if len(first_body) > 30000 or not GAMBLING.search(title + " " + first_body):
                raise ValueError("invalid_gambling_topic")
            nodes = nodes[1:]
        for node in nodes:
            content = node.select_one(CONTENT_SELECTOR)
            body = _required(content, "post_body_invalid")
            if len(body) > 12000:
                raise ValueError("reply_too_long")
            native_id = node.get("id") or ""
            if native_id:
                if native_id in seen_ids:
                    raise ValueError("duplicate_native_reply_id")
                seen_ids.add(native_id)
            if len(replies) < MAX_CAPTURED_REPLIES:
                replies.append({"body": body, "source_lang": "en"})
            if len(replies) >= MAX_CAPTURED_REPLIES:
                break
        wanted = min(total_posts - 1, MAX_CAPTURED_REPLIES)
        if len(replies) == wanted:
            return ({"title": title, "body": first_body, "source_lang": "en",
                     "comments": replies},
                    {"source_total": total_posts - 1, "captured": len(replies),
                     "capped": total_posts - 1 > MAX_CAPTURED_REPLIES,
                     "pages": page_number})
        if page_count is not None and page_number >= page_count:
            raise ValueError("forum_reply_count_mismatch")
        if page_count is None:
            raise ValueError("pagination_required_but_unavailable")
        page_number += 1
    raise ValueError("forum_page_limit_exceeded")
