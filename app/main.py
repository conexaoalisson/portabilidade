from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os
import subprocess
import sys
import psutil
import json
import time
from datetime import datetime, timedelta
from sqlalchemy import text

from app.database import SessionLocal, engine
from app.models import Base, FaixaOperadora, OperadoraRN1, OperadoraSTFC, PortabilidadeHistorico

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
            "import_historico": "POST /import/historico - Importar 51M registros históricos",
            "import_historico_status": "GET /import/historico/status - Status importação histórica",
            "import_historico_progress": "GET /import/historico/progress - Página web com progresso",
            "import_historico_reset": "DELETE /import/historico/reset - Resetar importação (limpar tudo)",
            "import_historico_reset_page": "GET /import/historico/reset-page - Página dedicada para reset",
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
        "api_port": 80
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
        "api_port": 80,
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

# Importação Histórica (51M registros)
def get_historico_status() -> Dict[str, Any]:
    """Obtém status da importação histórica"""
    try:
        session = SessionLocal()

        # Contar registros
        count_result = session.execute(text("SELECT COUNT(*) FROM portabilidade_historico"))
        current_count = count_result.fetchone()[0]

        # Verificar se processo está rodando
        import_running = False
        import_pid = None
        start_time = None

        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'import_chunks_smart.py' in cmdline or 'import_historico_auto.sh' in cmdline:
                    import_running = True
                    import_pid = proc.info['pid']
                    start_time = proc.info['create_time']
                    break
            except:
                pass

        # Verificar arquivo de chunks
        chunks_info = {}
        temp_dir = '/tmp/portabilidade_chunks'
        if os.path.exists(temp_dir):
            chunks = [f for f in os.listdir(temp_dir) if f.endswith('.csv')]
            chunks_info = {
                'total_chunks': len(chunks),
                'current_chunk': len(chunks) - len([f for f in chunks if os.path.exists(os.path.join(temp_dir, f))])
            }

        # Obter último count de 30 segundos atrás para calcular velocidade
        speed = 0
        try:
            # Criar tabela temporária se não existir
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS import_stats (
                    id SERIAL PRIMARY KEY,
                    record_count BIGINT,
                    timestamp TIMESTAMP DEFAULT NOW()
                )
            """))
            session.commit()

            # Salvar contagem atual
            session.execute(text("""
                INSERT INTO import_stats (record_count) VALUES (:count)
            """), {"count": current_count})
            session.commit()

            # Obter contagem de 30 segundos atrás
            result = session.execute(text("""
                SELECT record_count, EXTRACT(EPOCH FROM (NOW() - timestamp)) as seconds_ago
                FROM import_stats
                WHERE timestamp > NOW() - INTERVAL '60 seconds'
                ORDER BY timestamp ASC
                LIMIT 1
            """))
            old_data = result.fetchone()

            if old_data and old_data[1] > 0:
                records_diff = current_count - old_data[0]
                time_diff = old_data[1]
                speed = int(records_diff / time_diff) if time_diff > 0 else 0

            # Limpar registros antigos
            session.execute(text("""
                DELETE FROM import_stats
                WHERE timestamp < NOW() - INTERVAL '5 minutes'
            """))
            session.commit()

        except:
            pass

        session.close()

        # Calcular progresso
        TOTAL_EXPECTED = 51618684
        progress = (current_count / TOTAL_EXPECTED) * 100 if TOTAL_EXPECTED > 0 else 0

        # Calcular tempo estimado
        eta_seconds = 0
        if speed > 0:
            remaining = TOTAL_EXPECTED - current_count
            eta_seconds = remaining / speed

        # Tempo decorrido
        elapsed_seconds = 0
        if start_time:
            elapsed_seconds = time.time() - start_time

        return {
            'running': import_running,
            'current_records': current_count,
            'total_expected': TOTAL_EXPECTED,
            'progress_percent': round(progress, 2),
            'chunks_info': chunks_info,
            'completed': current_count >= TOTAL_EXPECTED,
            'speed': speed,
            'eta_seconds': int(eta_seconds),
            'elapsed_seconds': int(elapsed_seconds)
        }

    except Exception as e:
        return {
            'error': str(e),
            'running': False,
            'current_records': 0,
            'progress_percent': 0,
            'speed': 0,
            'eta_seconds': 0,
            'elapsed_seconds': 0
        }

@app.post("/import/historico")
async def import_historico(background_tasks: BackgroundTasks):
    """
    Inicia importação dos 51M registros históricos
    """
    status = get_historico_status()

    if status.get('running'):
        raise HTTPException(status_code=409, detail="Importação histórica já está em execução")

    if status.get('completed'):
        raise HTTPException(status_code=400, detail="Importação histórica já foi concluída")

    # Executar em background
    def run_import():
        subprocess.run(["/app/import_historico_auto.sh"],
                      env={**os.environ, 'AUTO_IMPORT_HISTORICO': 'true'})

    background_tasks.add_task(run_import)

    return {
        "status": "started",
        "message": "Importação histórica iniciada em background",
        "total_records": 51618684,
        "monitor_url": "/import/historico/progress"
    }

@app.delete("/import/historico/reset")
async def reset_import_historico():
    """
    Reseta a importação histórica (limpa tabela e arquivos)
    """
    try:
        session = SessionLocal()

        # Verificar se tem processo rodando
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'import_chunks' in cmdline or 'import_historico' in cmdline or 'import_low_memory' in cmdline or 'import_line_by_line' in cmdline:
                    proc.terminate()  # Terminar processo
            except:
                pass

        # Limpar tabela
        session.execute(text("TRUNCATE TABLE portabilidade_historico"))
        session.execute(text("DROP TABLE IF EXISTS import_stats"))
        session.commit()

        # Limpar arquivos
        import shutil

        # Remover chunks
        if os.path.exists('/tmp/portabilidade_chunks'):
            shutil.rmtree('/tmp/portabilidade_chunks')

        if os.path.exists('/app/data/portabilidade_chunks'):
            shutil.rmtree('/app/data/portabilidade_chunks')

        # Remover CSV
        for csv_path in ['/tmp/export_full_mysql.csv', '/app/data/export_full_mysql.csv']:
            if os.path.exists(csv_path):
                os.remove(csv_path)

            gz_path = csv_path + '.gz'
            if os.path.exists(gz_path):
                os.remove(gz_path)

        session.close()

        return {
            "status": "success",
            "message": "Importação resetada com sucesso",
            "actions": [
                "Tabela portabilidade_historico limpa",
                "Arquivos CSV removidos",
                "Chunks temporários removidos",
                "Processos de importação terminados"
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao resetar: {str(e)}")

@app.get("/import/historico/status")
async def import_historico_status():
    """Retorna status da importação histórica em JSON"""
    return get_historico_status()

@app.get("/import/historico/reset-page", response_class=HTMLResponse)
async def import_historico_reset_page():
    """Página dedicada para reset da importação"""
    status = get_historico_status()

    html_content = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Reset Importação - Portabilidade</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background-color: #0f172a;
                color: #e2e8f0;
                margin: 0;
                padding: 20px;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
            }}
            .container {{
                background-color: #1e293b;
                border-radius: 16px;
                padding: 32px;
                max-width: 500px;
                width: 100%;
                border: 2px solid rgba(239, 68, 68, 0.3);
            }}
            h1 {{
                color: #ef4444;
                text-align: center;
                margin: 0 0 24px 0;
                font-size: 32px;
            }}
            .warning-box {{
                background-color: rgba(239, 68, 68, 0.1);
                border: 1px solid rgba(239, 68, 68, 0.3);
                border-radius: 8px;
                padding: 16px;
                margin-bottom: 24px;
            }}
            .stats {{
                background-color: #334155;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 24px;
            }}
            .stat-item {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 12px;
                padding-bottom: 12px;
                border-bottom: 1px solid #475569;
            }}
            .stat-item:last-child {{
                margin-bottom: 0;
                padding-bottom: 0;
                border-bottom: none;
            }}
            .reset-button {{
                width: 100%;
                padding: 20px;
                background: #dc2626;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 18px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }}
            .reset-button:hover {{
                background: #b91c1c;
                transform: scale(1.02);
            }}
            .back-link {{
                display: block;
                text-align: center;
                margin-top: 24px;
                color: #60a5fa;
                text-decoration: none;
            }}
            .back-link:hover {{
                text-decoration: underline;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🗑️ Reset Total da Importação</h1>

            <div class="warning-box">
                <h3 style="color: #f87171; margin-top: 0;">⚠️ ATENÇÃO - AÇÃO IRREVERSÍVEL</h3>
                <p style="color: #fca5a5; margin: 0;">
                    Esta ação irá APAGAR permanentemente todos os dados importados e arquivos.
                    Não há como desfazer esta operação!
                </p>
            </div>

            <div class="stats">
                <h3 style="margin-top: 0; color: #f8fafc;">O que será apagado:</h3>
                <div class="stat-item">
                    <span>Registros no banco:</span>
                    <strong style="color: #ef4444;">{status['current_records']:,}</strong>
                </div>
                <div class="stat-item">
                    <span>Arquivos CSV:</span>
                    <strong style="color: #ef4444;">Todos</strong>
                </div>
                <div class="stat-item">
                    <span>Chunks temporários:</span>
                    <strong style="color: #ef4444;">Todos</strong>
                </div>
                <div class="stat-item">
                    <span>Processos em execução:</span>
                    <strong style="color: #ef4444;">Serão parados</strong>
                </div>
            </div>

            <button class="reset-button" onclick="confirmarReset()">
                CONFIRMAR RESET TOTAL
            </button>

            <div id="message" style="margin-top: 16px; text-align: center;"></div>

            <a href="/import/historico/progress" class="back-link">
                ← Voltar para página de progresso
            </a>
        </div>

        <script>
            function confirmarReset() {{
                if (!confirm('Última confirmação:\\n\\nTem ABSOLUTA CERTEZA que deseja apagar {status['current_records']:,} registros e todos os arquivos?\\n\\nEsta ação NÃO pode ser desfeita!')) {{
                    return;
                }}

                const button = document.querySelector('.reset-button');
                const message = document.getElementById('message');

                button.disabled = true;
                button.innerHTML = '⏳ EXECUTANDO RESET...';

                fetch('/import/historico/reset', {{
                    method: 'DELETE'
                }})
                .then(response => response.json())
                .then(data => {{
                    if (data.status === 'success') {{
                        message.innerHTML = '<div style="color: #22c55e; font-weight: bold;">✅ ' + data.message + '</div>';
                        button.innerHTML = '✓ RESET CONCLUÍDO';
                        setTimeout(() => {{
                            window.location.href = '/import/historico/progress';
                        }}, 3000);
                    }} else {{
                        throw new Error(data.detail || 'Erro ao resetar');
                    }}
                }})
                .catch(error => {{
                    message.innerHTML = '<div style="color: #ef4444;">❌ ' + error.message + '</div>';
                    button.disabled = false;
                    button.innerHTML = 'CONFIRMAR RESET TOTAL';
                }});
            }}
        </script>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)

@app.get("/import/historico/progress", response_class=HTMLResponse)
async def import_historico_progress():
    """Página web com progresso visual da importação"""
    status = get_historico_status()

    html_content = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Progresso da Importação - Portabilidade</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background-color: #0f172a;
                color: #e2e8f0;
                margin: 0;
                padding: 20px;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
            }}
            .container {{
                background-color: #1e293b;
                border-radius: 16px;
                padding: 32px;
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
                max-width: 600px;
                width: 100%;
            }}
            h1 {{
                margin: 0 0 8px 0;
                font-size: 28px;
                color: #f8fafc;
                text-align: center;
            }}
            .subtitle {{
                text-align: center;
                color: #94a3b8;
                margin-bottom: 32px;
                font-size: 14px;
            }}
            .progress-container {{
                background-color: #334155;
                border-radius: 12px;
                height: 32px;
                overflow: hidden;
                margin-bottom: 24px;
                position: relative;
            }}
            .progress-bar {{
                height: 100%;
                background: linear-gradient(90deg, #3b82f6 0%, #2563eb 100%);
                border-radius: 12px;
                transition: width 0.5s ease;
                position: relative;
                overflow: hidden;
            }}
            .progress-bar::after {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                bottom: 0;
                right: 0;
                background: linear-gradient(
                    45deg,
                    transparent 25%,
                    rgba(255, 255, 255, 0.1) 25%,
                    rgba(255, 255, 255, 0.1) 50%,
                    transparent 50%,
                    transparent 75%,
                    rgba(255, 255, 255, 0.1) 75%,
                    rgba(255, 255, 255, 0.1)
                );
                background-size: 50px 50px;
                animation: progress-bar-stripes 1s linear infinite;
            }}
            @keyframes progress-bar-stripes {{
                0% {{ background-position: 0 0; }}
                100% {{ background-position: 50px 50px; }}
            }}
            .stats {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 16px;
                margin-bottom: 24px;
            }}
            .stat {{
                background-color: #334155;
                padding: 16px;
                border-radius: 8px;
                text-align: center;
            }}
            .stat-value {{
                font-size: 24px;
                font-weight: bold;
                color: #3b82f6;
                margin-bottom: 4px;
            }}
            .stat-label {{
                font-size: 12px;
                color: #94a3b8;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }}
            .status {{
                text-align: center;
                padding: 12px;
                border-radius: 8px;
                font-weight: 500;
                margin-bottom: 16px;
            }}
            .status.running {{
                background-color: rgba(34, 197, 94, 0.1);
                color: #22c55e;
                border: 1px solid rgba(34, 197, 94, 0.2);
            }}
            .status.completed {{
                background-color: rgba(59, 130, 246, 0.1);
                color: #3b82f6;
                border: 1px solid rgba(59, 130, 246, 0.2);
            }}
            .status.stopped {{
                background-color: rgba(239, 68, 68, 0.1);
                color: #ef4444;
                border: 1px solid rgba(239, 68, 68, 0.2);
            }}
            .refresh-info {{
                text-align: center;
                color: #64748b;
                font-size: 12px;
                margin-top: 16px;
            }}
            .progress-text {{
                position: absolute;
                width: 100%;
                text-align: center;
                line-height: 32px;
                color: #f8fafc;
                font-weight: 500;
                text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
                z-index: 1;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Importação de Histórico</h1>
            <div class="subtitle">51.618.684 registros de portabilidade</div>

            <div class="status {'running' if status['running'] else 'completed' if status['completed'] else 'stopped'}">
                {'🔄 Importação em andamento...' if status['running'] else '✅ Importação concluída!' if status['completed'] else '⏸️ Importação pausada'}
            </div>

            <div class="progress-container">
                <div class="progress-bar" style="width: {status['progress_percent']}%">
                    <div class="progress-text">{status['progress_percent']:.1f}%</div>
                </div>
            </div>

            <div class="stats">
                <div class="stat">
                    <div class="stat-value">{status['current_records']:,}</div>
                    <div class="stat-label">Registros Importados</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{status['total_expected']:,}</div>
                    <div class="stat-label">Total Esperado</div>
                </div>
                {'<div class="stat">' if status['running'] else ''}
                    {'<div class="stat-value">' + f"{status['speed']:,}" + '/s</div>' if status.get('speed', 0) > 0 else '<div class="stat-value">Calculando...</div>' if status['running'] else ''}
                    {'<div class="stat-label">Velocidade</div>' if status['running'] else ''}
                {'</div>' if status['running'] else ''}
                {'<div class="stat">' if status['running'] else ''}
                    {'<div class="stat-value">' + (str(timedelta(seconds=status['eta_seconds'])).split('.')[0] if status.get('eta_seconds', 0) > 0 else 'Calculando...') + '</div>' if status['running'] else ''}
                    {'<div class="stat-label">Tempo Restante</div>' if status['running'] else ''}
                {'</div>' if status['running'] else ''}
            </div>

            <div class="refresh-info">
                Página atualiza automaticamente a cada 5 segundos
            </div>

            <div style="text-align: center; margin-top: 20px;">
                <a href="/import/historico/reset-page" style="
                    color: #ef4444;
                    text-decoration: none;
                    font-size: 14px;
                    padding: 8px 16px;
                    border: 1px solid #ef4444;
                    border-radius: 6px;
                    display: inline-block;
                    transition: all 0.3s ease;
                " onmouseover="this.style.backgroundColor='rgba(239,68,68,0.1)'" onmouseout="this.style.backgroundColor='transparent'">
                    🗑️ Ir para página de Reset
                </a>
            </div>

            {f'''
            <div style="margin-top: 24px;">
                <button id="startImport" onclick="startImport()" style="
                    width: 100%;
                    padding: 16px;
                    background: linear-gradient(90deg, #3b82f6 0%, #2563eb 100%);
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-size: 16px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                " onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='translateY(0)'">
                    🚀 Iniciar Importação de 51M Registros
                </button>
                <div id="message" style="margin-top: 16px; text-align: center; font-size: 14px;"></div>
            </div>
            ''' if not status['running'] and not status['completed'] else ''}

        </div>

        {f'''
        <!-- SEÇÃO DE RESET SEPARADA -->
        <div style="
            margin-top: 40px;
            padding: 24px;
            background-color: rgba(239, 68, 68, 0.1);
            border: 2px solid rgba(239, 68, 68, 0.3);
            border-radius: 12px;
        ">
            <h2 style="
                color: #ef4444;
                margin: 0 0 12px 0;
                font-size: 20px;
                text-align: center;
            ">⚠️ Zona de Perigo</h2>

            <p style="
                color: #f87171;
                text-align: center;
                margin-bottom: 20px;
                font-size: 14px;
            ">
                Esta ação é irreversível e apagará TODOS os dados
            </p>

            <button id="resetImport" onclick="resetImport()" style="
                width: 100%;
                padding: 16px;
                background: #dc2626;
                color: white;
                border: 2px solid #b91c1c;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
            " onmouseover="this.style.background='#b91c1c'" onmouseout="this.style.background='#dc2626'">
                🗑️ RESETAR TUDO E COMEÇAR DO ZERO
            </button>

            <div id="resetMessage" style="margin-top: 16px; text-align: center; font-size: 14px;"></div>

            <ul style="
                color: #fca5a5;
                font-size: 12px;
                margin-top: 16px;
                padding-left: 20px;
            ">
                <li>Apaga {status['current_records']:,} registros do banco</li>
                <li>Remove todos os arquivos CSV</li>
                <li>Deleta todos os chunks temporários</li>
                <li>Para processos em execução</li>
            </ul>
        </div>
        ''' if not status['running'] else ''}

        <script>
            // Auto-refresh a cada 5 segundos
            setTimeout(() => {{
                location.reload();
            }}, 5000);

            // Função para iniciar importação
            async function startImport() {{
                const button = document.getElementById('startImport');
                const message = document.getElementById('message');

                button.disabled = true;
                button.style.opacity = '0.6';
                button.style.cursor = 'not-allowed';
                button.innerHTML = '⏳ Iniciando importação...';

                try {{
                    const response = await fetch('/import/historico', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }}
                    }});

                    if (response.ok) {{
                        const data = await response.json();
                        message.style.color = '#22c55e';
                        message.innerHTML = '✅ ' + data.message;
                        setTimeout(() => {{
                            location.reload();
                        }}, 2000);
                    }} else {{
                        const error = await response.json();
                        message.style.color = '#ef4444';
                        message.innerHTML = '❌ ' + (error.detail || 'Erro ao iniciar importação');
                        button.disabled = false;
                        button.style.opacity = '1';
                        button.style.cursor = 'pointer';
                        button.innerHTML = '🚀 Iniciar Importação de 51M Registros';
                    }}
                }} catch (error) {{
                    message.style.color = '#ef4444';
                    message.innerHTML = '❌ Erro de conexão: ' + error.message;
                    button.disabled = false;
                    button.style.opacity = '1';
                    button.style.cursor = 'pointer';
                    button.innerHTML = '🚀 Iniciar Importação de 51M Registros';
                }}
            }}

            // Função para resetar importação
            async function resetImport() {{
                const button = document.getElementById('resetImport');
                const message = document.getElementById('resetMessage');

                if (!confirm('⚠️ ATENÇÃO: Isso vai APAGAR todos os 10M+ registros importados e remover os arquivos.\\n\\nTem certeza que deseja resetar tudo?')) {{
                    return;
                }}

                button.disabled = true;
                button.style.opacity = '0.6';
                button.style.cursor = 'not-allowed';
                button.innerHTML = '⏳ Resetando...';

                try {{
                    const response = await fetch('/import/historico/reset', {{
                        method: 'DELETE',
                        headers: {{
                            'Content-Type': 'application/json'
                        }}
                    }});

                    if (response.ok) {{
                        const data = await response.json();
                        message.style.color = '#22c55e';
                        message.innerHTML = '✅ ' + data.message + '<br><small>' + data.actions.join('<br>') + '</small>';
                        setTimeout(() => {{
                            location.reload();
                        }}, 3000);
                    }} else {{
                        const error = await response.json();
                        message.style.color = '#ef4444';
                        message.innerHTML = '❌ ' + (error.detail || 'Erro ao resetar');
                        button.disabled = false;
                        button.style.opacity = '1';
                        button.style.cursor = 'pointer';
                        button.innerHTML = '🔄 Resetar Importação (Limpar Tudo)';
                    }}
                }} catch (error) {{
                    message.style.color = '#ef4444';
                    message.innerHTML = '❌ Erro de conexão: ' + error.message;
                    button.disabled = false;
                    button.style.opacity = '1';
                    button.style.cursor = 'pointer';
                    button.innerHTML = '🔄 Resetar Importação (Limpar Tudo)';
                }}
            }}

            // Atualizar via API também
            async function updateProgress() {{
                try {{
                    const response = await fetch('/import/historico/status');
                    const data = await response.json();

                    // Atualizar elementos se necessário
                    // (implementação futura com atualização sem reload)
                }} catch (error) {{
                    console.error('Erro ao atualizar:', error);
                }}
            }}
        </script>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=80)
