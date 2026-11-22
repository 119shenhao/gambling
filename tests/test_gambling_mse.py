"""MoneySavingExpert parser contract checks with entirely fictional local HTML."""
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import gambling_mse as mse
from gambling_forums import source_id, discover, parse_topic_pages
import gambling_collect as collect

BASE = ("https://forums.moneysavingexpert.com/discussion/6512900/"
        "redemption-the-journey-of-a-recovering-gambling-addict")


def sample(page=1, total_pages=3, last_count=4):
    url = BASE if page == 1 else BASE + "/p" + str(page)
    count = last_count if page == total_pages else 10
    first = ('<div class="ItemDiscussion"><div class="Item-Body">'
             '<div class="Message userContent"><p>I am quitting gambling.</p>'
             '</div></div></div>') if page == 1 else ""
    comments = "".join(
        f'<li class="Item ItemComment" id="Comment_{page * 100+i}">'
        f'<div class="Comment"><div class="Item-Body">'
        f'<div class="Message userContent"><blockquote>Quoted</blockquote>'
        f'<p>Recovery reply {page}-{i} with real progress.</p>'
        f'<div class="Signature">Signature omitted</div>'
        f'</div></div></div></li>' for i in range(count)
    )
    return (f'<html><head><link rel="canonical" href="{url}"></head><body>'
            f'<h1>Gambling recovery diary</h1>{first}'
            f'<div class="NumberedPager"><a href="{BASE}/p2">2</a>'
            f'<a href="{BASE}/p{total_pages}">Last</a></div>'
            f'<ul class="MessageList DataList Comments">{comments}</ul></body></html>')


class MSEParserTests(unittest.TestCase):
    def test_numeric_stable_source_id(self):
        self.assertEqual(source_id("moneysavingexpert", BASE), "6512900")
        for bad in (BASE + "/p2", BASE+"?test=1",
                    "https://other.example/discussion/6512900/recovery"):
            with self.assertRaises(ValueError):
                source_id("moneysavingexpert", bad)

    def test_discover_filters_generic_debt_and_duplicates(self):
        html = (f'<a href="{BASE}">Gambling recovery diary</a>'
                f'<a href="{BASE}">Gambling recovery diary</a>'
                f'<a href="/discussion/12345/unrelated">Car payment debt</a>')
        self.assertEqual(discover("moneysavingexpert",
                         "https://forums.moneysavingexpert.com/categories/debt-free-diaries",
                         html), {"6512900": BASE})

    def test_page_integrity_cleans_quotes_and_signatures(self):
        by_page = {p: sample(p) for p in range(1,4)}
        draft, meta = parse_topic_pages("moneysavingexpert", "6512900", BASE,
            by_page[1], lambda url: by_page[int(url.rsplit("/p",1)[-1])])
        self.assertEqual(meta, {"source_total":24,"captured":24,"capped":False,"pages":3})
        self.assertEqual(len(draft["comments"]),24)
        self.assertNotIn("Quoted", draft["comments"][0]["body"])
        self.assertNotIn("Signature omitted", draft["comments"][0]["body"])
        self.assertEqual(collect.validate(draft),24)

    def test_501_replies_capped_at_500(self):
        calls = []
        def fetch(url):
            p=int(url.rsplit("/p",1)[-1])
            calls.append(p)
            return sample(p, total_pages=51,last_count=1)
        draft, meta=mse.parse_topic_pages("6512900",BASE,
            sample(total_pages=51,last_count=1),fetch)
        self.assertEqual(meta, {"source_total":501,"captured":500,"capped":True,"pages":50})
        self.assertEqual(len(draft["comments"]),500)
        self.assertEqual(collect.validate(draft),500)
        self.assertNotIn(52,calls)

    def test_missing_middle_page_rejected(self):
        def fetch(url):
            p=int(url.rsplit("/p",1)[-1])
            if p==2:
                raise ValueError("http_404")
            return sample(p)
        with self.assertRaisesRegex(ValueError, "http_404"):
            mse.parse_topic_pages("6512900",BASE,sample(),fetch)

    def test_duplicate_native_comment_rejected(self):
        first=sample()
        second=sample(2).replace("Comment_200", "Comment_100")
        def fetch(url):
            p=int(url.rsplit("/p",1)[-1])
            return second if p==2 else sample(p)
        with self.assertRaisesRegex(ValueError,"duplicate_comment"):
            mse.parse_topic_pages("6512900",BASE,first,fetch)

    def test_sensitive_reply_rejected(self):
        bad=sample(total_pages=1,last_count=1).replace(
            "Recovery reply 1-0 with real progress.", "Email me at test@example.com")
        with self.assertRaisesRegex(ValueError,"personal_identifier"):
            mse.parse_topic_pages("6512900",BASE,bad,Mock())

    def test_unapproved_source_never_collectible(self):
        obj={"approved":False, "parser_verified":True,"reuse_allowed":True,
             "permission_evidence":"not granted"}
        self.assertFalse(collect.available(obj))


if __name__=="__main__":
    unittest.main()
