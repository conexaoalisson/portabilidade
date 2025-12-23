from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os

app = FastAPI(
    title="API Portabilidade",
    description="API para consulta de portabilidade de operadora",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class TelefoneConsulta(BaseModel):
    telefone: str

class PortabilidadeResponse(BaseModel):
    telefone: str
    operadora: Optional[str] = None
    operadora_original: Optional[str] = None
    portado: bool = False
    ddd: Optional[str] = None
    prefixo: Optional[str] = None

# Rotas
@app.get("/")
async def root():
    return {
        "status": "online",
        "message": "API Portabilidade - Sistema de Consulta de Operadora",
        "version": "1.0.0"
    }

@app.get("/health")
async def health():
    db_status = "connected"
    try:
        # TODO: Verificar conexão com banco
        pass
    except:
        db_status = "disconnected"

    return {
        "status": "healthy",
        "database": db_status,
        "ssh": "enabled",
        "port": 22
    }

@app.post("/consulta", response_model=PortabilidadeResponse)
async def consultar_portabilidade(dados: TelefoneConsulta):
    """
    Consulta portabilidade de um número de telefone

    Formato aceito: DDDNumero (ex: 11987654321)
    """
    telefone = dados.telefone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")

    if len(telefone) < 10 or len(telefone) > 11:
        raise HTTPException(status_code=400, detail="Telefone inválido")

    ddd = telefone[:2]
    prefixo = telefone[2:6] if len(telefone) == 11 else telefone[2:5]

    # TODO: Implementar consulta no banco de dados
    # Por enquanto retorna dados mockados

    return PortabilidadeResponse(
        telefone=telefone,
        operadora="TIM",
        operadora_original="VIVO",
        portado=True,
        ddd=ddd,
        prefixo=prefixo
    )

@app.get("/info")
async def info():
    return {
        "database_url": os.getenv("DATABASE_URL", "Not configured"),
        "postgres_host": os.getenv("POSTGRES_HOST", "Not configured"),
        "ssh_enabled": True,
        "ssh_port": 22,
        "api_port": 8000
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
