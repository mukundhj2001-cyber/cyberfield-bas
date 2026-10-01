"""Unit + smoke samples for business inbox filter.

Run: cd backend && python -m unittest tests.test_business_relevance -v
"""

from __future__ import annotations

import unittest

from app.services.business_relevance import classify_business_relevance
from app.services.gmail import GMAIL_LIST_QUERY, MOCK_GMAIL_POOL


# Must stay in inbox (RFQ / PO / complaint / ops)
KEEPERS: list[dict[str, str]] = [
    {
        "subject": "URGENT RFQ — Centrifugal Process Pump C2 × 2 — ASAP",
        "body": "Please quote ASAP: 2 × Centrifugal Process Pump C2 (NW-PMP-C2).",
        "from_address": "buyer@riverbend-plants.example",
        "from_name": "Jordan Blake",
    },
    {
        "subject": "PO-4412 released — please confirm order",
        "body": "Purchase order PO-4412 is released for the pump package ($4,860).",
        "from_address": "buyer@riverbend-plants.example",
        "from_name": "Jordan Blake",
    },
    {
        "subject": "Quality complaint — damaged seal kit, need RMA",
        "body": "Defective NW-SEAL-KIT arrived damaged. Please open an RMA.",
        "from_address": "qa@summit-packaging.example",
        "from_name": "Alex Rivera",
    },
    {
        "subject": "Where is shipment for PO-3890? Need tracking / ETA",
        "body": "Share tracking and delivery status for PO-3890. Lead time update.",
        "from_address": "recv@lakeside-mfg.example",
        "from_name": "Priya Nair",
    },
    {
        "subject": "Remittance advice — INV-2201 paid $3,240 via ACH",
        "body": "Remittance for invoice INV-2201. Amount paid via ACH. PO-4100.",
        "from_address": "ap@coastal-agg.example",
        "from_name": "Finance Desk",
    },
]

# Must be filtered (noise that previously slipped into Inbox)
NOISE: list[dict[str, str]] = [
    {
        "subject": "r/industrialengineering — top posts this week",
        "body": "Your Reddit digest. Unsubscribe anytime. No action required.",
        "from_address": "noreply@redditmail.com",
        "from_name": "Reddit",
    },
    {
        "subject": "You have 12 new notifications — weekly roundup",
        "body": "Sponsored marketing tips. Unsubscribe · Manage preferences.",
        "from_address": "messages-noreply@linkedin.com",
        "from_name": "LinkedIn",
    },
    {
        "subject": "Stories for you from Medium",
        "body": "Read this article. Top stories trending now. View in browser. Unsubscribe.",
        "from_address": "noreply@medium.com",
        "from_name": "Medium",
    },
    {
        "subject": "Your Substack digest: 5 new posts",
        "body": "Weekly newsletter digest from writers you follow. Manage preferences.",
        "from_address": "noreply@substack.com",
        "from_name": "Substack",
    },
    {
        "subject": "[GitHub] You have new notifications",
        "body": "github notifications for your repositories. Pushed to main.",
        "from_address": "notifications@github.com",
        "from_name": "GitHub",
    },
    {
        "subject": "This week in industrial supply — newsletter",
        "body": "Your daily digest / morning brief. Unsubscribe anytime.",
        "from_address": "digest@industry-weekly.example",
        "from_name": "Industry Weekly",
    },
    {
        "subject": "Flash sale — 40% off ends tonight",
        "body": "Limited-time offer. Shop now. Coupon inside. Unsubscribe.",
        "from_address": "promo@retail.example",
        "from_name": "Retail Promo",
    },
    {
        "subject": "Hope you are doing well",
        "body": "Just checking in, no agenda.",
        "from_address": "friend@gmail.com",
        "from_name": "Sam",
    },
]


class BusinessRelevanceTests(unittest.TestCase):
    def test_keepers_pass(self) -> None:
        for row in KEEPERS:
            with self.subTest(subject=row["subject"]):
                verdict = classify_business_relevance(**row)
                self.assertTrue(
                    verdict.is_business,
                    f"expected business: {row['subject']} reasons={verdict.reasons} score={verdict.score}",
                )

    def test_noise_filtered(self) -> None:
        for row in NOISE:
            with self.subTest(subject=row["subject"]):
                verdict = classify_business_relevance(**row)
                self.assertFalse(
                    verdict.is_business,
                    f"noise leaked: {row['subject']} reasons={verdict.reasons} score={verdict.score}",
                )

    def test_github_with_po_kept(self) -> None:
        verdict = classify_business_relevance(
            subject="PO-991 attached",
            body="Purchase order PO-991 and invoice for NW-PMP-C2. Please confirm.",
            from_address="notifications@github.com",
            from_name="GitHub",
        )
        self.assertTrue(verdict.is_business, verdict.reasons)

    def test_mock_pool_expect_filtered(self) -> None:
        for row in MOCK_GMAIL_POOL:
            if not row.get("expect_filtered"):
                continue
            with self.subTest(message_id=row["message_id"]):
                verdict = classify_business_relevance(
                    subject=row["subject"],
                    body=row["body"],
                    from_address=row["from_address"],
                    from_name=row.get("from_name") or "",
                )
                self.assertFalse(
                    verdict.is_business,
                    f"mock noise not filtered: {row['message_id']} {verdict.reasons}",
                )

    def test_mock_pool_business_seeds_kept(self) -> None:
        for row in MOCK_GMAIL_POOL:
            if row.get("expect_filtered"):
                continue
            with self.subTest(message_id=row["message_id"]):
                verdict = classify_business_relevance(
                    subject=row["subject"],
                    body=row["body"],
                    from_address=row["from_address"],
                    from_name=row.get("from_name") or "",
                )
                self.assertTrue(
                    verdict.is_business,
                    f"business seed dropped: {row['message_id']} {verdict.reasons} score={verdict.score}",
                )

    def test_oauth_list_query_excludes_promotions_social(self) -> None:
        q = GMAIL_LIST_QUERY.lower()
        self.assertIn("in:inbox", q)
        self.assertIn("-category:promotions", q)
        self.assertIn("-category:social", q)
        self.assertIn("-from:redditmail.com", q)
        self.assertIn("-from:substack.com", q)
        self.assertIn("-from:notifications.github.com", q)


if __name__ == "__main__":
    unittest.main()
