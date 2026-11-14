"""FastAPI dependencies."""

from functools import lru_cache

from fincalc.core.tax import TaxConfig, load_tax_config


@lru_cache(maxsize=1)
def get_tax_config() -> TaxConfig:
    """Tax config loaded once per process (override in tests via dependency_overrides)."""
    return load_tax_config()
