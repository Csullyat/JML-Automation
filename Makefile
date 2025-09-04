# Makefile for filevine-automation
.PHONY: install test onboard terminate setup

install:
	pip install -r requirements.txt

onboard:
	python scripts/run.py onboard

onboard-test:
	python scripts/run.py onboard --test

terminate:
	python scripts/run.py terminate

setup:
	powershell -ExecutionPolicy Bypass -File scripts/setup_windows.ps1

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
