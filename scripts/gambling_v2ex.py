"""Strict public HTML parser for V2EX problem-gambling threads (DEV only).

No requests on import. Flat replies stay flat. No account or API tokens used.
Source remains disabled until real Runner and D1 end-to-end verification.
"""
import re
from urllib.parse import parse_qs, urljoin, urlsplit
from bs4 import BeautifulSoup, NavigableString

HOST = "www.v2ex.com"
TOPIC = re.compile(r"^/t/([1-9]\d{0,11})/?$")
GAMBLING = re.compile(r"戒赌|复赌|赌博|赌瘾|赌债|网赌|赌球|老虎机|赌徒|输光|上岸")
PRIVATE = re.compile(r"(?<!\d)(?:[+]?\d[ -]?){10,15}(?!\d)|[\w.+-]+@[\w.-]+\.[a-z]{2,}",re.I)
MAX_CAPTURED = 500
MAX_PAGES = 501


def source_id(url):
    parsed = urlsplit(url)
    matched = TOPIC.fullmatch(parsed.path)
    if (parsed.scheme != "https" or parsed.netloc != HOST or
            parsed.query or parsed.fragment or not matched):
        raise ValueError("invalid_v2ex_topic_url")
    return matched.group(1)


def discover(listing_url, html, excluded=(), maximum=60):
    parsed = urlsplit(listing_url)
    if parsed.scheme != "https" or parsed.netloc != HOST:
        raise ValueError("invalid_v2ex_listing_host")
    doc = BeautifulSoup(html,"html.parser")
    found = {}
    for anchor in doc.select("a[href*='/t/']"):
        if anchor.find_parent(["nav","footer"]):
            continue
        url = urljoin(listing_url,anchor.get("href","")).split("?",1)[0]
        try:
            key = source_id(url)
        except ValueError:
            continue
        label = anchor.get_text(" ",strip=True)
        if not GAMBLING.search(label) or key in excluded or key in found:
            continue
        found[key] = url
        if len(found) >= maximum:
            break
    return found


def _text(node):
    clone=BeautifulSoup(str(node),"html.parser")
    for child in clone.select("script, style, noscript, button, svg"):
        child.decompose()
    for media in clone.select("img, video, iframe, audio, [data-attachment]"):
        if media.parent is None:
            continue
        if media.name != "img":
            raise ValueError("v2ex_uncollected_media")
        alt=(media.get("alt") or "").strip()
        src=(media.get("src") or "").strip()
        if alt and not src:
            replacement=alt
        else:
            dest=urlsplit(urljoin("https://"+HOST+"/",src))
            if (not src or dest.scheme!="https" or not dest.hostname or
                    dest.username or dest.password or len(dest.geturl())>1500):
                raise ValueError("v2ex_invalid_media_url")
            replacement=("[Image: "+dest.geturl()+"]" if not alt else
                         "[Image: "+alt[:90]+" "+dest.geturl()+"]")
        media.replace_with(NavigableString(" "+replacement+" "))
    parts=[]
    def walk(n):
        if isinstance(n,NavigableString):
            if str(n).strip():
                parts.append(str(n).strip())
        elif getattr(n,"name",None):
            if n.name=="br":
                parts.append("\n")
            else:
                for child in n.children:
                    walk(child)
                if n.name in ("p","div","li","blockquote"):
                    parts.append("\n")
    walk(clone)
    value=re.sub(r" *\n *","\n"," ".join(parts)).strip()
    if not value:
        raise ValueError("v2ex_empty_text")
    # Published posts sometimes mention contact details. Do not expose these
    # in the imported topic, but also do not drop an otherwise complete
    # 251-reply recovery discussion merely because one reply contains them.
    # Same sanitized text flows to staging, dev D1 and exact public readback.
    if PRIVATE.search(value):
        value = PRIVATE.sub("[联系方式已隐藏]", value)
        if not value.replace("[联系方式已隐藏]", "").strip():
            raise ValueError("v2ex_only_private_identifier")
    return value


def _reply_nodes(doc):
    nodes=doc.select(".cell[id^='r_']")
    if not nodes:
        # Some V2EX layouts set the ID on the cell's inner wrapper.
        nodes=doc.select("[id^='r_']")
    nodes=[n for n in nodes if not n.find_parent(lambda p:p in nodes)]
    if len({node.get("id") for node in nodes})!=len(nodes):
        raise ValueError("v2ex_duplicate_reply_on_page")
    return nodes


def _reply_total(doc):
    text=doc.get_text(" ",strip=True)
    matches=re.findall(r"\b(\d{1,7})\s+repl(?:y|ies)\b",text,re.I)
    return int(matches[0]) if matches else None


def _page_count(doc,base):
    pages={1}
    for link in doc.select("a[href]"):
        dest=urlsplit(urljoin(base,link["href"]))
        if (dest.scheme!="https" or dest.hostname!=HOST or
                not TOPIC.fullmatch(dest.path) or
                TOPIC.fullmatch(dest.path).group(1)!=source_id(base)):
            continue
        params=parse_qs(dest.query)
        if set(params) != {"p"} or len(params["p"])!=1:
            continue
        raw=params["p"][0]
        if re.fullmatch(r"[1-9]\d{0,3}",raw):
            pages.add(int(raw))
    return max(pages)


def _first_post(doc):
    title=doc.select_one("h1")
    if title is None:
        raise ValueError("v2ex_title_missing")
    title_text=_text(title)
    # Supplements must be retained in chronological order rather than silently
    # discarded. Only the verified first-page topic body & subtle supplements.
    main=[n for n in doc.select(".topic_content")
          if not n.find_parent(class_="subtle")]
    if len(main)!=1:
        raise ValueError("v2ex_original_body_ambiguous")
    text=_text(main[0])
    for section in doc.select(".subtle .topic_content"):
        text+="\n\n"+_text(section)
    if len(title_text)>200 or len(text)>30000:
        raise ValueError("v2ex_topic_too_long")
    if not GAMBLING.search(title_text+" "+text):
        raise ValueError("not_problem_gambling")
    return title_text,text


def parse_topic_pages(expected_id,base,first_html,fetch):
    if source_id(base)!=expected_id:
        raise ValueError("v2ex_source_id_mismatch")
    first=BeautifulSoup(first_html,"html.parser")
    title,body=_first_post(first)
    total=_reply_total(first)
    pages=_page_count(first,base)
    if not total or total>1_000_000 or pages>MAX_PAGES:
        raise ValueError("v2ex_reply_count_unavailable")
    first_nodes=_reply_nodes(first)
    per_page=len(first_nodes)
    if not per_page or per_page>200 or (pages>1 and total<=per_page):
        raise ValueError("v2ex_page_size_unverified")
    expected_pages=(total+per_page-1)//per_page
    if expected_pages!=pages:
        raise ValueError("v2ex_reply_pages_mismatch")
    target=min(total,MAX_CAPTURED)
    need_pages=(target+per_page-1)//per_page
    seen=set()
    replies=[]
    for number in range(1,need_pages+1):
        doc=(first if number==1 else
             BeautifulSoup(fetch(base+"?p="+str(number)),"html.parser"))
        if _page_count(doc,base)!=pages:
            raise ValueError("v2ex_pagination_changed")
        later_total=_reply_total(doc)
        if later_total is not None and later_total!=total:
            raise ValueError("v2ex_reply_total_changed")
        nodes=first_nodes if number==1 else _reply_nodes(doc)
        expected=(per_page if number<pages else total-(pages-1)*per_page)
        if len(nodes)!=expected:
            raise ValueError("v2ex_reply_page_incomplete")
        for node in nodes:
            reply_id=node.get("id")
            if not reply_id or reply_id in seen:
                raise ValueError("v2ex_duplicate_reply_across_pages")
            seen.add(reply_id)
            content=node.select_one(".reply_content")
            if content is None:
                raise ValueError("v2ex_reply_body_missing")
            body_text=_text(content)
            if len(body_text)>12000:
                raise ValueError("v2ex_reply_too_long")
            replies.append({"body":body_text,"source_lang":"zh"})
    if len(replies)!=target:
        raise ValueError("v2ex_total_reply_mismatch")
    return ({"title":title,"body":body,"source_lang":"zh","comments":replies},
            {"source_total":total,"captured":target,"capped":total>MAX_CAPTURED,
             "pages":need_pages})
