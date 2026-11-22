"""Read-only access and HTML shape checks for authorized story sources."""
from concurrent.futures import ThreadPoolExecutor
import json
import re
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from bs4 import BeautifulSoup

TARGETS = {
    "mumsnet": [
        "https://www.mumsnet.com/talk/substance_addiction_",
        "https://www.mumsnet.com/talk/substance_addiction_/5534704-partner-has-admitted-to-gambling-70k-worth-of-debt?page=1",
        "https://www.mumsnet.com/talk/substance_addiction_/5534704-partner-has-admitted-to-gambling-70k-worth-of-debt?page=2",
        "https://www.mumsnet.com/talk/relationships/5581276-partner-repeatedly-hiding-gambling-debts-and-i-feel-strangely-calm"
    ],
    "myfico": [
        "https://ficoforums.myfico.com/t5/Bankruptcy/bd-p/bankruptcy",
        "https://ficoforums.myfico.com/t5/Bankruptcy/Income-Increase-During-Chapter-13/td-p/4832222",
        "https://ficoforums.myfico.com/t5/Bankruptcy/My-1-Year-Past-Discharge/td-p/6465004"
    ],
    "tacklinggamblingstigma": [
        "https://tacklinggamblingstigma.com/contributors/",
        "https://tacklinggamblingstigma.com/contributor/ben/",
        "https://tacklinggamblingstigma.com/contributor/rachel/",
        "https://tacklinggamblingstigma.com/contributor/julie/"
    ],
    "agr": [
        "https://www.agr.org.au/stories",
        "https://www.agr.org.au/stories/sunenna",
        "https://www.agr.org.au/stories/jacob"
    ],
    "gamblingwithlives": [
        "https://www.gamblingwithlives.org/remembering/",
        "https://www.gamblingwithlives.org/newsletter/inquests-gareth-and-stephen/"
    ],
    "gamblingcommission": [
        "https://www.gamblingcommission.gov.uk/report/lived-experiences-of-affected-others-qualitative-research",
        "https://www.gamblingcommission.gov.uk/report/lived-experiences-of-affected-others-qualitative-research/consequences",
        "https://www.gamblingcommission.gov.uk/about-us/guide/page/4-participants-journeys-with-adverse-or-severe-consequences-from-gambling"
    ],
    "australiadss": [
        "https://www.dss.gov.au/gambling/gambling-support-services",
        "https://www.dss.gov.au/gambling/gambling-support-services/matthews-story"
    ]
}

SELECTORS = (
    "main", "article", "h1", "main h1", "main p", "article p",
    "[data-testid]", "[itemprop='articleBody']", ".post-content", ".post__content",
    ".message-body", ".lia-message-body-content", ".lia-message-view-wrapper",
    ".lia-quilt-row-main", ".lia-thread-reply", "div[id^='message']", ".lia-paging-full",
    ".entry-content", ".post-content", ".wp-block-post-content",
    "[data-testid='richTextElement']", ".field--name-body", ".field--type-text-with-summary",
    "main .govuk-grid-column-two-thirds", ".govuk-body",
)

def summarize(target):
    site, url = target
    record = {"site": site, "path": urlsplit(url).path, "page": urlsplit(url).query}
    try:
        req = Request(url, headers={"User-Agent": "GamblingCommunityCollector/2.0 (public pages)",
                                    "Accept": "application/json,text/html"})
        with urlopen(req, timeout=18) as response:
            final = urlsplit(response.geturl())
            if final.scheme != "https" or final.hostname != urlsplit(url).hostname:
                raise ValueError("unexpected_redirect")
            data = response.read(4_000_001)
        if len(data) > 4_000_000:
            raise ValueError("source_response_too_large")
        doc = BeautifulSoup(data, "html.parser")
        record["html_bytes"] = len(data)
        record["same_host_final_path"] = final.path
        record["shape"] = {s: n for s in SELECTORS if (n := len(doc.select(s)))}
        nodes = doc.select("main p, article p, .lia-message-body-content")
        classes = {}
        for node in nodes[:180]:
            for p in list(node.parents)[:5]:
                if not p.name or p.name in {"body", "html"}:
                    break
                labels = [c for c in p.get("class", [])
                          if re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{2,70}", c)]
                key = p.name + ("." + ".".join(labels[:4]) if labels else "")
                classes[key] = classes.get(key, 0) + 1
        record["body_ancestors"] = sorted(classes.items(), key=lambda item: -item[1])[:22]
        tests = {}
        for node in doc.select("[data-testid]"):
            name = node["data-testid"]
            if re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{2,70}", name):
                tests[name] = tests.get(name, 0) + 1
        record["markers"] = sorted(tests.items(), key=lambda item: -item[1])[:35]
        links = set()
        for a in doc.select("main a[href], article a[href]"):
            link = urlsplit(urljoin(url, a["href"]))
            if (link.hostname == final.hostname and
                    re.search(r"/(?:contributor/|stories/|newsletter/|td-p/|talk/|report/|gambling-support-services/)", link.path)):
                links.add((link.path, link.query if re.fullmatch(r"page=[0-9]+", link.query) else ""))
        record["links"] = len(links)
        record["page_numbers"] = sorted(int(q.split("=")[1]) for _, q in links if q)[:15]
        visible = doc.get_text(" ", strip=True)
        m = re.search(r"\b([0-9,]{1,7})\s+repl(?:y|ies)\b", visible, re.I)
        record["declared_replies"] = int(m[1].replace(",", "")) if m else None
    except HTTPError as error:
        record["error"] = f"http_{error.code}"
    except ValueError as error:
        record["error"] = str(error)
    except (TimeoutError, OSError):
        record["error"] = "network_error_or_timeout"
    return record

def probe():
    targets = [(site, url) for site, urls in TARGETS.items() for url in urls]
    with ThreadPoolExecutor(max_workers=7) as workers:
        for record in workers.map(summarize, targets):
            print("story_probe=" + json.dumps(record, sort_keys=True), flush=True)
