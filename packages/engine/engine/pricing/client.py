"""Three-tier pricing client (BLUEPRINT.md §5, ADR-0002).

get_price(instance_type, region) resolves an on-demand monthly USD price through:
  1. committed snapshot.json  — deterministic; the ONLY tier tests/eval touch
  2. on-disk cache            — ~/.cloudtrim/pricing_cache/prices.json
  3. live Price List Query API (boto3 get_products) — only if creds/boto3 present

Determinism first: with default construction the snapshot answers everything our
fixtures need, so no test or eval run hits the network. The live tier is an
optional accuracy upgrade, cached to disk after the first fetch.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_SNAPSHOT_PATH = Path(__file__).parent / "snapshot.json"

# The Price List Query API is only served from these regions (ADR-0002 caveat).
_PRICING_API_REGION = "us-east-1"

# Region code -> Price List "location" display name (subset; extend as needed).
_REGION_NAMES: dict[str, str] = {
    "us-east-1": "US East (N. Virginia)",
    "us-east-2": "US East (Ohio)",
    "us-west-1": "US West (N. California)",
    "us-west-2": "US West (Oregon)",
    "eu-west-1": "EU (Ireland)",
    "eu-central-1": "EU (Frankfurt)",
    "ap-south-1": "Asia Pacific (Mumbai)",
    "ap-southeast-1": "Asia Pacific (Singapore)",
    "ap-northeast-1": "Asia Pacific (Tokyo)",
}


class PricingClient:
    def __init__(
        self,
        cache_dir: Path | None = None,
        allow_live: bool = True,
        snapshot_path: Path | None = None,
    ) -> None:
        self._snapshot = json.loads((snapshot_path or _SNAPSHOT_PATH).read_text())
        self._prices: dict[str, dict[str, float]] = self._snapshot["prices"]
        self._hours = self._snapshot["meta"]["hours_per_month"]
        self._default_region = self._snapshot["meta"]["default_region"]
        self._allow_live = allow_live
        default_cache = Path.home() / ".cloudtrim" / "pricing_cache"
        self._cache_dir = cache_dir if cache_dir is not None else default_cache
        self._cache = self._load_cache()

    def get_price(self, instance_type: str | None, region: str | None = None) -> float | None:
        """Monthly USD (rounded to cents) for an on-demand instance, or None if unknown."""
        if not instance_type:
            return None
        region = region or self._default_region
        hourly = self._from_snapshot(instance_type, region)
        if hourly is None:
            hourly = self._cache.get(self._key(instance_type, region))
        if hourly is None and self._allow_live:
            hourly = self._fetch_live(instance_type, region)
            if hourly is not None:
                self._store_cache(instance_type, region, hourly)
        if hourly is None:
            return None
        return round(hourly * self._hours, 2)

    # --- tier 1: snapshot ----------------------------------------------------

    def _from_snapshot(self, instance_type: str, region: str) -> float | None:
        by_region = self._prices.get(region) or self._prices.get(self._default_region, {})
        return by_region.get(instance_type)

    # --- tier 2: disk cache --------------------------------------------------

    @staticmethod
    def _key(instance_type: str, region: str) -> str:
        return f"{region}|{instance_type}"

    def _load_cache(self) -> dict[str, float]:
        path = self._cache_dir / "prices.json"
        try:
            return json.loads(path.read_text())
        except (FileNotFoundError, ValueError):
            return {}

    def _store_cache(self, instance_type: str, region: str, hourly: float) -> None:
        self._cache[self._key(instance_type, region)] = hourly
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            (self._cache_dir / "prices.json").write_text(json.dumps(self._cache, indent=2))
        except OSError:
            pass  # cache is best-effort; never fail a price lookup on a write error

    # --- tier 3: live Price List Query API -----------------------------------

    def _fetch_live(self, instance_type: str, region: str) -> float | None:
        try:
            import boto3  # imported lazily; optional dependency
        except ImportError:
            return None
        location = _REGION_NAMES.get(region)
        if location is None:
            return None
        try:
            client = boto3.client("pricing", region_name=_PRICING_API_REGION)
            if instance_type.startswith("db."):
                filters = [
                    {"Type": "TERM_MATCH", "Field": "instanceType", "Value": instance_type},
                    {"Type": "TERM_MATCH", "Field": "location", "Value": location},
                    {"Type": "TERM_MATCH", "Field": "deploymentOption", "Value": "Single-AZ"},
                    {"Type": "TERM_MATCH", "Field": "databaseEngine", "Value": "MySQL"},
                ]
                service = "AmazonRDS"
            else:
                filters = [
                    {"Type": "TERM_MATCH", "Field": "instanceType", "Value": instance_type},
                    {"Type": "TERM_MATCH", "Field": "location", "Value": location},
                    {"Type": "TERM_MATCH", "Field": "tenancy", "Value": "Shared"},
                    {"Type": "TERM_MATCH", "Field": "operatingSystem", "Value": "Linux"},
                    {"Type": "TERM_MATCH", "Field": "preInstalledSw", "Value": "NA"},
                    {"Type": "TERM_MATCH", "Field": "capacitystatus", "Value": "Used"},
                ]
                service = "AmazonEC2"
            resp = client.get_products(ServiceCode=service, Filters=filters, MaxResults=1)
            return _parse_ondemand_hourly(resp.get("PriceList", []))
        except (
            Exception
        ):  # noqa: BLE001 — best-effort live tier; snapshot/cache are the source of truth
            return None


def _parse_ondemand_hourly(price_list: list[Any]) -> float | None:
    for item in price_list:
        doc = json.loads(item) if isinstance(item, str) else item
        on_demand = doc.get("terms", {}).get("OnDemand", {})
        for term in on_demand.values():
            for dim in term.get("priceDimensions", {}).values():
                usd = dim.get("pricePerUnit", {}).get("USD")
                if usd is not None:
                    return float(usd)
    return None


_default_client = PricingClient()


def get_price(instance_type: str | None, region: str | None = None) -> float | None:
    """Module-level convenience using a shared default client."""
    return _default_client.get_price(instance_type, region)
