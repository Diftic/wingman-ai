"""
SC_Accountant — Production Manager (Stub)

Tracks production runs where input materials are converted into
output products. Records input costs and output value for margin
analysis. Stub implementation for future expansion.

Author: Mallachi
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from models import ProductionRun
from store import AccountantStore

logger = logging.getLogger(__name__)


class ProductionManager:
    """Tracks production runs converting inputs to outputs.

    Stub implementation — will be expanded as production
    gameplay features mature in Star Citizen.
    """

    def __init__(self, store: AccountantStore) -> None:
        """Initialize with shared store.

        Args:
            store: AccountantStore for persistence.
        """
        self._store = store

    # ------------------------------------------------------------------
    # Tool: Log Production
    # ------------------------------------------------------------------

    def log_production(
        self,
        output_name: str,
        output_quantity: float,
        output_value: float = 0.0,
        inputs: str = "",
        location: str = "",
        status: str = "completed",
        notes: str = "",
    ) -> dict:
        """Log a production run.

        Args:
            output_name: Name of the produced item/commodity.
            output_quantity: Amount produced.
            output_value: Estimated value of the output in aUEC.
            inputs: Comma-separated inputs as "name:qty:cost" entries.
                Example: "iron:10:500,carbon:5:200"
            location: Where production happened.
            status: in_progress, completed, or cancelled.
            notes: Additional notes.

        Returns:
            Confirmation dict with production run details.
        """
        if status not in ("in_progress", "completed", "cancelled"):
            return {
                "error": f"Invalid status: {status}. "
                "Use 'in_progress', 'completed', or 'cancelled'."
            }

        now = datetime.now(timezone.utc).isoformat()

        # Parse inputs string into structured data
        parsed_inputs: list[dict] = []
        total_input_cost = 0.0

        if inputs:
            for entry in inputs.split(","):
                entry = entry.strip()
                if not entry:
                    continue
                parts = entry.split(":")
                if len(parts) >= 2:
                    name = parts[0].strip()
                    try:
                        qty = float(parts[1].strip())
                    except ValueError:
                        qty = 0.0
                    cost = 0.0
                    if len(parts) >= 3:
                        try:
                            cost = float(parts[2].strip())
                        except ValueError:
                            cost = 0.0
                    parsed_inputs.append(
                        {
                            "item_name": name,
                            "quantity": qty,
                            "cost": cost,
                        }
                    )
                    total_input_cost += cost

        run = ProductionRun(
            id=str(uuid.uuid4()),
            started_at=now,
            status=status,
            inputs=parsed_inputs,
            output_name=output_name,
            output_quantity=output_quantity,
            output_value=output_value,
            location=location,
            completed_at=now if status == "completed" else None,
            notes=notes,
        )

        self._store.save_production_run(run)

        value_added = output_value - total_input_cost
        logger.info(
            "Logged production %s: %s (value added: %.0f aUEC)",
            run.id[:8],
            output_name,
            value_added,
        )

        return {
            "status": "logged",
            "run_id": run.id[:8],
            "output_name": output_name,
            "output_quantity": output_quantity,
            "output_value": round(output_value, 2),
            "input_count": len(parsed_inputs),
            "total_input_cost": round(total_input_cost, 2),
            "value_added": round(value_added, 2),
        }

    # ------------------------------------------------------------------
    # Tool: Production Summary
    # ------------------------------------------------------------------

    def get_production_summary(self) -> dict:
        """Get aggregated production statistics.

        Returns:
            Dict with total_runs, total_input_cost, total_output_value,
            total_value_added, and by_output breakdown.
        """
        runs = self._store.query_production_runs(status="completed", limit=500)

        total_input_cost = 0.0
        total_output_value = 0.0

        # Aggregate by output
        by_output: dict[str, dict] = {}

        for run in runs:
            run_input_cost = sum(i.get("cost", 0) for i in run.inputs)
            total_input_cost += run_input_cost
            total_output_value += run.output_value

            name = run.output_name
            if name not in by_output:
                by_output[name] = {
                    "count": 0,
                    "total_quantity": 0.0,
                    "input_cost": 0.0,
                    "output_value": 0.0,
                }
            entry = by_output[name]
            entry["count"] += 1
            entry["total_quantity"] += run.output_quantity
            entry["input_cost"] += run_input_cost
            entry["output_value"] += run.output_value

        total_value_added = total_output_value - total_input_cost

        # Sort by value added descending
        outputs = []
        for name, data in sorted(
            by_output.items(),
            key=lambda x: x[1]["output_value"] - x[1]["input_cost"],
            reverse=True,
        ):
            value_added = data["output_value"] - data["input_cost"]
            outputs.append(
                {
                    "output": name,
                    "run_count": data["count"],
                    "total_quantity": round(data["total_quantity"], 1),
                    "input_cost": round(data["input_cost"], 2),
                    "output_value": round(data["output_value"], 2),
                    "value_added": round(value_added, 2),
                }
            )

        # Count active runs
        active = self._store.query_production_runs(status="in_progress", limit=100)

        return {
            "total_completed_runs": len(runs),
            "active_runs": len(active),
            "total_input_cost": round(total_input_cost, 2),
            "total_output_value": round(total_output_value, 2),
            "total_value_added": round(total_value_added, 2),
            "by_output": outputs,
        }
