"""Calculator endpoints: validate input, call the core function, return the result."""

from typing import Annotated

from fastapi import APIRouter, Depends

from fincalc.api.dependencies import get_tax_config
from fincalc.core.etf_costs import etf_costs
from fincalc.core.inflation import compound_with_inflation, inflation
from fincalc.core.models import (
    CompoundInflationInput,
    CompoundInflationResult,
    EtfCostInput,
    EtfCostResult,
    InflationInput,
    InflationResult,
    TbszInput,
    TbszResult,
)
from fincalc.core.tax import TaxConfig
from fincalc.core.tbsz import tbsz

router = APIRouter(prefix="/calc", tags=["calculators"])


@router.post("/compound", summary="Compound interest with monthly contributions")
def calc_compound(inp: CompoundInflationInput) -> CompoundInflationResult:
    return compound_with_inflation(inp)


@router.post("/inflation", summary="Inflation-adjusted (real) value")
def calc_inflation(inp: InflationInput) -> InflationResult:
    return inflation(inp)


@router.post("/etf-costs", summary="Impact of ETF expense ratios (TER)")
def calc_etf_costs(inp: EtfCostInput) -> EtfCostResult:
    return etf_costs(inp)


@router.post("/tbsz", summary="TBSZ vs. regular brokerage account")
def calc_tbsz(inp: TbszInput, config: Annotated[TaxConfig, Depends(get_tax_config)]) -> TbszResult:
    return tbsz(inp, config)
