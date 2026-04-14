# FuelNearMe

FuelNearMe is a simple Python utility that retrieves data from the UK Government’s
solution to centralising fuel station prices across the country. You can read more
about it [here](https://www.fuel-finder.service.gov.uk/).

It lacks useful features like crowdsourcing data, but it aims to be a quick and simple
way to find the cheapest fuel near you.

## Usage

[Geopy](https://github.com/geopy/geopy) is used to get the coordinates to search for
fuel stations in the surrounding area in miles. It is also used to calculate the
geodesic distance between the starting coordinates and the coordinates of a fuel
station - this is an estimate and may not represent the actual distance.

It's relatively easy to use. For example, you can search for service stations
around LS11 (Leeds), within a 5 mile radius, and to sort the results by distance.

```
python3 main.py --address "LS11" --radius 5 --sort "distance"
```

### Sort Options

You can sort by: `distance`, `e10`, `e5`, `b7s`

If this parameter isn't used, it automatically defaults to e10 (standard petrol).

## Installation

For now, create a [virtual environment](https://docs.python.org/3/library/venv.html),
activate it, and then install the dependencies from the `requirements.txt`.

```
pip install -r requirements.txt
```

## To-Do & Goals

- [ ] Access data via API (requires OAuth 2.0 credentials)
- [ ] Improve aesthetics of output (i.e. table view)
- [ ] Create installable Python package for CLI
- [ ] Show premium diesel prices
- [ ] Avoid `for` loops - use NumPy operations to speed up operations
- [ ] Use bounding boxes to discard stations outside of coordinate ranges (e.g. ±0.1 degrees)
- [ ] Cache Nominatim results to reduce hits on API
- [ ] Handle API timeouts using `while` loops
- [ ] Add true cost of fuel - cheaper fuel further away but driving there still costs
- [ ] Create a real-time TUI - **depends on API functionality**
- [ ] Modularise the code - split into functions/classes
- [ ] Replace `print` with `logging` module
