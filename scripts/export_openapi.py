"""Export the API's OpenAPI schema to docs/openapi.json (BLUEPRINT.md §8 Week 6).

    python scripts/export_openapi.py

The live schema is also served at /openapi.json with interactive docs at /docs.
"""

from __future__ import annotations

import json
from pathlib import Path

from api.main import app


def main() -> int:
    out = Path(__file__).resolve().parents[1] / "docs" / "openapi.json"
    out.write_text(json.dumps(app.openapi(), indent=2) + "\n")
    paths = len(app.openapi().get("paths", {}))
    print(f"wrote {out} ({paths} paths)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
