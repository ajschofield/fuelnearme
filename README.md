# FuelNearMe

FuelNearMe is a simple Python utility that retrieves data from the UK Government’s
solution to centralising fuel station prices across the country. You can read more
about it [here](https://www.fuel-finder.service.gov.uk/).

It lacks useful features like crowdsourcing data, but it aims to be a quick and simple
way to find the cheapest fuel near you.

## Installation

This project uses `uv` for dependency management and environment handling. In the
project's current state, follow the steps below to install (will improve further
in development!)

### Clone

```
git clone https://github.com/ajschofield/FuelNearMe.git
cd FuelNearMe
```

### Sync

```
uv sync
```

### Install

```
uv pip install -e .
```

## Usage

[Geopy](https://github.com/geopy/geopy) is used to get the coordinates to search for
fuel stations in the surrounding area in miles. It is also used to calculate the
geodesic distance between the starting coordinates and the coordinates of a fuel
station - this is an estimate and may not represent the actual distance.

You can run the utility directly via `uv` - the tool handles everything for you.

```
uv run fnme [-h] -a ADDRESS [-r RADIUS] [-s {e10,e5,b7s,distance}]
```

It's relatively easy to use. For example, you can search for service stations
around LS11 (Leeds), within a 5 mile radius, and to sort the results by distance.

```
uv run fnme --address "LS11" --radius 5 --sort "distance"
```

If you wish to run the command-line module directly without using the registered
script, you can do so by running this from the root of the repository.

```
uv run python -m fnme.cli [-h] -a ADDRESS [-r RADIUS] [-s {e10,e5,b7s,distance}]
```

### Sort Options

You can sort by: `distance`, `e10`, `e5`, `b7s`

If this parameter isn't used, it automatically defaults to e10 (standard petrol).
