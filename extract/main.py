import json
import os
from pathlib import Path

from extract.fetch import fetch_all_prices, fetch_all_stations, generate_access_token


def read_secret(name: str) -> str:
    """Return a secret from `{name}_FILE` (a Docker secret) if set, else `{name}`.

    Lets the same code read plaintext env in dev and file-based secrets in prod.
    """
    file_path = os.environ.get(f"{name}_FILE")
    if file_path:
        return Path(file_path).read_text().strip()
    return os.environ[name]


def read_watermark(data_dir: Path) -> str | None:
    """Return the watermark timestamp written by the load `prepare` step.

    `prepare` writes `watermark.txt` to the shared volume: the last completed
    run's timestamp, or empty for a full run. Returns None when the file is
    absent (e.g. a local CLI run with no prior prepare) or empty.
    """
    path = Path(data_dir) / "watermark.txt"
    if path.exists():
        return path.read_text().strip() or None
    return None


def main(
    output_dir: Path = Path("/data"),
    effective_start_timestamp: str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # An explicit timestamp wins; otherwise fall back to the watermark file.
    if effective_start_timestamp is None:
        effective_start_timestamp = read_watermark(output_dir)

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
        client_id=read_secret("CLIENT_ID"),
        client_secret=read_secret("CLIENT_SECRET"),
    )
