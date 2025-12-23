#!/bin/bash

# Iniciar SSH
service ssh start

# Iniciar aplicação FastAPI
cd /app
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
