from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def export_openapi(output: Path) -> None:
    from app.main import app

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = output.with_suffix(f"{output.suffix}.tmp")
    temporary_output.write_text(
        json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_output.replace(output)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export the FastAPI OpenAPI schema for frontend generation."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("frontend/openapi.json"),
        help="Destination path (default: frontend/openapi.json)",
    )
    arguments = parser.parse_args()
    output = arguments.output.resolve()
    os.chdir(Path(__file__).resolve().parents[1])
    export_openapi(output)


if __name__ == "__main__":
    main()
