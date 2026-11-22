"""Read-only Chinese gambling forum feasibility probe.

Only public HTTPS GET to exact host allowlist. Never writes/exports user
content or identifiers, bypasses sign-in, or calls production/import APIs.
Outputs aggregate structural counts needed to implement strict adapters.
"""
import json
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup

TARGETS = [
    ("v2ex", "https://www.v2ex.com/t/1121755?p=1"),
    ("v2ex", "https://www.v2ex.com/t/1121755?p=2"),
    ("v2ex", "https://www.v2ex.com/t/1121755?p=3"),
    ("v2ex", "https://www.v2ex.com/tag/%E8%B5%8C%E5%8D%9A"),
    ("douban", "https://www.douban.com/group/586083/"),
]
HOSTS = {"v2ex": {"www.v2ex.com"}, "douban": {"www.douban.com"}}
SELECTORS = {
    "v2ex": {
        "heading": ["h1", ".header h1"],
        "topic": [".topic_content", "#topic_content", ".subtle .topic_content"],
        "supplements": [".subtle", ".topic_content"],
        "replies": [".cell[id^='r_']", "[id^='r_']", ".reply_content"],
        "pager": ["a[href*='?p=']", "a[href*='&p=']", ".page_normal", ".page_current"],
        "discovery": ["a[href^='/t/']", "a[href*='v2ex.com/t/']"],
    },
    "douban": {
        "heading": ["h1", "h2"],
        "topic": [".topic-content", ".topic-doc", ".topic-richtext"],
        "replies": [".reply-doc", ".reply-item", ".comment-item", "li.comment-item"],
        "pager": ["a[href*='start=']", "a[href*='?page=']", ".paginator a"],
        "discovery": ["a[href*='/group/topic/']"],
    },
}

def fetch(site, url):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in HOSTS[site]:
        raise ValueError("source_host_not_allowed")
    request = Request(url, headers={
        "User-Agent": "GamblingCommunitySourceResearch/1.0 (public readonly HTML)",
        "Accept": "text/html",
    })
    try:
        with urlopen(request, timeout=20) as response:
            final = urlsplit(response.geturl())
            if final.scheme != "https" or final.hostname not in HOSTS[site]:
                raise ValueError("unsafe_source_redirect")
            data = response.read(2_000_001)
            status = response.status
            mime = response.headers.get("Content-Type","")
        if len(data) > 2_000_000:
            raise ValueError("source_html_too_large")
        if "html" not in mime.lower():
            raise ValueError("not_html")
        return status, data
    except HTTPError as exc:
        raise ValueError("http_" + str(exc.code)) from None
    except (URLError, TimeoutError, OSError):
        raise ValueError("network_error_or_timeout") from None

def probe(site, url):
    record = {"event":"chinese_source_probe", "source":site,
              "path":urlsplit(url).path, "query_page":urlsplit(url).query,
              "read_only":True, "database_writes":False}
    try:
        status, data = fetch(site,url)
        doc = BeautifulSoup(data, "html.parser")
        record.update({"status":"ok", "http_status":status,
                       "html_bytes":len(data), "has_login_form":bool(doc.select_one("form[action*='login'], form[action*='passport']"))})
        for kind, selectors in SELECTORS[site].items():
            record[kind+"_counts"] = {
                s:len(doc.select(s)) for s in selectors
            }
        if site == "v2ex":
            all_text = doc.get_text(" ", strip=True)
            total = re.search(r"(?<!\\d)(\\d{1,6})\\s+replies\\b",all_text,re.I)
            record["declared_replies"] = int(total.group(1)) if total else None
            # Only aggregate the number of distinct reply containers.
            ids = [n.get("id") for n in doc.select("[id^='r_']")]
            record["reply_ids_unique"] = len(ids) == len(set(ids))
        else:
            # No topic IDs or user content are printed; aggregate public links only.
            links = set()
            for a in doc.select("a[href*='/group/topic/']"):
                dest=urlsplit(urljoin(url,a.get("href","")))
                if dest.scheme=="https" and dest.hostname in HOSTS[site] and re.fullmatch(r"/group/topic/\\d+/?",dest.path):
                    links.add(dest.path)
            record["public_topic_links"]=len(links)
    except ValueError as exc:
        record.update({"status":"unavailable", "reason":str(exc)})
    print(json.dumps(record,ensure_ascii=False,sort_keys=True),flush=True)

def main():
    for site,url in TARGETS:
        probe(site,url)
        time.sleep(.4)

if __name__=="__main__":
    main()
