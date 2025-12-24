#!/usr/bin/env python3
"""
Monitor em tempo real da importação
Mostra progresso, velocidade e estimativas
"""
import psycopg2
import time
import os
import sys
from datetime import datetime, timedelta

# Configurações
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('POSTGRES_DB', 'portabilidade'),
    'user': os.getenv('POSTGRES_USER', 'portabilidade'),
    'password': os.getenv('POSTGRES_PASSWORD', 'portabilidade123')
}

# Cores
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
BOLD = '\033[1m'
NC = '\033[0m'

def clear_screen():
    os.system('clear' if os.name == 'posix' else 'cls')

def format_time(seconds):
    """Formata segundos em tempo legível"""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}min"
    else:
        return f"{seconds/3600:.1f}h"

def monitor_import():
    """Monitora importação em tempo real"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # Total esperado
    TOTAL_EXPECTED = 51618684

    start_time = time.time()
    last_count = 0
    samples = []  # Para calcular média móvel

    print(f"{BOLD}╔════════════════════════════════════════════════════════════╗{NC}")
    print(f"{BOLD}║           MONITOR DE IMPORTAÇÃO EM TEMPO REAL              ║{NC}")
    print(f"{BOLD}╚════════════════════════════════════════════════════════════╝{NC}")

    try:
        while True:
            # Contar registros atuais
            cursor.execute("SELECT COUNT(*) FROM portabilidade_historico")
            current_count = cursor.fetchone()[0]

            # Calcular métricas
            elapsed = time.time() - start_time
            imported_now = current_count - last_count

            # Adicionar amostra para média móvel
            if imported_now > 0:
                samples.append(imported_now)
                if len(samples) > 10:  # Manter últimas 10 amostras
                    samples.pop(0)

            # Velocidade instantânea e média
            speed_now = imported_now / 1.0  # Por segundo
            speed_avg = sum(samples) / len(samples) if samples else 0

            # Progresso
            progress = (current_count / TOTAL_EXPECTED) * 100

            # Estimativa de tempo restante
            if speed_avg > 0:
                remaining = TOTAL_EXPECTED - current_count
                eta_seconds = remaining / speed_avg
                eta_time = datetime.now() + timedelta(seconds=eta_seconds)
            else:
                eta_time = None

            # Limpar tela e mostrar dados
            clear_screen()
            print(f"{BOLD}╔════════════════════════════════════════════════════════════╗{NC}")
            print(f"{BOLD}║           MONITOR DE IMPORTAÇÃO EM TEMPO REAL              ║{NC}")
            print(f"{BOLD}╚════════════════════════════════════════════════════════════╝{NC}")
            print()

            # Progresso
            print(f"{BLUE}PROGRESSO:{NC}")
            bar_length = 50
            filled = int(bar_length * progress / 100)
            bar = '█' * filled + '░' * (bar_length - filled)
            print(f"[{bar}] {progress:.1f}%")
            print(f"Importados: {current_count:,} / {TOTAL_EXPECTED:,}")
            print()

            # Velocidade
            print(f"{YELLOW}VELOCIDADE:{NC}")
            print(f"Atual:      {speed_now:>10,.0f} registros/s")
            print(f"Média (10s): {speed_avg:>10,.0f} registros/s")
            print()

            # Tempo
            print(f"{GREEN}TEMPO:{NC}")
            print(f"Decorrido:  {format_time(elapsed)}")
            if eta_time:
                remaining_time = (eta_time - datetime.now()).total_seconds()
                print(f"Restante:   {format_time(remaining_time)}")
                print(f"Conclusão:  {eta_time.strftime('%H:%M:%S')}")
            print()

            # Estatísticas do banco
            cursor.execute("""
                SELECT
                    pg_size_pretty(pg_relation_size('portabilidade_historico')) as table_size,
                    pg_size_pretty(pg_total_relation_size('portabilidade_historico')) as total_size
            """)
            sizes = cursor.fetchone()
            print(f"{BOLD}BANCO DE DADOS:{NC}")
            print(f"Tamanho tabela: {sizes[0]}")
            print(f"Tamanho total:  {sizes[1]}")

            # Verificar se concluído
            if current_count >= TOTAL_EXPECTED:
                print(f"\n{GREEN}✓ IMPORTAÇÃO CONCLUÍDA!{NC}")
                break

            last_count = current_count
            time.sleep(1)  # Atualizar a cada segundo

    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}Monitor interrompido{NC}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    monitor_import()