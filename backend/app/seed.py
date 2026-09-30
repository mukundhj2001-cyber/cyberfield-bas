"""Seed sample inbox, pricing catalog, empty CRM, and starter tasks."""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import Contact, Deal, Email, Product, Task
from app.services.attention import apply_attention, catalog_prices


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

# Varied ages + content so attention ranking demos clearly.
_NOW = datetime.now(timezone.utc)

EMAILS = [
    {
        "message_id": "msg-001-quote-bearings",
        "from_address": "procurement@lakeside-mfg.example",
        "from_name": "Priya Nair",
        "subject": "RFQ — 6205 bearings and seal kits for Q4 line maintenance",
        "body": (
            "Hello Northwind team,\n\n"
            "We need a formal quotation for upcoming plant maintenance:\n"
            "- 200 × NW-BRG-6205 Industrial Ball Bearing 6205-2RS\n"
            "- 15 × NW-SEAL-KIT Mechanical Seal Rebuild Kit\n\n"
            "Ship-to: Lakeside Manufacturing, Toledo OH.\n"
            "Preferred delivery within 10 business days. Net-30 terms if possible.\n\n"
            "Please reply with unit pricing, lead time, and total.\n\n"
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
            "Hi,\n\n"
            "URGENT — production line upgrade. Need quote ASAP.\n"
            "• 4 units of 3HP TEFC Induction Motor (NW-MTR-3HP)\n"
            "• 4 units of 7.5 HP Variable Frequency Drive (NW-VFD-7)\n\n"
            "Deadline Friday EOD. Approx budget $8,000–$10,000.\n"
            "Company: Summit Packaging LLC\n"
            "Contact phone: +1-419-555-0142\n\n"
            "Thanks,\nMarcus Chen\nOperations Manager"
        ),
        "status": "unread",
        "received_at": _NOW - timedelta(hours=2),
    },
    {
        "message_id": "msg-003-general",
        "from_address": "info@harbor-logistics.example",
        "from_name": "Elena Rossi",
        "subject": "Catalog and distributor terms?",
        "body": (
            "Good afternoon,\n\n"
            "Do you have a current product catalog and standard distributor terms?\n"
            "We are evaluating suppliers for conveyor idlers and pumps.\n\n"
            "Elena Rossi\nHarbor Logistics"
        ),
        "status": "unread",
        "received_at": _NOW - timedelta(days=2),
    },
    {
        "message_id": "msg-004-newsletter",
        "from_address": "digest@industry-weekly.example",
        "from_name": "Industry Weekly",
        "subject": "This week in industrial supply — newsletter",
        "body": (
            "Your weekly digest of bearings, motors, and plant news.\n"
            "Unsubscribe anytime. No action required."
        ),
        "status": "unread",
        "received_at": _NOW - timedelta(days=1),
    },
]


def seed_if_empty(db: Session) -> None:
    if db.query(Product).count() == 0:
        for row in PRODUCTS:
            db.add(Product(**row))
        db.flush()

    if db.query(Email).count() == 0:
        catalog = catalog_prices(db)
        for row in EMAILS:
            email = Email(**row)
            apply_attention(email, catalog=catalog)
            db.add(email)

    # CRM starts empty of deals; leave contacts empty too so quote approval creates them.
    if db.query(Contact).count() == 0 and db.query(Deal).count() == 0:
        pass  # intentionally empty — demo creates CRM on approve

    if db.query(Task).count() == 0:
        pass

    db.commit()
