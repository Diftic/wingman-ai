"""
SC_Accountant — Credit Manager

Tracks receivables (someone owes you) and payables (you owe someone)
with payment recording and automatic status transitions.

Author: Mallachi
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from models import Credit
from store import AccountantStore

logger = logging.getLogger(__name__)


class CreditManager:
    """Manages receivables and payables with payment tracking."""

    def __init__(self, store: AccountantStore) -> None:
        """Initialize with shared store.

        Args:
            store: AccountantStore for persistence.
        """
        self._store = store

    # ------------------------------------------------------------------
    # Tool: Create Credit
    # ------------------------------------------------------------------

    def create_credit(
        self,
        credit_type: str,
        counterparty: str,
        amount: float,
        description: str,
        item_type: str = "cash",
        item_name: str = "",
        due_date: str = "",
        notes: str = "",
    ) -> dict:
        """Create a new receivable or payable.

        Args:
            credit_type: "receivable" (they owe you) or "payable" (you owe them).
            counterparty: Player name or organization.
            amount: Amount owed in aUEC.
            description: What the credit is for.
            item_type: Type of item — cash, ship, cargo, or service.
            item_name: Specific item name (optional).
            due_date: When payment is expected (ISO date, optional).
            notes: Additional notes.

        Returns:
            Confirmation dict with credit details.
        """
        if credit_type not in ("receivable", "payable"):
            return {
                "error": f"Invalid credit_type: {credit_type}. Use 'receivable' or 'payable'."
            }

        if amount <= 0:
            return {"error": "Amount must be positive."}

        now = datetime.now(timezone.utc).isoformat()

        credit = Credit(
            id=str(uuid.uuid4()),
            created_at=now,
            credit_type=credit_type,
            status="outstanding",
            counterparty=counterparty,
            original_amount=amount,
            remaining_amount=amount,
            description=description,
            item_type=item_type,
            item_name=item_name,
            due_date=due_date,
            notes=notes,
        )

        self._store.save_credit(credit)

        direction = "owes you" if credit_type == "receivable" else "you owe"
        logger.info(
            "Created %s: %s %s %.0f aUEC — %s",
            credit_type,
            counterparty,
            direction,
            amount,
            description,
        )

        return {
            "status": "created",
            "credit_id": credit.id[:8],
            "credit_type": credit_type,
            "counterparty": counterparty,
            "amount": round(amount, 2),
            "description": description,
        }

    # ------------------------------------------------------------------
    # Tool: Record Payment
    # ------------------------------------------------------------------

    def record_payment(
        self,
        credit_id: str,
        amount: float,
        notes: str = "",
    ) -> dict:
        """Record a payment against a credit.

        Appends the payment, updates remaining balance, and auto-transitions
        status to 'settled' when fully paid or 'partial' when partially paid.

        Args:
            credit_id: Full or partial credit ID.
            amount: Payment amount in aUEC.
            notes: Payment notes.

        Returns:
            Confirmation dict with updated credit details.
        """
        credit = self._find_by_id(credit_id)
        if not credit:
            return {"error": f"Credit not found: {credit_id}"}

        if credit.status in ("settled", "written_off"):
            return {"error": f"Credit is already {credit.status}."}

        if amount <= 0:
            return {"error": "Payment amount must be positive."}

        now = datetime.now(timezone.utc).isoformat()

        # Record the payment
        credit.payments.append(
            {
                "date": now,
                "amount": amount,
                "notes": notes,
            }
        )
        credit.remaining_amount -= amount

        # Auto-transition status
        if credit.remaining_amount <= 0:
            credit.remaining_amount = 0.0
            credit.status = "settled"
        else:
            credit.status = "partial"

        self._store.save_credit(credit)

        total_paid = credit.original_amount - credit.remaining_amount
        logger.info(
            "Payment recorded on %s: %.0f aUEC (%.0f/%.0f paid)",
            credit.id[:8],
            amount,
            total_paid,
            credit.original_amount,
        )

        return {
            "status": credit.status,
            "credit_id": credit.id[:8],
            "counterparty": credit.counterparty,
            "payment_amount": round(amount, 2),
            "total_paid": round(total_paid, 2),
            "remaining": round(credit.remaining_amount, 2),
            "original_amount": round(credit.original_amount, 2),
        }

    # ------------------------------------------------------------------
    # Tool: List Credits
    # ------------------------------------------------------------------

    def list_credits(
        self,
        credit_type: str = "",
        status: str = "",
        counterparty: str = "",
        limit: int = 20,
    ) -> list[dict]:
        """List credits with optional filters.

        Args:
            credit_type: Filter — receivable, payable, or empty for all.
            status: Filter — outstanding, partial, settled, written_off, or empty.
            counterparty: Filter by counterparty name (partial match).
            limit: Maximum results.

        Returns:
            List of credit dicts formatted for tool response.
        """
        query_type = credit_type if credit_type else None
        query_status = status if status else None
        query_cp = counterparty if counterparty else None

        credits = self._store.query_credits(
            credit_type=query_type,
            status=query_status,
            counterparty=query_cp,
            limit=limit,
        )

        return [self._format_credit(c) for c in credits]

    # ------------------------------------------------------------------
    # Tool: Credit Summary
    # ------------------------------------------------------------------

    def get_credit_summary(self) -> dict:
        """Get aggregated summary of all outstanding credits.

        Returns:
            Dict with total_receivable, total_payable, net_position,
            overdue_count, outstanding_count, and top counterparties.
        """
        all_credits = self._store.query_credits(limit=500)

        total_receivable = 0.0
        total_payable = 0.0
        overdue_count = 0
        outstanding_count = 0
        now = datetime.now(timezone.utc).isoformat()

        # Track counterparty balances
        cp_receivable: dict[str, float] = {}
        cp_payable: dict[str, float] = {}

        for credit in all_credits:
            if credit.status in ("settled", "written_off"):
                continue

            outstanding_count += 1

            if credit.credit_type == "receivable":
                total_receivable += credit.remaining_amount
                cp_receivable[credit.counterparty] = (
                    cp_receivable.get(credit.counterparty, 0.0)
                    + credit.remaining_amount
                )
            else:
                total_payable += credit.remaining_amount
                cp_payable[credit.counterparty] = (
                    cp_payable.get(credit.counterparty, 0.0) + credit.remaining_amount
                )

            # Check overdue
            if credit.due_date and credit.due_date < now:
                overdue_count += 1

        # Top debtors (owe you most)
        top_debtors = sorted(cp_receivable.items(), key=lambda x: x[1], reverse=True)[
            :5
        ]

        # Top creditors (you owe most)
        top_creditors = sorted(cp_payable.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "total_receivable": round(total_receivable, 2),
            "total_payable": round(total_payable, 2),
            "net_position": round(total_receivable - total_payable, 2),
            "outstanding_count": outstanding_count,
            "overdue_count": overdue_count,
            "top_debtors": [
                {"counterparty": name, "amount": round(amt, 2)}
                for name, amt in top_debtors
            ],
            "top_creditors": [
                {"counterparty": name, "amount": round(amt, 2)}
                for name, amt in top_creditors
            ],
        }

    # ------------------------------------------------------------------
    # Tool: Write Off Credit
    # ------------------------------------------------------------------

    def write_off_credit(self, credit_id: str, reason: str = "") -> dict:
        """Write off a credit as uncollectable.

        Args:
            credit_id: Full or partial credit ID.
            reason: Why the credit is being written off.

        Returns:
            Confirmation dict.
        """
        credit = self._find_by_id(credit_id)
        if not credit:
            return {"error": f"Credit not found: {credit_id}"}

        if credit.status in ("settled", "written_off"):
            return {"error": f"Credit is already {credit.status}."}

        credit.status = "written_off"
        if reason:
            credit.notes = (credit.notes + f" Written off: {reason}").strip()

        self._store.save_credit(credit)

        logger.info(
            "Written off credit %s: %.0f aUEC from %s",
            credit.id[:8],
            credit.remaining_amount,
            credit.counterparty,
        )

        return {
            "status": "written_off",
            "credit_id": credit.id[:8],
            "counterparty": credit.counterparty,
            "amount_written_off": round(credit.remaining_amount, 2),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_by_id(self, credit_id: str) -> Credit | None:
        """Find a credit by full or partial ID."""
        credit = self._store.get_credit(credit_id)
        if credit:
            return credit

        for credit in self._store.query_credits(limit=500):
            if credit.id.startswith(credit_id):
                return credit

        return None

    def _format_credit(self, credit: Credit) -> dict:
        """Format a credit for tool response."""
        total_paid = credit.original_amount - credit.remaining_amount

        result = {
            "id": credit.id[:8],
            "credit_type": credit.credit_type,
            "status": credit.status,
            "counterparty": credit.counterparty,
            "original_amount": round(credit.original_amount, 2),
            "remaining": round(credit.remaining_amount, 2),
            "total_paid": round(total_paid, 2),
            "description": credit.description,
            "created_at": credit.created_at,
        }

        if credit.item_type != "cash":
            result["item_type"] = credit.item_type
        if credit.item_name:
            result["item_name"] = credit.item_name
        if credit.due_date:
            result["due_date"] = credit.due_date
        if credit.payments:
            result["payment_count"] = len(credit.payments)
        if credit.notes:
            result["notes"] = credit.notes

        return result
