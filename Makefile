# Makefile for jkm-ttf-arbitrage.
#
# make is not installed on every machine, a stock Windows box among them. Every
# target below is a single command you can paste into a shell instead, and the
# help target prints those commands. Recipes use tabs, POSIX sh.

.DEFAULT_GOAL := help
.PHONY: help data data-offline data-jobs routes test validate gate site

help:
	@echo "targets"
	@echo "  make data          refresh every source into data/cache and rewrite data/manifest.json"
	@echo "                     equivalent: python scripts/refresh.py"
	@echo "  make data-offline  revalidate the committed caches and rewrite the manifest, no network"
	@echo "                     equivalent: python scripts/refresh.py --offline"
	@echo "  make data-jobs     list the refresh jobs and the series each one owns, run nothing"
	@echo "                     equivalent: python scripts/refresh.py --list"
	@echo "  make routes        recompute the four sea routes with searoute 1.6.0 and rewrite the seed"
	@echo "                     equivalent: python scripts/routes.py (needs searoute==1.6.0 installed)"
	@echo "  make test          the python suite"
	@echo "                     equivalent: python -m pytest tests"
	@echo "  make validate      the node validators, no network, no python"
	@echo "                     equivalent: node tools/<each>.mjs, for validate-data, validate-engine,"
	@echo "                                 validate-artifacts, check-paths, check-literals, check-styles"
	@echo "  make gate          everything that must pass before a change lands"
	@echo "                     equivalent: python scripts/refresh.py --offline"
	@echo "                                 python -m pytest tests"
	@echo "                                 the node validators above"
	@echo "  make site          the page in a headless browser: the calculator's form and every screenshot"
	@echo "                     equivalent: python scripts/serve.py --port 8131   (in another shell)"
	@echo "                                 node tools/check-model-form.mjs"
	@echo "                                 node scripts/screenshots.mjs"

data:
	python scripts/refresh.py

data-offline:
	python scripts/refresh.py --offline

data-jobs:
	python scripts/refresh.py --list

routes:
	python scripts/routes.py

test:
	python -m pytest tests

validate:
	node tools/validate-data.mjs
	node tools/validate-engine.mjs
	node tools/validate-artifacts.mjs
	node tools/check-paths.mjs
	node tools/check-literals.mjs
	node tools/check-styles.mjs

gate:
	python scripts/refresh.py --offline
	python -m pytest tests
	node tools/validate-data.mjs
	node tools/validate-engine.mjs
	node tools/validate-artifacts.mjs
	node tools/check-paths.mjs
	node tools/check-literals.mjs
	node tools/check-styles.mjs

site:
	node tools/check-model-form.mjs
	node scripts/screenshots.mjs
