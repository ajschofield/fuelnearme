import json
import os
from pathlib import Path

from extract.fetch import fetch_all_prices, fetch_all_stations, generate_access_token


def main(
    output_dir: Path = Path("/data"),
    effective_start_timestamp: str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    access_token = generate_access_token(client_id, client_secret)
    stations = fetch_all_stations(
        access_token, effective_start_timestamp=effective_start_timestamp
    )
    prices = fetch_all_prices(
        access_token, effective_start_timestamp=effective_start_timestamp
    )

    (output_dir / "stations.json").write_text(json.dumps(stations))
    (output_dir / "prices.json").write_text(json.dumps(prices))

    print(f"Extracted {len(stations)} stations and {len(prices)} price records.")


if __name__ == "__main__":
    main(
        output_dir=Path(os.getenv("OUTPUT_DIR", "/data")),
        effective_start_timestamp=os.getenv("EFFECTIVE_START_TIMESTAMP"),
        client_id=os.environ["CLIENT_ID"],
        client_secret=os.environ["CLIENT_SECRET"],
    )
