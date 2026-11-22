import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from gambling_psychforums import LISTING, discover, parse_topic_pages


TOPIC_URL = "https://www.psychforums.com/my-gambling-recovery/topic123.html"
PAGE_TWO = TOPIC_URL.removesuffix(".html") + "/page2.html"


def topic_page(url, first_id, count, page_number, next_url=""):
    posts = "".join(
        f'<div class="post" id="p{post_id}"><div class="postbody"><div>'
        f'<div class="content">My gambling recovery entry {post_id}</div>'
        f'</div></div></div>'
        for post_id in range(first_id, first_id + count)
    )
    next_link = f'<a rel="next" href="{next_url}">Next</a>' if next_url else ""
    return (
        f'<link rel="canonical" href="{url}"><span class="crumb" data-forum-id="204"></span>'
        f'<h1 class="topic-title">My gambling recovery</h1>'
        f'<div class="action-bar"><div class="pagination">13 posts'
        f'<ul><li class="active">{page_number}</li></ul>{next_link}</div></div>{posts}'
    )


class PsychForumsTests(unittest.TestCase):
    def test_discovery_uses_native_id_and_skips_completed_topics(self):
        listing = (
            '<ul class="topiclist topics"><li><dl>'
            '<dt><a class="topictitle" href="/my-gambling-recovery/topic123.html">My recovery</a></dt>'
            '<dd class="posts">12 Replies</dd></dl></li></ul>'
        )
        self.assertEqual(discover(LISTING, listing), {"123": TOPIC_URL})
        self.assertEqual(discover(LISTING, listing, {"123"}), {})

    def test_reads_complete_pagination_and_keeps_chronological_replies(self):
        pages = {PAGE_TWO: topic_page(PAGE_TWO, 11, 3, 2)}
        draft, metadata = parse_topic_pages(
            "123", TOPIC_URL, topic_page(TOPIC_URL, 1, 10, 1, PAGE_TWO), pages.__getitem__
        )
        self.assertEqual(metadata, {"pages": 2, "source_total": 12, "captured": 12, "capped": False})
        self.assertEqual(draft["body"], "My gambling recovery entry 1")
        self.assertEqual(
            [reply["body"] for reply in draft["comments"]],
            [f"My gambling recovery entry {post_id}" for post_id in range(2, 14)],
        )

    def test_rejects_incomplete_page_and_repeated_post_id(self):
        first = topic_page(TOPIC_URL, 1, 10, 1, PAGE_TWO)
        for count, identifier, reason in [
            (2, 11, "psychforums_page_incomplete"),
            (3, 10, "psychforums_post_id_unverified"),
        ]:
            with self.subTest(reason=reason), self.assertRaisesRegex(ValueError, reason):
                parse_topic_pages(
                    "123", TOPIC_URL, first, lambda url: topic_page(url, identifier, count, 2)
                )
