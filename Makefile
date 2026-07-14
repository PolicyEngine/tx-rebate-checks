.PHONY: dev build test lint install pipeline pipeline-districts

install:
	cd frontend && npm install

dev:
	cd frontend && npm run dev

build:
	cd frontend && npm run build

test:
	cd frontend && npm run test

lint:
	cd frontend && npm run lint

pipeline:
	modal run scripts/modal_pipeline.py

pipeline-districts:
	modal run scripts/modal_district_pipeline.py
