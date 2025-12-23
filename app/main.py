from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
import subprocess
import sys
from sqlalchemy import text

from app.database import SessionLocal, engine
from app.models import Base, FaixaOperadora, OperadoraRN1, OperadoraSTFC

app = FastAPI(
    title="API Portabilidade",
    description="API para consulta de portabilidade de operadora telefônica",
    version="2.0.0"
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
    sigla_operadora: Optional[str] = None
    portado: bool = False
    ddd: Optional[str] = None
    prefixo: Optional[str] = None
    numero: Optional[str] = None
    estado: Optional[str] = None
    tipo_numero: Optional[str] = None

class ImportRequest(BaseModel):
    test_mode: bool = False

class StatsResponse(BaseModel):
    operadoras_rn1: int
    operadoras_stfc: int
    faixa_operadora: int
    total_registros: int

class RebootRequest(BaseModel):
    confirm: bool = False
    delay: int = 5  # segundos de delay antes do reboot

# Estado da importação
import_status = {
    "running": False,
    "last_run": None,
    "last_status": None,
    "message": None
}

# Rotas
@app.get("/")
async def root():
    return {
        "status": "online",
        "message": "API Portabilidade - Sistema de Consulta de Operadora",
        "version": "2.0.0",
        "endpoints": {
            "health": "GET /health - Status do sistema",
            "consulta": "POST /consulta - Consultar portabilidade",
            "stats": "GET /stats - Estatísticas da base",
            "import": "POST /import - Importar base de dados",
            "import_status": "GET /import/status - Status da importação",
            "reboot": "POST /reboot - Reiniciar sistema (requer confirmação)"
        }
    }

@app.get("/health")
async def health():
    """Verifica saúde da aplicação e conexão com banco"""
    db_status = "disconnected"
    db_tables_count = 0

    try:
        # Testar conexão com banco
        session = SessionLocal()
        result = session.execute(text("SELECT 1"))
        result.fetchone()
        db_status = "connected"

        # Contar tabelas
        result = session.execute(text("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = 'public'
        """))
        db_tables_count = result.fetchone()[0]

        session.close()
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy" if db_status == "connected" else "unhealthy",
        "database": db_status,
        "tables_count": db_tables_count,
        "ssh": "enabled",
        "ssh_port": 2222,
        "api_port": 8000
    }

@app.get("/stats", response_model=StatsResponse)
async def stats():
    """Retorna estatísticas da base de dados"""
    try:
        session = SessionLocal()

        rn1_count = session.query(OperadoraRN1).count()
        stfc_count = session.query(OperadoraSTFC).count()
        faixa_count = session.query(FaixaOperadora).count()

        session.close()

        return StatsResponse(
            operadoras_rn1=rn1_count,
            operadoras_stfc=stfc_count,
            faixa_operadora=faixa_count,
            total_registros=rn1_count + stfc_count + faixa_count
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter estatísticas: {str(e)}")

@app.post("/consulta", response_model=PortabilidadeResponse)
async def consultar_portabilidade(dados: TelefoneConsulta):
    """
    Consulta portabilidade de um número de telefone

    Formato aceito: DDDNumero (ex: 11987654321)
    """
    # Limpar telefone
    telefone = dados.telefone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")

    if len(telefone) < 10 or len(telefone) > 11:
        raise HTTPException(status_code=400, detail="Telefone inválido. Use formato: DDDNumero (ex: 11987654321)")

    # Extrair componentes
    ddd = telefone[:2]

    # Para celular (11 dígitos): prefixo = 4 primeiros após DDD
    # Para fixo (10 dígitos): prefixo = 3 ou 4 primeiros após DDD
    if len(telefone) == 11:
        prefixo = telefone[2:6]  # 9XXXX
        numero = telefone[6:]    # últimos 4 dígitos
    else:
        prefixo = telefone[2:6]  # XXXX
        numero = telefone[6:]    # últimos 4 dígitos

    try:
        session = SessionLocal()

        # Consultar faixa de operadora
        # Converter número para inteiro para comparar com faixa
        numero_int = int(numero)

        faixa = session.query(FaixaOperadora).filter(
            FaixaOperadora.ddd == ddd,
            FaixaOperadora.prefixo == prefixo,
            FaixaOperadora.faixa_inicio <= numero_int,
            FaixaOperadora.faixa_fim >= numero_int
        ).first()

        session.close()

        if not faixa:
            # Número não encontrado na base
            return PortabilidadeResponse(
                telefone=telefone,
                ddd=ddd,
                prefixo=prefixo,
                numero=numero,
                operadora="Não encontrado",
                portado=False
            )

        # Retornar dados da operadora
        return PortabilidadeResponse(
            telefone=telefone,
            ddd=ddd,
            prefixo=prefixo,
            numero=numero,
            operadora=faixa.nome_operadora,
            sigla_operadora=faixa.sigla_operadora,
            estado=faixa.estado,
            tipo_numero=faixa.tipo_numero,
            portado=True  # Se encontrou na base, pode ter sido portado
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao consultar portabilidade: {str(e)}")

def executar_importacao(test_mode: bool = False):
    """Executa importação em background"""
    global import_status

    import_status["running"] = True
    import_status["message"] = "Iniciando importação..."

    try:
        # Executar script de importação
        cmd = [sys.executable, "-m", "app.import_data"]
        if test_mode:
            cmd.append("--test")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hora timeout
        )

        import_status["running"] = False
        import_status["last_run"] = "completed"
        import_status["last_status"] = "success" if result.returncode == 0 else "error"
        import_status["message"] = result.stdout if result.returncode == 0 else result.stderr

    except subprocess.TimeoutExpired:
        import_status["running"] = False
        import_status["last_run"] = "timeout"
        import_status["last_status"] = "error"
        import_status["message"] = "Importação excedeu tempo limite de 1 hora"
    except Exception as e:
        import_status["running"] = False
        import_status["last_run"] = "failed"
        import_status["last_status"] = "error"
        import_status["message"] = str(e)

@app.post("/import")
async def import_data(request: ImportRequest, background_tasks: BackgroundTasks):
    """
    Importa dados de portabilidade do servidor público

    - test_mode: Se true, importa apenas amostra para teste
    """
    global import_status

    if import_status["running"]:
        raise HTTPException(status_code=409, detail="Importação já está em execução")

    # Executar importação em background
    background_tasks.add_task(executar_importacao, request.test_mode)

    return {
        "status": "started",
        "test_mode": request.test_mode,
        "message": "Importação iniciada. Use GET /import/status para acompanhar progresso."
    }

@app.get("/import/status")
async def import_status_endpoint():
    """Retorna status da importação"""
    return import_status

@app.get("/info")
async def info():
    """Informações de configuração"""
    return {
        "database_url": os.getenv("DATABASE_URL", "Not configured"),
        "postgres_host": os.getenv("POSTGRES_HOST", "localhost"),
        "postgres_port": 5432,
        "ssh_enabled": True,
        "ssh_port": 2222,
        "api_port": 8000,
        "base_url": "https://techsuper.com.br/baseportabilidade/"
    }

def executar_reboot(delay: int):
    """Executa reboot após delay especificado"""
    import time
    import os

    try:
        time.sleep(delay)
        # Tentar reboot via systemctl (mais seguro)
        result = subprocess.run(
            ["systemctl", "reboot"],
            capture_output=True,
            text=True
        )

        # Se falhar, tentar comando reboot direto
        if result.returncode != 0:
            subprocess.run(["reboot"], check=True)

    except Exception as e:
        # Último recurso: reboot via /sbin/reboot
        try:
            subprocess.run(["/sbin/reboot"], check=True)
        except:
            pass

@app.post("/reboot")
async def reboot_system(request: RebootRequest, background_tasks: BackgroundTasks):
    """
    Reinicia o sistema (container/VM)

    ATENÇÃO: Isto irá desligar o sistema em poucos segundos!

    - confirm: Deve ser true para confirmar o reboot
    - delay: Segundos de espera antes do reboot (padrão: 5s)
    """

    if not request.confirm:
        raise HTTPException(
            status_code=400,
            detail="Reboot não confirmado. Envie {\"confirm\": true} para confirmar."
        )

    # Validar delay
    if request.delay < 0 or request.delay > 60:
        raise HTTPException(
            status_code=400,
            detail="Delay deve estar entre 0 e 60 segundos"
        )

    # Executar reboot em background
    background_tasks.add_task(executar_reboot, request.delay)

    return {
        "status": "reboot_scheduled",
        "message": f"Sistema será reiniciado em {request.delay} segundos",
        "delay": request.delay,
        "warning": "A API ficará offline durante o reinício"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
