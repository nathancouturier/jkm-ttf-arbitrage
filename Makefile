# make          build the site's data, run the tests, write the research note
# make serve    serve the site at http://localhost:8000/jkm-ttf-arbitrage/
# make refresh  fetch the public series, each source on its own and kept only if the study still stands on it

export PYTHONPATH := src
PYTHON ?= python

all: build test note

build:
	$(PYTHON) -m arb.build

test:
	$(PYTHON) -m pytest -q

note:
	$(PYTHON) -m arb.note

refresh:
	$(PYTHON) -m arb.fetch --check

serve:
	$(PYTHON) -m arb.serve

.PHONY: all build test note refresh serve
