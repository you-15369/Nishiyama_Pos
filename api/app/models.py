"""ORMモデル（仕様設計書 §4）。"""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

# SQLite では BIGINT の AUTOINCREMENT が効かないため Integer にフォールバック
BigIntPK = BigInteger().with_variant(Integer(), "sqlite")


class Staff(Base):
    __tablename__ = "staff"

    staff_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    login_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)


class Member(Base):
    __tablename__ = "member"

    member_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))
    address: Mapped[str | None] = mapped_column(String(255))
    gender: Mapped[str | None] = mapped_column(String(10))
    age: Mapped[int | None] = mapped_column(Integer)


class TaxRate(Base):
    __tablename__ = "tax_rate"

    tax_rate_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tax_class: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    rate: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)


class Product(Base):
    __tablename__ = "product"
    __table_args__ = (CheckConstraint("unit_price_ex_tax >= 0", name="ck_product_price"),)

    product_code: Mapped[str] = mapped_column(String(13), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    unit_price_ex_tax: Mapped[int] = mapped_column(Integer, nullable=False)
    tax_class: Mapped[str] = mapped_column(String(20), nullable=False)  # standard / reduced


class Promotion(Base):
    __tablename__ = "promotion"

    promotion_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_code: Mapped[str] = mapped_column(ForeignKey("product.product_code"), nullable=False, index=True)
    discount_type: Mapped[str] = mapped_column(String(10), nullable=False)  # rate / amount
    discount_value: Mapped[int] = mapped_column(Integer, nullable=False)  # rate は % の整数、amount は円
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)


class Transaction(Base):
    __tablename__ = "transaction"

    transaction_id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    transacted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    staff_id: Mapped[int] = mapped_column(ForeignKey("staff.staff_id"), nullable=False)
    member_id: Mapped[str | None] = mapped_column(ForeignKey("member.member_id"), nullable=True)
    total_ex_tax: Mapped[int] = mapped_column(Integer, nullable=False)
    total_discount: Mapped[int] = mapped_column(Integer, nullable=False)
    total_in_tax: Mapped[int] = mapped_column(Integer, nullable=False)

    details: Mapped[list["TransactionDetail"]] = relationship(back_populates="transaction")


class TransactionDetail(Base):
    __tablename__ = "transaction_detail"
    __table_args__ = (CheckConstraint("quantity BETWEEN 1 AND 99", name="ck_detail_qty"),)

    detail_id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transaction.transaction_id"), nullable=False, index=True)
    product_code: Mapped[str] = mapped_column(String(13), nullable=False)
    product_name: Mapped[str] = mapped_column(String(128), nullable=False)
    unit_price: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    discount_amount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tax_class: Mapped[str] = mapped_column(String(20), nullable=False)
    applied_rate: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)

    transaction: Mapped[Transaction] = relationship(back_populates="details")
