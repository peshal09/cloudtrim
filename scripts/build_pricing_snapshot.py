"""Regenerate the committed pricing snapshot from the AWS Price List Query API.

Build-time tool (ADR-0002). Run manually with AWS creds when you want to refresh
or extend the snapshot; the output is committed so tests/eval stay deterministic
and the demo runs offline. This never runs in CI or at request time.

Usage:
    python scripts/build_pricing_snapshot.py --region us-east-1 \
        --types t3.small,t3.medium,t3.large,db.t3.small,db.t3.medium

Requires boto3 + credentials. The Price List API is only served from us-east-1 /
ap-south-1, independent of the region you're pricing.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from engine.pricing.client import PricingClient

_SNAPSHOT_PATH = (
    Path(__file__).resolve().parents[1] / "packages/engine/engine/pricing/snapshot.json"
)

_DEFAULT_TYPES = [
    "t3.nano",
    "t3.micro",
    "t3.small",
    "t3.medium",
    "t3.large",
    "t3.xlarge",
    "t3.2xlarge",
    "m5.large",
    "m5.xlarge",
    "m5.2xlarge",
    "m5.4xlarge",
    "c5.large",
    "c5.xlarge",
    "c5.2xlarge",
    "c5.4xlarge",
    "db.t3.micro",
    "db.t3.small",
    "db.t3.medium",
    "db.t3.large",
    "db.m5.large",
    "db.m5.xlarge",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--types", default=",".join(_DEFAULT_TYPES))
    args = parser.parse_args()

    snapshot = json.loads(_SNAPSHOT_PATH.read_text())
    client = PricingClient(allow_live=True)
    region_prices = snapshot["prices"].setdefault(args.region, {})

    updated = 0
    for instance_type in args.types.split(","):
        instance_type = instance_type.strip()
        if not instance_type:
            continue
        # Go straight to the live tier so existing snapshot entries get refreshed,
        # not shadowed. Snapshot stores the hourly unit.
        hourly = client._fetch_live(instance_type, args.region)  # noqa: SLF001 — build tool
        if hourly is None:
            print(f"  skip {instance_type}: no live price (creds/boto3?)")
            continue
        region_prices[instance_type] = round(hourly, 6)
        updated += 1
        print(f"  {instance_type}: {region_prices[instance_type]} USD/hr")

    _SNAPSHOT_PATH.write_text(json.dumps(snapshot, indent=2) + "\n")
    print(f"Wrote {updated} prices for {args.region} -> {_SNAPSHOT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
