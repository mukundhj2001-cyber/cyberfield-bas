"""Seed catalog + varied B2B inbox covering the full intent matrix."""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.agent.intents import suggested_action_for
from app.agent.llm import mock_classify_intent
from app.models import Contact, Deal, Email, Product, Task
from app.services.attention import apply_attention, catalog_prices
from app.services.business_relevance import classify_business_relevance

PRODUCTS = [
    {
        "sku": "NW-BRG-6205",
        "name": "Industrial Ball Bearing 6205-2RS",
        "description": "Sealed deep-groove ball bearing, chrome steel, 25×52×15 mm.",
        "unit_price": 18.50,
        "unit": "ea",
        "category": "Bearings",
        "in_stock": 2400,
    },
    {
        "sku": "NW-MTR-3HP",
        "name": "3HP TEFC Induction Motor",
        "description": "230/460V, 1750 RPM, cast iron frame, continuous duty.",
        "unit_price": 685.00,
        "unit": "ea",
        "category": "Motors",
        "in_stock": 48,
    },
    {
        "sku": "NW-PMP-C2",
        "name": "Centrifugal Process Pump C2",
        "description": "Cast stainless wet end, 120 GPM @ 80 ft head.",
        "unit_price": 2140.00,
        "unit": "ea",
        "category": "Pumps",
        "in_stock": 12,
    },
    {
        "sku": "NW-VFD-7",
        "name": "7.5 HP Variable Frequency Drive",
        "description": "IP20 panel mount, Modbus RTU, built-in EMC filter.",
        "unit_price": 920.00,
        "unit": "ea",
        "category": "Drives",
        "in_stock": 35,
    },
    {
        "sku": "NW-SEAL-KIT",
        "name": "Mechanical Seal Rebuild Kit",
        "description": "Compatible with C-series pumps; includes O-rings and faces.",
        "unit_price": 145.00,
        "unit": "kit",
        "category": "Parts",
        "in_stock": 180,
    },
    {
        "sku": "NW-CNV-IDL",
        "name": "Conveyor Idler Roller 4-inch",
        "description": "Greased for life, CEMA C, carbon steel shell.",
        "unit_price": 62.00,
        "unit": "ea",
        "category": "Conveyors",
        "in_stock": 520,
    },
]

_NOW = datetime.now(timezone.utc)

EMAILS = [
    {
        "message_id": "msg-001-quote-bearings",
        "from_address": "procurement@lakeside-mfg.example",
        "from_name": "Priya Nair",
        "subject": "RFQ — 6205 bearings and seal kits for Q4 line maintenance",
        "body": (
            "Hello Northwind team,\n\nWe need a formal quotation for upcoming plant maintenance:\n"
            "- 200 × NW-BRG-6205 Industrial Ball Bearing 6205-2RS\n"
            "- 15 × NW-SEAL-KIT Mechanical Seal Rebuild Kit\n\n"
            "Ship-to: Lakeside Manufacturing, Toledo OH.\n"
            "Preferred delivery within 10 business days. Net-30 terms if possible.\n\n"
            "Regards,\nPriya Nair\nProcurement — Lakeside Manufacturing"
        ),
        "status": "unread",
        "received_at": _NOW - timedelta(hours=5),
    },
    {
        "message_id": "msg-002-quote-motor-vfd",
        "from_address": "ops@summit-packaging.example",
        "from_name": "Marcus Chen",
        "subject": "URGENT — Quote request: 3HP motor + VFD package (needed by Friday)",
        "body": (
            "Hi,\n\nURGENT — production line upgrade. Need quote ASAP.\n"
            "• 4 units of 3HP TEFC Induction Motor (NW-MTR-3HP)\n"
            "• 4 units of 7.5 HP Variable Frequency Drive (NW-VFD-7)\n\n"
            "Deadline Friday EOD. Approx budget $8,000–$10,000.\n"
            "Company: Summit Packaging LLC\n\nThanks,\nMarcus Chen\nOperations Manager"
        ),
        "status": "unread",
        "received_at": _NOW - timedelta(hours=2),
    },
    {
        "message_id": "msg-003-catalog",
        "from_address": "info@harbor-logistics.example",
        "from_name": "Elena Rossi",
        "subject": "Catalog, datasheet, and distributor terms?",
        "body": (
            "Good afternoon,\n\nDo you have a current product catalog, datasheets, and standard "
            "distributor terms? Evaluating suppliers for conveyor idlers and pumps. "
            "Availability confirmation appreciated.\n\nElena Rossi\nHarbor Logistics"
        ),
        "status": "unread",
        "received_at": _NOW - timedelta(days=2),
    },

    {
        "message_id": "msg-006-shipping",
        "from_address": "recv@lakeside-mfg.example",
        "from_name": "Priya Nair",
        "subject": "Where is shipment for PO-3890? Need tracking / ETA",
        "body": (
            "Hi logistics,\n\nCan you share tracking and delivery status for PO-3890?\n"
            "Lead time update appreciated.\n\nPriya Nair"
        ),
        "status": "unread",
        "received_at": _NOW - timedelta(hours=4),
    },
    {
        "message_id": "msg-007-complaint",
        "from_address": "qa@summit-packaging.example",
        "from_name": "Alex Rivera",
        "subject": "Quality complaint — damaged seal kit, need RMA",
        "body": (
            "We received NW-SEAL-KIT that arrived damaged / defective.\n"
            "Unacceptable. Please open an RMA and advise replacement or refund.\n\nAlex Rivera"
        ),
        "status": "unread",
        "received_at": _NOW - timedelta(hours=3),
    },
    {
        "message_id": "msg-008-meeting",
        "from_address": "proc@harbor-logistics.example",
        "from_name": "Elena Rossi",
        "subject": "Demo / discovery call next week?",
        "body": (
            "We would like to schedule a meeting / product demo.\n"
            "Available Tuesday 2pm. Zoom preferred.\n\nElena Rossi"
        ),
        "status": "unread",
        "received_at": _NOW - timedelta(hours=9),
    },
    {
        "message_id": "msg-009-invoice",
        "from_address": "ap@coastal-agg.example",
        "from_name": "Finance Desk",
        "subject": "Remittance advice — INV-2201 paid $3,240 via ACH",
        "body": (
            "Please find remittance for invoice INV-2201.\n"
            "Amount paid: $3,240.00 USD via ACH. PO-4100 referenced.\n\nAP Coastal Aggregates"
        ),
        "status": "unread",
        "received_at": _NOW - timedelta(hours=8),
    },
    {
        "message_id": "msg-010-po",
        "from_address": "buyer@riverbend-plants.example",
        "from_name": "Jordan Blake",
        "subject": "PO-4412 released — please confirm order",
        "body": (
            "Purchase order PO-4412 is released for the pump package ($4,860).\n"
            "Please confirm order acknowledgment.\n\nJordan Blake"
        ),
        "status": "unread",
        "received_at": _NOW - timedelta(hours=7),
    },
    {
        "message_id": "msg-004-newsletter",
        "from_address": "digest@industry-weekly.example",
        "from_name": "Industry Weekly",
        "subject": "This week in industrial supply — newsletter",
        "body": "Your weekly digest. Unsubscribe anytime. No action required.",
        "status": "unread",
        "received_at": _NOW - timedelta(days=1),
    },
    {
        "message_id": "msg-005-reddit-noise",
        "from_address": "noreply@redditmail.com",
        "from_name": "Reddit",
        "subject": "r/manufacturing — weekly roundup",
        "body": "Top posts from Reddit. Unsubscribe · View in browser.",
        "status": "unread",
        "received_at": _NOW - timedelta(hours=6),
    },
]


def _annotate(email: Email) -> None:
    classified = mock_classify_intent(
        {
            "from_address": email.from_address,
            "from_name": email.from_name,
            "subject": email.subject,
            "body": email.body,
        }
    )
    intent = classified.get("intent") or "other_business"
    email.intent = intent
    email.extracted = classified
    email.suggested_action = suggested_action_for(
        intent,
        attention_label=email.attention_label or "Low",
        confidence=float(classified.get("confidence") or 0.7),
    )


def seed_if_empty(db: Session) -> None:
    if db.query(Product).count() == 0:
        for row in PRODUCTS:
            db.add(Product(**row))
        db.flush()

    if db.query(Email).count() == 0:
        catalog = catalog_prices(db)
        for row in EMAILS:
            verdict = classify_business_relevance(
                subject=row["subject"],
                body=row["body"],
                from_address=row["from_address"],
                from_name=row.get("from_name") or "",
            )
            if not verdict.is_business:
                continue
            email = Email(**row)
            email.business_relevant = True
            email.business_meta = verdict.as_meta()
            apply_attention(email, catalog=catalog)
            _annotate(email)
            db.add(email)

    if db.query(Contact).count() == 0 and db.query(Deal).count() == 0:
        pass
    if db.query(Task).count() == 0:
        pass

    db.commit()
