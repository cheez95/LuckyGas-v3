"""
Invoice sequence model for Taiwan e-invoice number management
"""

from sqlalchemy import (Boolean, CheckConstraint, Column, DateTime, Index,
                        Integer, String)
from sqlalchemy.sql import func

from app.core.database import Base


class InvoiceSequence(Base):
    """
    Manages invoice number sequences for Taiwan e-invoice system.

    Taiwan e-invoices require sequential numbering within allocated ranges.
    Government allocates ranges of numbers with specific prefixes for each period.
    """

    __tablename__ = "invoice_sequences"

    id = Column(Integer, primary_key=True, index=True)

    # Period and prefix
    year_month = Column(
        String(6), nullable=False, comment="YYYYMM format (e.g., 202501)"
    )
    prefix = Column(String(2), nullable=False, comment="Invoice prefix (e.g., AA, AB)")

    # Allocated range
    range_start = Column(
        Integer, nullable=False, comment="Starting number of allocated range"
    )
    range_end = Column(
        Integer, nullable=False, comment="Ending number of allocated range"
    )

    # Current sequence
    current_number = Column(
        Integer, nullable=False, comment="Current sequential number"
    )

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Notes
    notes = Column(String(500))

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Constraints
    __table_args__ = (
        # Ensure unique year_month + prefix combination
        Index("idx_invoice_sequence_unique", "year_month", "prefix", unique=True),
        # Index for finding active sequences
        Index("idx_invoice_sequence_active", "is_active", "year_month"),
        # Ensure current_number is within allocated range
        CheckConstraint(
            "current_number >= range_start AND current_number <= range_end",
            name="check_current_number_in_range",
        ),
        # Ensure range is valid
        CheckConstraint("range_end > range_start", name="check_valid_range"),
    )

    def __repr__(self):
        return f"<InvoiceSequence {self.year_month}-{self.prefix}: {self.current_number}/{self.range_end}>"

    @property
    def available_count(self) -> int:
        """Get count of available invoice numbers"""
        return self.range_end - self.current_number + 1

    @property
    def usage_percentage(self) -> float:
        """Get percentage of range used"""
        total = self.range_end - self.range_start + 1
        used = self.current_number - self.range_start
        return (used / total) * 100 if total > 0 else 0

    def get_next_number(self) -> str:
        """
        Get the next invoice number in format: PREFIX + 8-digit number

        Returns:
            str: Next invoice number (e.g., "AA10000001")

        Raises:
            ValueError: If no more numbers available in range
        """
        if self.current_number > self.range_end:
            raise ValueError(
                f"No more invoice numbers available for {self.year_month}-{self.prefix}. "
                f"Range exhausted at {self.range_end}"
            )

        # Format as 8-digit number with prefix
        return f"{self.prefix}{str(self.current_number).zfill(8)}"
