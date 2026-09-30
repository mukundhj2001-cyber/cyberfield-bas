from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Email(Base):
    __tablename__ = "emails"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    from_address: Mapped[str] = mapped_column(String(255))
    from_name: Mapped[str] = mapped_column(String(255), default="")
    to_address: Mapped[str] = mapped_column(String(255), default="quotes@northwind-industrial.example")
    subject: Mapped[str] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status: Mapped[str] = mapped_column(String(32), default="unread")  # unread|processing|quoted|ignored
    intent: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    extracted: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    approvals: Mapped[list["Approval"]] = relationship(back_populates="email")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    unit_price: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(32), default="ea")
    category: Mapped[str] = mapped_column(String(64), default="General")
    in_stock: Mapped[int] = mapped_column(Integer, default=100)


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    company: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    deals: Mapped[list["Deal"]] = relationship(back_populates="contact")


class Deal(Base):
    __tablename__ = "deals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    contact_id: Mapped[Optional[int]] = mapped_column(ForeignKey("contacts.id"), nullable=True)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    stage: Mapped[str] = mapped_column(String(64), default="qualified")  # qualified|quote_sent|won|lost
    source: Mapped[str] = mapped_column(String(64), default="email")
    quote_ref: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    contact: Mapped[Optional[Contact]] = relationship(back_populates="deals")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default="open")  # open|in_progress|done
    assignee: Mapped[str] = mapped_column(String(128), default="Sales Ops")
    priority: Mapped[str] = mapped_column(String(32), default="medium")
    related_deal_id: Mapped[Optional[int]] = mapped_column(ForeignKey("deals.id"), nullable=True)
    related_email_id: Mapped[Optional[int]] = mapped_column(ForeignKey("emails.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email_id: Mapped[int] = mapped_column(ForeignKey("emails.id"))
    workflow: Mapped[str] = mapped_column(String(64), default="quote_from_email")
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending|approved|rejected
    quote_draft: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    email_draft: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    agent_trace: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    review_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    email: Mapped[Email] = relationship(back_populates="approvals")


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(64))  # email_sent|crm_update|task_created|workflow
    message: Mapped[str] = mapped_column(Text)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
