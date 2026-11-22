"""Parse the public PsychForums gambling addiction board and its phpBB topics."""

import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from gambling_forums import GAMBLING, MAX_CAPTURED_REPLIES, _required

HOST = "www.psychforums.com"
LISTING = f"https://{HOST}/gambling-addiction-forum-f204/"
TOPIC = re.compile(r"^/([a-z0-9-]+)/topic([0-9]+)\.html$")
POST_COUNT = re.compile(r"^\s*([0-9]+)\s+posts?\b")
PAGE_LABEL = re.compile(r"Page\s+([0-9]+)\s+of\s+([0-9]+)")
EXPERIENCE = re.compile(
    r"\b(?:i|my|me|gambl\w*|betting|relaps\w*|quit\w*|recover\w*|debt\w*|lost|losses)\b",
    re.I,
)


def source_id(url):
    parsed = urlsplit(url)
    match = TOPIC.fullmatch(parsed.path)
    if parsed.scheme != "https" or parsed.netloc != HOST or parsed.query or parsed.fragment or not match:
        raise ValueError("invalid_psychforums_topic_url")
    return match[2]


def discover(listing_url, html, excluded=(), maximum=60):
    if listing_url != LISTING:
        raise ValueError("invalid_psychforums_listing")
    page = BeautifulSoup(html, "html.parser")
    found = {}
    for anchor in page.select("ul.topiclist.topics a.topictitle[href]"):
        row = anchor.find_parent("dl")
        if not row or any("sticky" in name or "announce" in name for name in row.get("class", [])):
            continue
        reply_count = row.select_one("dd.posts")
        if not reply_count or not re.match(r"^\s*[1-9][0-9]*\b", reply_count.get_text(" ", strip=True)):
            continue
        if not EXPERIENCE.search(anchor.get_text(" ", strip=True)):
            continue
        url = urljoin(listing_url, anchor["href"])
        try:
            identifier = source_id(url)
        except ValueError:
            continue
        if identifier not in excluded:
            found.setdefault(identifier, url)
        if len(found) >= maximum:
            break
    return found


def _body(node):
    content = node.select_one(".postbody .content")
    if content is None:
        raise ValueError("psychforums_post_body_missing")
    for attribution in content.select("blockquote cite"):
        attribution.decompose()
    for emoji in content.select("img.smilies[alt], img.emoji[alt]"):
        emoji.replace_with(emoji["alt"])
    return _required(content, "psychforums_empty_post")


def parse_topic_pages(identifier, url, first_html, fetch):
    if source_id(url) != identifier:
        raise ValueError("psychforums_topic_id_mismatch")
    origin = url.removesuffix(".html")
    replies = []
    seen = set()
    total = title = body = None
    page_number, page_url, html = 1, url, first_html
    while True:
        page = BeautifulSoup(html, "html.parser")
        canonical = page.select_one('link[rel="canonical"][href]')
        if not canonical or urljoin(page_url, canonical["href"]) != page_url:
            raise ValueError("psychforums_canonical_mismatch")
        if not page.select_one('.crumb[data-forum-id="204"]'):
            raise ValueError("psychforums_topic_outside_gambling_board")
        pagination = page.select_one(".action-bar .pagination")
        count = POST_COUNT.match(pagination.get_text(" ", strip=True)) if pagination else None
        if not count or (total is not None and int(count[1]) != total):
            raise ValueError("psychforums_post_count_unverified")
        total = int(count[1])
        expected_pages = (total + 9) // 10
        label = PAGE_LABEL.search(pagination.get_text(" ", strip=True))
        active = pagination.select_one("li.active")
        if ((label and (int(label[1]), int(label[2])) != (page_number, expected_pages))
                or (expected_pages > 1
                    and (active is None or active.get_text(strip=True) != str(page_number)))):
            raise ValueError("psychforums_page_number_mismatch")
        expected_nodes = min(10, total - (page_number - 1) * 10)
        nodes = page.select("div.post[id]")
        if total < 2 or len(nodes) != expected_nodes:
            raise ValueError("psychforums_page_incomplete")
        for index, node in enumerate(nodes):
            native_id = node["id"]
            if not re.fullmatch(r"p[0-9]+", native_id) or native_id in seen:
                raise ValueError("psychforums_post_id_unverified")
            seen.add(native_id)
            if page_number == 1 and index == 0:
                title = _required(page.select_one("h1.topic-title"), "psychforums_title_missing")
                body = _body(node)
                if not GAMBLING.search(f"{title} {body}"):
                    raise ValueError("not_problem_gambling")
            elif len(replies) < MAX_CAPTURED_REPLIES:
                reply = _body(node)
                if len(reply) > 12000:
                    raise ValueError("reply_too_long")
                replies.append({"body": reply, "source_lang": "en"})
        if len(replies) == min(total - 1, MAX_CAPTURED_REPLIES):
            return (
                {"title": title, "body": body, "source_lang": "en", "comments": replies},
                {"pages": page_number, "source_total": total - 1, "captured": len(replies),
                 "capped": total - 1 > MAX_CAPTURED_REPLIES},
            )
        next_link = pagination.select_one('a[rel="next"][href]')
        page_number += 1
        next_url = f"{origin}/page{page_number}.html"
        if not next_link or urljoin(page_url, next_link["href"]) != next_url:
            raise ValueError("psychforums_next_page_missing")
        page_url, html = next_url, fetch(next_url)
