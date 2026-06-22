.PHONY: test lint check download-2mrs build-2mrs

test:
	pytest -q

lint:
	ruff check pipeline scripts tests

check: test lint

# Requires a live internet connection to VizieR.
download-2mrs:
	python scripts/download_2mrs.py

build-2mrs:
	python scripts/build_2mrs_lightcone.py
