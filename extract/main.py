import json
import os
from pathlib import Path

from extract.fetch import fetch_all_prices, fetch_all_stations


def main(
    output_dir: Path = Path("/data"),
    effective_start_timestamp: str | None = None,
) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    stations = fetch_all_stations(effective_start_timestamp=effective_start_timestamp)
    prices = fetch_all_prices(effective_start_timestamp=effective_start_timestamp)

    (output_dir / "stations.json").write_text(json.dumps(stations))
    (output_dir / "prices.json").write_text(json.dumps(prices))

    print(f"Extracted {len(stations)} stations and {len(prices)} price records.")


if __name__ == "__main__":
    main(
        output_dir=Path(os.getenv("OUTPUT_DIR", "/data")),
        effective_start_timestamp=os.getenv("EFFECTIVE_START_TIMESTAMP"),
    )
