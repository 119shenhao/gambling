"""Public, standalone stories with per-site text and catalog boundaries."""
import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

ARTICLE_SOURCES = {
    "tacklinggamblingstigma": (
        "tacklinggamblingstigma.com", r"/contributor/([a-z0-9-]+)/?", "main h1, h1",
    ),
    "agr": (
        "www.agr.org.au", r"/stories/([a-z0-9-]+)/?", "main h1",
    ),
    "gamblingwithlives": (
        "www.gamblingwithlives.org", r"/([a-z][a-z-]{2,99})/?",
        "main article .entry-title, main article h1, main article h2",
    ),
    "australiadss": (
        "www.dss.gov.au", r"/gambling/gambling-support-services/([a-z0-9-]+-story)/?",
        "main h1",
    ),
}

GAMBLING = re.compile(r"\b(?:gambl\w*|betting|pokies|poker machines|casino|bookies)\b", re.I)
PRIVATE = re.compile(r"(?<!\d)(?:[+]?\d[ -]?){10,15}(?!\d)|[\w.+-]+@[\w.-]+\.[a-z]{2,}", re.I)


def source_id(site, url):
    host, pattern, _ = ARTICLE_SOURCES[site]
    parsed = urlsplit(url)
    match = re.fullmatch(pattern, parsed.path)
    if (parsed.scheme != "https" or parsed.netloc != host or not match
            or parsed.query or parsed.fragment or len(match[1]) > 128):
        raise ValueError("invalid_story_url")
    return match[1]


def discover(site, listing_url, html, excluded=(), maximum=60):
    root = urlsplit(listing_url)
    if root.scheme != "https" or root.netloc != ARTICLE_SOURCES[site][0]:
        raise ValueError("invalid_story_listing_host")
    doc = BeautifulSoup(html, "html.parser")
    found = {}
    for anchor in doc.select("main a[href]"):
        if anchor.find_parent(["nav", "footer", "aside"]):
            continue
        target = urljoin(listing_url, anchor["href"])
        try:
            ident = source_id(site, target)
        except ValueError:
            continue
        if site == "gamblingwithlives" and not re.search(
                r"\baged\s+\d+\b", anchor.get_text(" ", strip=True), re.I):
            continue
        if ident not in excluded:
            found.setdefault(ident, target)
        if len(found) >= maximum:
            break
    return found


def _paragraphs(node):
    # Keep visible story text. The footer and interactive sharing UI are not story text.
    blocks = []
    for p in node.select("p, li, blockquote, h2, h3, h4, figcaption"):
        if p.find_parent(["li", "blockquote", "figcaption"]) or p.find_parent(
                ["script", "style", "aside", "nav", "button"]):
            continue
        value = p.get_text(" ", strip=True)
        if value:
            blocks.append(value)
    return blocks


def _sections(site, doc):
    if site == "tacklinggamblingstigma":
        sections = []
        for quote in doc.select("main section.quote"):
            section = quote.select_one(".quote-body, .collapse .card-body")
            if section is None:
                raise ValueError("story_quote_transcript_missing")
            sections.append(section)
        return sections
    if site == "agr":
        return [node for node in doc.select("main [data-testid='richTextElement']")
                if len(node.select("p")) >= 4]
    if site == "gamblingwithlives":
        return doc.select("main article .entry-content")
    return [node for node in doc.select("main .ct-site-page__content .ct-basic-content")
            if len(node.select("p")) >= 4]


def parse_story(site, expected_id, page_url, html):
    if source_id(site, page_url) != expected_id:
        raise ValueError("story_id_mismatch")
    doc = BeautifulSoup(html, "html.parser")
    canonical = doc.select_one("link[rel='canonical'][href]")
    if not canonical or source_id(site, urljoin(page_url, canonical["href"])) != expected_id:
        raise ValueError("story_canonical_mismatch")
    headline = doc.select_one(ARTICLE_SOURCES[site][2])
    if headline is None:
        raise ValueError("story_title_missing")
    title = headline.get_text(" ", strip=True)
    sections = _sections(site, doc)
    if not sections or (site != "tacklinggamblingstigma" and len(sections) != 1):
        raise ValueError("story_text_container_missing_or_ambiguous")
    blocks = [part for section in sections for part in _paragraphs(section) if part != title]
    if len(blocks) < 3 or sum(map(len, blocks)) < 220:
        raise ValueError("story_body_incomplete")
    if not GAMBLING.search(" ".join([title, *blocks])):
        raise ValueError("not_problem_gambling")
    if PRIVATE.search(" ".join([title, *blocks])):
        raise ValueError("personal_identifier_in_public_content")
    # Source identity remains in the collection receipt, never append metadata to the story.
    body = "\n\n".join(blocks)
    return {"title": title, "body": body, "source_lang": "en", "comments": []}
