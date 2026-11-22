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
        with self.assertRaisesRegex(ValueError, "not_topic_url"):
            source_id(self.site, "https://community.gamcare.org.uk/forum/new-members-intros-forum/paged/2/")

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
                       {"id": "comment-" + str(i), "body": x["body"], "source_lang": "en", "parent_comment_id": None}
                       for i, x in enumerate(reversed(draft["comments"]))
                   ], "next": None}
        with patch.object(collect, "api", return_value=details):
            self.assertTrue(collect.readback("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", draft, 2))


    def test_atomic_claim_complete_with_mock_preview_and_readback(self):
        lease = "a" * 64
        calls = []
        def fake_api(path, body=None):
            calls.append((path, body))
            if path.endswith("/claim"):
                return {"results": [{"result": "granted", "lease_token": lease}]}
            if path.endswith("/complete"):
                self.assertEqual(body["source_id"], "trying-to-stop")
                self.assertEqual(body["lease_token"], lease)
                self.assertEqual(len(body["topic"]["comments"]), 2)
                return {"status": "completed", "topic_id":
                        "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                        "imported": {"topics": 1, "comments": 2}}
            raise AssertionError("unexpected API path " + path)
        with patch.object(collect, "api", side_effect=fake_api), \
                patch.object(collect, "http", return_value=fixture().encode()), \
                patch.object(collect, "readback", return_value=True) as verify:
            self.assertEqual(collect.collect_one(
                self.site, {}, "trying-to-stop", self.url, None), (1, 2, 0))
            verify.assert_called_once()
        self.assertEqual([p for p, _ in calls], [
            "/api/collect/claim", "/api/collect/complete"])

    def test_unverified_parsing_releases_claim_without_writing(self):
        calls = []
        def fake_api(path, body=None):
            calls.append(path)
            if path.endswith("/claim"):
                return {"results": [{"result": "granted",
                                     "lease_token": "b" * 64}]}
            if path.endswith("/release"):
                return {"status": "released"}
            raise AssertionError("unexpected API path: " + path)
        with patch.object(collect, "api", side_effect=fake_api), \
                patch.object(collect, "http", return_value=b"<html>incomplete</html>"):
            with self.assertRaisesRegex(ValueError, "title_missing"):
                collect.collect_one(self.site, {}, "trying-to-stop", self.url, None)
        self.assertEqual(calls, ["/api/collect/claim", "/api/collect/release"])


    def test_readback_fetches_all_comment_pages(self):
        draft = {"title": "Gambling recovery update",
                 "body": "I am trying to quit online gambling.",
                 "source_lang": "en",
                 "comments": [{"body": "Response " + str(i), "source_lang": "en"}
                              for i in range(21)]}
        saved = {k: draft[k] for k in ("title", "body", "source_lang")}
        rows = [{"id": "cid-" + str(i), "body": "Response " + str(i),
                 "source_lang": "en", "parent_comment_id": None}
                for i in range(21)]
        pages = iter([
            {"topic": saved, "comments": rows[:20], "next": 200},
            {"topic": saved, "comments": rows[20:], "next": None},
        ])
        with patch.object(collect, "api", side_effect=lambda *_: next(pages)) as mock:
            self.assertTrue(collect.readback(
                "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", draft, 21))
            self.assertEqual(mock.call_count, 2)
            self.assertTrue(mock.call_args_list[1].args[0].endswith("?before=200"))


    def test_readback_allows_server_detected_language_not_import_hint(self):
        draft = {"title": "Online gambling recovery", "body": "I am starting to quit",
                 "source_lang": "en", "comments": [
                     {"body": "Wish you well", "source_lang": "en"},
                     {"body": "Keep going", "source_lang": "en"}]}
        result = {"topic": {"title": draft["title"], "body": draft["body"],
                            "source_lang": "und"},
                  "comments": [
                      {"id": "c1", "body": "Wish you well", "source_lang": "und",
                       "parent_comment_id": None},
                      {"id": "c2", "body": "Keep going", "source_lang": "en",
                       "parent_comment_id": None}],
                  "next": None}
        with patch.object(collect, "api", return_value=result):
            self.assertTrue(collect.readback(
                "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", draft, 2))

    def test_incomplete_source_raises_rejected_candidate_and_releases(self):
        calls = []
        def fake_api(path, body=None):
            calls.append(path)
            if path.endswith("/claim"):
                return {"results": [{"result": "granted",
                                     "lease_token": "x" * 64}]}
            if path.endswith("/release"):
                return {"status": "released"}
            raise AssertionError("unexpected API path " + path)
        with patch.object(collect, "api", side_effect=fake_api), \
                patch.object(collect, "http", return_value=b"<html></html>"):
            with self.assertRaises(collect.RejectedCandidate):
                collect.collect_one(self.site, {}, "trying-to-stop", self.url, None)
        self.assertEqual(calls, ["/api/collect/claim", "/api/collect/release"])


    def test_audit_completed_uses_exact_published_full_body_readback(self):
        topic = parse_topic(self.site, "trying-to-stop", self.url, fixture())
        topic_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        feed = {"topics": [{"id": topic_id, "title": topic["title"]}], "next": None}
        detail = {"topic": {"title": topic["title"], "body": topic["body"],
                            "source_lang": "en"},
                  "comments": [
                      {"id": "a", "body": topic["comments"][0]["body"],
                       "source_lang": "en", "parent_comment_id": None},
                      {"id": "b", "body": topic["comments"][1]["body"],
                       "source_lang": "und", "parent_comment_id": None}],
                  "next": None}
        def mock_api(url):
            if url.startswith("/api/topics?"):
                return feed
            if url == "/api/topics/" + topic_id:
                return detail
            raise AssertionError(url)
        with patch.object(collect, "api", side_effect=mock_api):
            self.assertEqual(collect.lookup_published_topic_id(topic), topic_id)
            collect.audit_completed(self.site, "trying-to-stop", self.url, topic, 2)

    def test_audit_missing_source_cannot_claim_as_verified(self):
        topic = parse_topic(self.site, "trying-to-stop", self.url, fixture())
        with patch.object(collect, "api", return_value={"topics": [], "next": None}):
            with self.assertRaisesRegex(ValueError, "completed_topic_not_visible"):
                collect.audit_completed(self.site, "trying-to-stop", self.url, topic, 2)


if __name__ == "__main__":
    unittest.main()
