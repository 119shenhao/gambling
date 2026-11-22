"""Synthetic strict V2EX parser contract tests; no external user data."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import gambling_v2ex as v2

BASE="https://www.v2ex.com/t/12345"

def page(p=1,pages=3,tail=4):
    n=tail if p==pages else 10
    main=('<h1>戒赌经历分享</h1><div class="topic_content">我曾沉迷网赌，决定戒赌。</div>'
          '<div class="subtle"><div class="topic_content">现在开始康复。</div></div>') if p==1 else ""
    pager="".join('<a href="/t/12345?p='+str(i)+'">'+str(i)+'</a>' for i in range(1,pages+1))
    rows="".join('<div class="cell" id="r_'+str(p*100+i)+'">'
                 '<div class="reply_content">加油，别再赌了 '+str(p)+'/'+str(i)+'</div></div>'
                 for i in range(n))
    declared=(pages-1)*10+tail
    return ('<html><body>'+main+'<div class="header">'+str(declared)
            +' replies</div>'+pager+rows+'</body></html>')

class V2EXParserTests(unittest.TestCase):
    def test_stable_source_id_requires_exact_https_and_canonical_path(self):
        self.assertEqual(v2.source_id(BASE),"12345")
        for invalid in (BASE+"?p=2",BASE+"/foo","http://www.v2ex.com/t/12345",
                        "https://v2ex.com/t/12345"):
            with self.assertRaises(ValueError):
                v2.source_id(invalid)

    def test_discover_only_recovery_discussions(self):
        html=('<a href="/t/12345">戒赌经历分享</a>'
              '<a href="/t/12345">戒赌经历分享</a>'
              '<a href="/t/54321">股票分析</a>')
        self.assertEqual(v2.discover("https://www.v2ex.com/tag/%E8%B5%8C%E5%8D%9A",html),
                         {"12345":BASE})
        self.assertEqual(v2.discover("https://www.v2ex.com/tag/%E8%B5%8C%E5%8D%9A",html,{"12345"}),{})

    def test_seed_fallback_keeps_gambling_stories_with_debt_only_titles(self):
        from unittest.mock import patch
        import gambling_collect as collect
        site={"id":"v2ex","listings":["https://www.v2ex.com/tag/%E8%B5%8C%E5%8D%9A"],
              "seed_topics":["https://www.v2ex.com/t/1121755"]}
        # A listing can omit the word 戒赌 even if the actual post recounts
        # gambling recovery. A seed remains just a candidate, not permission.
        with (patch.object(collect,"http",return_value=b"<html></html>"),
              patch.object(collect.time,"sleep",return_value=None)):
            candidates=collect.discover_source(site,{})
            self.assertEqual(candidates,{"1121755":"https://www.v2ex.com/t/1121755"})
            self.assertEqual(collect.discover_source(site,{"1121755":"completed"}),{})

    def test_all_pages_replies_and_supplements(self):
        draft,meta=v2.parse_topic_pages("12345",BASE,page(),
            lambda url:page(int(url.split("=")[-1])))
        self.assertEqual(meta,{"source_total":24,"captured":24,"capped":False,"pages":3})
        self.assertEqual(len(draft["comments"]),24)
        self.assertIn("康复",draft["body"])
        self.assertEqual(draft["source_lang"],"zh")
        self.assertTrue(all("replies" not in c for c in draft["comments"]))

    def test_501_caps_exactly_500(self):
        calls=[]
        def fetch(url):
            idx=int(url.split("=")[-1])
            calls.append(idx)
            return page(idx,pages=51,tail=1)
        draft,meta=v2.parse_topic_pages("12345",BASE,page(pages=51,tail=1),fetch)
        self.assertEqual(meta,{"source_total":501,"captured":500,"capped":True,"pages":50})
        self.assertEqual(len(draft["comments"]),500)
        self.assertNotIn(51,calls)

    def test_missing_middle_page_must_fail_closed(self):
        def fetch(url):
            if url.endswith("p=2"):
                raise ValueError("http_403")
            return page(3)
        with self.assertRaisesRegex(ValueError,"http_403"):
            v2.parse_topic_pages("12345",BASE,page(),fetch)

    def test_reply_missing_or_private_must_fail_closed(self):
        broken=page(pages=1,tail=1).replace(
            "加油，别再赌了 1/0", "欢迎联系 me@example.com")
        with self.assertRaisesRegex(ValueError,"v2ex_private_identifier"):
            v2.parse_topic_pages("12345",BASE,broken,lambda _:None)
        empty=page(pages=1,tail=1).replace(
            "加油，别再赌了 1/0", "")
        with self.assertRaisesRegex(ValueError,"v2ex_empty_text"):
            v2.parse_topic_pages("12345",BASE,empty,lambda _:None)

    def test_page_loss_detected(self):
        with self.assertRaisesRegex(ValueError,"v2ex_reply_body_missing"):
            v2.parse_topic_pages("12345",BASE,page(),
                lambda url:page(int(url.split("=")[-1])).replace('class="reply_content"','class="ignored"') if url.endswith("p=2") else page(3))

if __name__=="__main__":
    unittest.main()
