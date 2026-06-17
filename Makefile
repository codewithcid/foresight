# Foresight — convenience targets for macOS / Linux.
# On Windows use the PowerShell scripts instead: .\setup.ps1, .\run-backend.ps1, .\run-frontend.ps1
PY=.venv/bin/python

.PHONY: setup data backend frontend

setup:
	python3 -m venv .venv
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r requirements.txt
	$(PY) data/generate.py
	cd frontend && npm install

data:
	$(PY) data/generate.py

backend:
	cd backend && ../$(PY) -m uvicorn main:app --host 127.0.0.1 --port 8000

frontend:
	cd frontend && npm run dev
