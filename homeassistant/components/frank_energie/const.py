"""Constants for the Frank Energie integration."""
from __future__ import annotations

from dataclasses import dataclass

from python_frank_energie.models import Invoices, MarketPrices, MonthSummary

DOMAIN = "frank_energie"

CONF_COORDINATOR = "coordinator"
ATTR_TIME = "from_time"

DATA_ELECTRICITY = "electricity"
DATA_GAS = "gas"
DATA_MONTH_SUMMARY = "month_summary"
DATA_INVOICES = "invoices"

SERVICE_NAME_PRICES = "Prices"
SERVICE_NAME_COSTS = "Costs"


@dataclass
class DeviceResponseEntry:
    """Dict describing a single response entry."""

    electricity: MarketPrices
    gas: MarketPrices
    month_summary: MonthSummary | None
    invoices: Invoices | None
