"""Deterministic OPIU ERP rule catalog and resolver."""

from .opiu_indicator_resolver import OPIUIndicatorResolver
from .opiu_rule_builder import build_opiu_rule_catalog
from .opiu_rule_models import (
    AUTO_MATCH,
    AMBIGUOUS,
    NOT_FOUND,
    OPIUMatchResult,
    OPIURule,
    OPIURuleCatalog,
)

__all__ = [
    "AMBIGUOUS",
    "AUTO_MATCH",
    "NOT_FOUND",
    "OPIUIndicatorResolver",
    "OPIUMatchResult",
    "OPIURule",
    "OPIURuleCatalog",
    "build_opiu_rule_catalog",
]

