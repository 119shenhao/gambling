"""Live MSE parsing smoke, read-only and metadata-only output.

No forum body or user names are logged, persisted, or imported. Network calls
stay within public HTML pages; rights gate for republication remains disabled.
"""
import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from gambling_mse import parse_topic_pages, source_id
from bs4 import BeautifulSoup
from collections import Counter

SAMPLES = [
    "https://forums.moneysavingexpert.com/discussion/6200242/gambling-recovery-and-covid-job-loss",
    "https://forums.moneysavingexpert.com/discussion/6512900/redemption-the-journey-of-a-recovering-gambling-addict",
]
REQUEST_COUNT = 0

def fetch(url):
    global REQUEST_COUNT
    if (urlsplit(url).scheme != "https" or
            urlsplit(url).hostname != "forums.moneysavingexpert.com"):
        raise ValueError("cross_host_request")
    if REQUEST_COUNT:
        time.sleep(0.25)
    REQUEST_COUNT += 1
    req = Request(url, headers={
        "User-Agent":"GamblingCommunityReadOnlyProbe/1.0 (+public forum pages)",
        "Accept":"text/html",
    })
    try:
        with urlopen(req, timeout=25) as resp:
            if urlsplit(resp.geturl()).hostname != "forums.moneysavingexpert.com":
                raise ValueError("cross_host_redirect")
            payload = resp.read(2_000_001)
        if len(payload) > 2_000_000:
            raise ValueError("html_too_large")
        return payload
    except HTTPError as exc:
        raise ValueError("http_" + str(exc.code)) from None
    except (URLError, OSError, TimeoutError):
        raise ValueError("network_error") from None

def main():
    for url in SAMPLES:
        identifier = source_id(url)
        before = REQUEST_COUNT
        record = {"site":"moneysavingexpert", "source_id":identifier,
                  "read_only":True, "database_writes":False}
        try:
            first = fetch(url)
            doc = BeautifulSoup(first, "html.parser")
            bodies = doc.select("li.ItemComment .Message, .ItemDiscussion .Message")
            media = Counter()
            for body in bodies:
                clone = BeautifulSoup(str(body), "html.parser")
                for skipped in clone.select("blockquote, .Quote, .Signature, .UserSignature, .User-Signature, .PostSignature"):
                    skipped.decompose()
                for node in clone.select("img, video, iframe, audio, .attachment, [data-attachment]"):
                    tag = node.name
                    classes = sorted(node.get("class", []))[:4]
                    domain = ""
                    if tag == "img":
                        domain = urlsplit(node.get("src", "")).hostname or "relative"
                    media[(tag, tuple(classes), domain, bool(node.get("alt")),bool(node.get("title")))]+=1
            record["media_types"] = [{"tag":t,"classes":list(c),"src_host":h,"has_alt":a,"has_title":ti,"count":n} for (t,c,h,a,ti),n in media.most_common(20)]
            record["body_nodes"] = len(bodies)
            draft, meta = parse_topic_pages(identifier,url,first,fetch)
            record.update({"status":"parser_ok", "captured":len(draft["comments"]), **meta})
        except (ValueError, TypeError, KeyError) as error:
            record.update({"status":"parser_rejected", "reason":str(error)[:120]})
        record["http_requests"] = REQUEST_COUNT - before
        print(json.dumps(record,sort_keys=True),flush=True)

if __name__ == "__main__":
    main()
