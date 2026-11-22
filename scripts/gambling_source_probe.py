"""Read-only probe for prospective gambling support community sources.

Never imports content or logs personal posts; tests public HTTP reachability,
stable topic links, visible comment structures and pagination metadata only.
"""
import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup

TARGETS = [
    ("psychforums", "listing", "https://www.psychforums.com/gambling-addiction-forum-f204/"),
    ("psychforums", "single", "https://www.psychforums.com/gambling-addiction/topic126528.html"),
    ("psychforums", "paged", "https://www.psychforums.com/gambling-addiction/topic108461-50.html"),
    ("moneysavingexpert", "single", "https://forums.moneysavingexpert.com/discussion/6512900/redemption-the-journey-of-a-recovering-gambling-addict"),
    ("moneysavingexpert", "paged", "https://forums.moneysavingexpert.com/discussion/6512900/redemption-the-journey-of-a-recovering-gambling-addict/p49"),
    ("gamblinghelponline", "listing", "https://community.gamblinghelponline.org.au/s/"),
    ("evive", "listing", "https://community.getevive.app/"),
]
ALLOWED_HOSTS = {
    "psychforums": "www.psychforums.com",
    "moneysavingexpert": "forums.moneysavingexpert.com",
    "gamblinghelponline": "community.gamblinghelponline.org.au",
    "evive": "community.getevive.app",
}

def probe(site, role, url):
    record = {"site": site, "role": role, "url": url, "read_only": True}
    try:
        request = Request(url, headers={
            "User-Agent": "GamblingCommunityReadOnlyProbe/1.0 (+public forum pages)",
            "Accept": "text/html",
        })
        with urlopen(request, timeout=20) as res:
            final = res.geturl()
            if urlsplit(final).hostname != ALLOWED_HOSTS[site]:
                raise ValueError("cross_host_redirect")
            data = res.read(2_000_001)
            if len(data) > 2_000_000:
                raise ValueError("html_over_2mb")
            record["http_status"] = res.status
            record["final_path"] = urlsplit(final).path
        soup = BeautifulSoup(data, "html.parser")
        record["title_present"] = bool(soup.select_one("h1"))
        record["topic_links"] = len({
            urljoin(final, a["href"]).split("?")[0]
            for a in soup.select("a[href]")
            if re.search(r"/topic\d+|/discussion/\d+", a["href"], re.I)
        })
        record["post_containers"] = len(soup.select("div.post, article.post, .Comment, .comment, .Message, .ItemComment, [id^='post-']"))
        record["post_bodies"] = len(soup.select(".postbody .content, .post .content, .Message, .message, .userContent, .Item-Body, .Comment .Message"))
        record["pagination_links"] = len(soup.select("a[href*='/page'], a[href*='-10.html'], a[href*='/p2'], a[href*='/p49'], .pagination a"))
        summary = soup.get_text(" ", strip=True)
        m = re.search(r"\b(\d{1,5})\s+posts?\b", summary, re.I)
        record["declared_posts"] = int(m[1]) if m else None
        match = re.search(r"\bPage\s+(\d+)\s+of\s+(\d+)\b", summary, re.I)
        record["page_label"] = [int(match[1]), int(match[2])] if match else None
        record["html_bytes"] = len(data)
        # Never log body text, usernames, or comment contents.
    except HTTPError as e:
        record["error"] = "http_" + str(e.code)
    except (URLError, TimeoutError, ValueError, OSError) as e:
        record["error"] = str(e)[:80] if isinstance(e, ValueError) else "network_error"
    print(json.dumps(record, sort_keys=True), flush=True)

if __name__ == "__main__":
    selected = TARGETS
    if os.environ.get("MSE_ONLY") == "1":
        selected = [item for item in TARGETS if item[0] == "moneysavingexpert"]
    for entry in selected:
        probe(*entry)


def mse_structure_probe(url):
    """Emit HTML structural facts only, never forum post text or author data."""
    record = {"site": "moneysavingexpert", "mode": "structure", "path": urlsplit(url).path}
    try:
        req = Request(url, headers={"User-Agent": "GamblingCommunityReadOnlyProbe/1.0 (+public forum pages)", "Accept": "text/html"})
        with urlopen(req, timeout=25) as response:
            if urlsplit(response.geturl()).hostname != "forums.moneysavingexpert.com":
                raise ValueError("cross_host_redirect")
            payload = response.read(2_000_001)
        if len(payload) > 2_000_000:
            raise ValueError("html_over_2mb")
        page = BeautifulSoup(payload, "html.parser")
        selectors = [
            ".Comment", ".ItemComment", "li.Comment", "div.Comment", ".CommentBody",
            ".Message", ".Item-Body", ".ItemComment .Message", ".ItemComment .userContent",
            ".Comment .Message", ".Comment .userContent", ".Comment .Item-Body",
            ".DataList", ".DataList li", ".Discussion", ".PageInfo", ".NumberedPager",
            ".Pager", ".Pagination", ".page-numbers", ".js-comment", "[id^='Comment_']",
            "[data-commentid]", ".UserContent", ".userContent", ".Quote", "blockquote",
        ]
        record["selectors"] = {s: len(page.select(s)) for s in selectors if page.select(s)}
        candidates = page.select(".Comment, .ItemComment, [data-commentid], [id^='Comment_']")
        observations = []
        for n in candidates[:3]:
            chain = []
            parent = n
            for _ in range(4):
                if not getattr(parent, "name", None):
                    break
                chain.append({"tag": parent.name,
                              "classes": list(parent.get("class", []))[:8],
                              "attrs": sorted(x for x in parent.attrs if x in (
                                  "id", "data-commentid", "data-type", "data-id",
                                  "data-discussionid", "role"))})
                parent = parent.parent
            observations.append(chain)
        record["post_container_ancestry"] = observations
        navs = []
        for a in page.select("a[href]"):
            href = a.get("href", "")
            if re.search(r"/p\d+(?:/|[?#]|$)|[?&]page=\d+", href):
                full = urljoin(url, href)
                if urlsplit(full).hostname == "forums.moneysavingexpert.com":
                    navs.append(urlsplit(full).path)
        record["page_link_paths"] = list(dict.fromkeys(navs))[-8:]
        canonical = page.select_one("link[rel='canonical'][href]")
        record["canonical_path"] = urlsplit(canonical["href"]).path if canonical else None
        record["html_bytes"] = len(payload)
    except HTTPError as error:
        record["error"] = "http_" + str(error.code)
    except (URLError, OSError, TimeoutError, ValueError) as error:
        record["error"] = (str(error)[:80] if isinstance(error, ValueError)
                           else "network_error")
    print(json.dumps(record, sort_keys=True), flush=True)

if __name__ == "__main__":
    for target in [
        "https://forums.moneysavingexpert.com/discussion/6512900/redemption-the-journey-of-a-recovering-gambling-addict",
        "https://forums.moneysavingexpert.com/discussion/6512900/redemption-the-journey-of-a-recovering-gambling-addict/p2",
        "https://forums.moneysavingexpert.com/discussion/6200242/gambling-recovery-and-covid-job-loss"
    ]:
        mse_structure_probe(target)
