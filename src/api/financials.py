from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.financial_rule import FinancialRule
from src.schemas.carrier import FinancialRuleCreate, FinancialRuleResponse

router = APIRouter(prefix="/api/v1/financial-rules", tags=["financials"])


@router.post("", response_model=FinancialRuleResponse, status_code=201)
async def create_financial_rule(
    payload: FinancialRuleCreate,
    db: AsyncSession = Depends(get_db),
) -> FinancialRuleResponse:
    rule = FinancialRule(**payload.model_dump())
    db.add(rule)
    await db.flush()
    return FinancialRuleResponse.model_validate(rule)


@router.get("", response_model=list[FinancialRuleResponse])
async def list_financial_rules(
    db: AsyncSession = Depends(get_db),
) -> list[FinancialRuleResponse]:
    result = await db.execute(select(FinancialRule))
    return [FinancialRuleResponse.model_validate(r) for r in result.scalars().all()]


@router.get("/{rule_id}", response_model=FinancialRuleResponse)
async def get_financial_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
) -> FinancialRuleResponse:
    result = await db.execute(
        select(FinancialRule).where(FinancialRule.rule_id == rule_id)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Financial rule not found")
    return FinancialRuleResponse.model_validate(rule)


@router.delete("/{rule_id}", status_code=204)
async def delete_financial_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(FinancialRule).where(FinancialRule.rule_id == rule_id)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Financial rule not found")
    await db.delete(rule)
