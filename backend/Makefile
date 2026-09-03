.DEFAULT_GOAL := help
PY := .venv/bin/python
UV := uv

MODEL   ?= llama3.2:3b
EMBED   ?= nomic-embed-text
LIMIT   ?= 260
SAMPLES ?= 5
CORPUS  ?= data/corpus/$(subst :,-,$(MODEL)).jsonl
MODELDIR?= models/$(subst :,-,$(MODEL))
EVALCORPUS ?= data/corpus/$(subst :,-,$(MODEL))-eval.jsonl

.PHONY: help setup models doctor build train ablate report score serve test lint fmt clean all

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

setup:  ## Create the venv and install the package with all extras
	$(UV) venv --python 3.12 .venv
	$(UV) pip install --python $(PY) -e ".[all,dev]"

models:  ## Pull the Ollama models this project uses
	ollama pull $(MODEL)
	ollama pull $(EMBED)

doctor:  ## Check Ollama connectivity, models, logprobs and embeddings
	$(PY) -m halluciwatch.cli doctor --model $(MODEL) --embed-model $(EMBED)

build:  ## Generate a labelled corpus (resumable)
	$(PY) -m halluciwatch.cli build --model $(MODEL) --embed-model $(EMBED) \
		--sources trivia_qa nq_open --limit $(LIMIT) --samples $(SAMPLES) --out $(CORPUS)

train:  ## Train and calibrate the detector
	$(PY) -m halluciwatch.cli train --corpus $(CORPUS) --out $(MODELDIR)

ablate:  ## Measure what each signal tier buys
	$(PY) -m halluciwatch.cli ablate --corpus $(CORPUS) --samples $(SAMPLES) \
		--json $(MODELDIR)/ablation.json

refresh:  ## Recompute sampling features from stored samples (no regeneration)
	$(PY) -m halluciwatch.cli refresh --corpus $(CORPUS)

dashboard:  ## Export every dashboard metric to the website as JSON
	$(PY) scripts/export_dashboard.py --corpus $(CORPUS) --model-dir $(MODELDIR) \
		--eval-corpus $(EVALCORPUS) \
		--out ../website/src/data/dashboard.json

report:  ## Regenerate RESULTS.md from the corpus and trained model
	$(PY) scripts/report.py --corpus $(CORPUS) --model-dir $(MODELDIR) --out RESULTS.md

score:  ## Score a question: make score Q="who invented radio?"
	$(PY) -m halluciwatch.cli score $(Q) --model-dir $(MODELDIR)

serve:  ## Run the HTTP API on :8000
	$(PY) -m halluciwatch.cli serve --model-dir $(MODELDIR) --model $(MODEL)

test:  ## Run the unit tests
	$(PY) -m pytest tests/ -q

lint:  ## Lint and type-check
	$(PY) -m ruff check src tests scripts
	$(PY) -m ruff format --check src tests scripts

fmt:  ## Auto-format
	$(PY) -m ruff format src tests scripts
	$(PY) -m ruff check --fix src tests scripts

all: doctor build train ablate report dashboard  ## Full pipeline end to end

clean:  ## Remove caches and build artefacts
	rm -rf .pytest_cache .ruff_cache **/__pycache__ dist build *.egg-info
