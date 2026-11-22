"""Offline parser/coordinator contract tests; no external websites or D1 writes."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import gambling_collect as collect
from gambling_forums import discover, parse_topic, source_id


def fixture():
    return """<!doctype html><html><head>
    <link rel="canonical" href="https://community.gamcare.org.uk/forum/recovery-diaries/trying-to-stop/">
    </head><body>
    <h1>Trying to stop gambling</h1><div class="wpf-topic-stat">3 Posts</div>
    <article class="wpforo-post" id="wpf-post-101"><div class="wpforo-post-content">
    <p>I lost money gambling, need help quitting.</p></div></article>
    <article class="wpforo-post" id="wpf-post-102"><div class="wpforo-post-content">
    <p>I hope you find support.</p></div></article>
    <article class="wpforo-post" id="wpf-post-103"><div class="wpforo-post-content">
    <p>Consider speaking to a counsellor.</p></div></article>
    </body></html>"""


class ParserTests(unittest.TestCase):
    def setUp(self):
        self.site = "gamcare"
        self.url = "https://community.gamcare.org.uk/forum/recovery-diaries/trying-to-stop/"

    def test_stable_original_slug(self):
        self.assertEqual(source_id(self.site, self.url), "trying-to-stop")
        with self.assertRaises(ValueError):
            source_id(self.site, "https://evil.example/forum/recovery-diaries/trying-to-stop/")
        with self.assertRaises(ValueError):
            source_id(self.site, self.url + "?page=2")

    def test_realistic_discovery_filters_duplicates(self):
        page = ('<a class="wpforo-topic-title" href="#">not selected</a>'
                '<div class="wpforo-topic-title"><a href="/forum/recovery-diaries/trying-to-stop/">'
                'Trying to stop</a></div>'
                '<div class="wpforo-topic-title"><a href="/forum/recovery-diaries/trying-to-stop/">'
                'Duplicated</a></div>')
        self.assertEqual(discover(self.site,
                         "https://community.gamcare.org.uk/forum/recovery-diaries/",
                         page), {"trying-to-stop": self.url})
        self.assertFalse(discover(self.site,
                         "https://community.gamcare.org.uk/forum/recovery-diaries/",
                         page, excluded={"trying-to-stop"}))

    def test_topic_text_replies_and_count(self):
        data = parse_topic(self.site, "trying-to-stop", self.url, fixture())
        self.assertEqual(data["source_lang"], "en")
        self.assertEqual(len(data["comments"]), 2)
        self.assertEqual(collect.validate(data), 2)
        self.assertNotIn("replies", data["comments"][1])

    def test_no_truncating_missing_replies(self):
        with self.assertRaisesRegex(ValueError, "public_reply_count_mismatch"):
            parse_topic(self.site, "trying-to-stop", self.url,
                        fixture().replace("3 Posts", "4 Posts"))

    def test_no_invented_parent_relationship(self):
        self.assertEqual(len(parse_topic(self.site, "trying-to-stop", self.url,
                    fixture().replace("I hope", "@first_user I hope"))["comments"]), 2)

    def test_no_unparsed_pagination(self):
        page = fixture().replace("</body>", '<a class="next page-numbers" href="x">Next</a></body>')
        with self.assertRaisesRegex(ValueError, "multipage_thread"):
            parse_topic(self.site, "trying-to-stop", self.url, page)

    def test_reject_private_identifiers(self):
        page = fixture().replace("I hope you find support.", "My email is test@example.com")
        with self.assertRaisesRegex(ValueError, "personal_identifier"):
            parse_topic(self.site, "trying-to-stop", self.url, page)

    def test_permission_gate_is_explicit(self):
        source = {"approved": True, "parser_verified": True, "reuse_allowed": True}
        self.assertFalse(collect.available(source))
        source["permission_evidence"] = "signed-agreement-123"
        self.assertTrue(collect.available(source))
        source["approved"] = False
        self.assertFalse(collect.available(source))

    def test_exclusions_page_all(self):
        replies = iter([
            {"site": "gamcare", "items": [{"source_id": "a", "status": "completed"}], "next_cursor": "a"},
            {"site": "gamcare", "items": [{"source_id": "b", "status": "claimed"}], "next_cursor": None},
        ])
        with patch.object(collect, "api", side_effect=lambda *args: next(replies)) as mock:
            self.assertEqual(collect.excluded_ids("gamcare"), {"a": "completed", "b": "claimed"})
            self.assertEqual(mock.call_count, 2)

    def test_readback_verifies_flat_replies_without_order_assumption(self):
        draft = parse_topic(self.site, "trying-to-stop", self.url, fixture())
        details = {"topic": {"title": draft["title"], "body": draft["body"], "source_lang": "en"},
                   "comments": [
                       {"body": x["body"], "source_lang": "en", "parent_comment_id": None}
                       for x in reversed(draft["comments"])
                   ], "next": None}
        with patch.object(collect, "api", return_value=details):
            self.assertTrue(collect.readback("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", draft, 2))


if __name__ == "__main__":
    unittest.main()
