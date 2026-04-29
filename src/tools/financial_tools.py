from langchain_core.tools import tool
from sqlalchemy import select
from src.database import get_sync_db
from src.models.financial_rule import FinancialRule


@tool
def query_financial_rules(sku_id: str) -> dict:
    """
    Retrieve the financial rules (expedite budget, auto-approve ceiling,
    penalty per day) for a given SKU. Falls back to the global default rule
    (sku_id IS NULL) if no SKU-specific rule exists.
    Returns max_expedite_budget, auto_approve_ceiling, penalty_per_day,
    baseline_freight_cost, and currency.
    """
    db = get_sync_db()
    try:
        # SKU-specific rule first
        result = db.execute(
            select(FinancialRule).where(FinancialRule.sku_id == sku_id)
        )
        rule = result.scalars().first()

        # Global default fallback
        if not rule:
            result = db.execute(
                select(FinancialRule).where(FinancialRule.sku_id.is_(None))
            )
            rule = result.scalars().first()

        if not rule:
            return {
                "found": False,
                "max_expedite_budget": 15000.0,
                "auto_approve_ceiling": 5000.0,
                "penalty_per_day": 50000.0,
                "baseline_freight_cost": 0.0,
                "currency": "USD",
                "note": "No rule found — using system defaults",
            }

        return {
            "found": True,
            "rule_id": rule.rule_id,
            "sku_id": rule.sku_id,
            "max_expedite_budget": rule.max_expedite_budget,
            "auto_approve_ceiling": rule.auto_approve_ceiling,
            "penalty_per_day": rule.penalty_per_day,
            "baseline_freight_cost": rule.baseline_freight_cost,
            "currency": rule.currency,
        }
    finally:
        db.close()


FINANCIAL_TOOLS = [query_financial_rules]
