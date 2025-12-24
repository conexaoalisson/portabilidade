#!/usr/bin/env python3
"""
Importador com capacidade de resumir de onde parou
- Detecta chunks existentes
- Continua importação sem redividir arquivo
"""
import os
import sys
import time
import psycopg2
import gc
from datetime import datetime

# Configurações
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('POSTGRES_DB', 'portabilidade'),
    'user': os.getenv('POSTGRES_USER', 'portabilidade'),
    'password': os.getenv('POSTGRES_PASSWORD', 'portabilidade123')
}

TEMP_DIR = '/tmp/portabilidade_chunks'
CHUNK_SIZE = 1000000

# Cores
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
BLUE = '\033[0;34m'
BOLD = '\033[1m'
NC = '\033[0m'

def get_current_count(conn):
    """Obtém contagem atual de registros"""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM portabilidade_historico")
    count = cursor.fetchone()[0]
    cursor.close()
    return count

def get_processed_chunks(current_count):
    """Calcula quantos chunks já foram processados"""
    return current_count // CHUNK_SIZE

def import_chunk(conn, chunk_file, chunk_num):
    """Importa um chunk usando COPY com fallback para INSERT"""
    cursor = conn.cursor()

    print(f"\n{BOLD}Processando chunk {chunk_num}{NC}")
    print(f"Arquivo: {os.path.basename(chunk_file)}")

    try:
        # Criar tabela temporária
        cursor.execute("""
            CREATE TEMP TABLE IF NOT EXISTS staging_portabilidade (
                campo1 TEXT, campo2 TEXT, campo3 TEXT, campo4 TEXT, campo5 TEXT,
                campo6 TEXT, campo7 TEXT, campo8 TEXT, campo9 TEXT, campo10 TEXT,
                campo11 TEXT, campo12 TEXT, campo13 TEXT, campo14 TEXT, campo15 TEXT,
                campo16 TEXT, campo17 TEXT, campo18 TEXT, campo19 TEXT
            )
        """)

        # Limpar staging
        cursor.execute("TRUNCATE staging_portabilidade")

        # COPY para staging
        print(f"{BLUE}Importando com COPY...{NC}", end='', flush=True)
        with open(chunk_file, 'r', encoding='utf-8') as f:
            cursor.copy_expert(
                "COPY staging_portabilidade FROM STDIN WITH DELIMITER ';' CSV",
                f
            )

        # Inserir na tabela final
        cursor.execute("""
            INSERT INTO portabilidade_historico (
                spid_origem, flag_1, data_criacao, telefone, codigo_1,
                spid_destino, codigo_operadora, codigo_completo,
                flag_2, flag_3, status, flag_4, data_atualizacao,
                flag_5, data_nula_1, flag_6, flag_7, flag_8, data_nula_2
            )
            SELECT
                campo1::VARCHAR(10),
                NULLIF(campo2, '')::BIGINT,
                campo3::VARCHAR(50),
                CASE
                    WHEN campo4 ~ '^[0-9]+$' AND LENGTH(campo4) <= 15
                    THEN campo4::BIGINT
                    ELSE NULL
                END,
                NULLIF(campo5, '')::BIGINT,
                campo6::VARCHAR(10),
                campo7::VARCHAR(10),
                campo8::VARCHAR(10),
                NULLIF(campo9, '')::BIGINT,
                NULLIF(campo10, '')::BIGINT,
                campo11::VARCHAR(20),
                NULLIF(campo12, '')::BIGINT,
                campo13::VARCHAR(50),
                NULLIF(campo14, '')::BIGINT,
                CASE
                    WHEN campo15 = '0000-00-00 00:00:00' THEN NULL
                    ELSE campo15::VARCHAR(50)
                END,
                NULLIF(campo16, '')::BIGINT,
                NULLIF(campo17, '')::BIGINT,
                NULLIF(campo18, '')::BIGINT,
                CASE
                    WHEN campo19 = '0000-00-00 00:00:00' THEN NULL
                    ELSE campo19::VARCHAR(50)
                END
            FROM staging_portabilidade
        """)

        rows_inserted = cursor.rowcount
        conn.commit()

        # Limpar staging
        cursor.execute("TRUNCATE staging_portabilidade")
        conn.commit()

        print(f"\r{GREEN}✓ Chunk {chunk_num} importado: {rows_inserted:,} registros{NC}")

        # Deletar chunk processado
        os.remove(chunk_file)
        print(f"{YELLOW}  Chunk deletado para liberar espaço{NC}")

        # Forçar limpeza de memória
        gc.collect()

        return True, rows_inserted

    except Exception as e:
        conn.rollback()
        print(f"\r{RED}✗ Erro no chunk {chunk_num}: {str(e)}{NC}")
        return False, 0
    finally:
        cursor.close()

def main():
    print(f"{BOLD}╔════════════════════════════════════════════════════════════╗{NC}")
    print(f"{BOLD}║         IMPORTADOR RESUMÍVEL - PORTABILIDADE               ║{NC}")
    print(f"{BOLD}╚════════════════════════════════════════════════════════════╝{NC}\n")

    # Conectar ao banco
    conn = psycopg2.connect(**DB_CONFIG)

    # Verificar situação atual
    current_count = get_current_count(conn)
    processed_chunks = get_processed_chunks(current_count)

    print(f"{BLUE}Situação atual:{NC}")
    print(f"  Registros importados: {current_count:,}")
    print(f"  Chunks processados: {processed_chunks}")

    # Verificar chunks existentes
    if not os.path.exists(TEMP_DIR):
        print(f"\n{RED}✗ Diretório de chunks não encontrado: {TEMP_DIR}{NC}")
        return

    chunk_files = sorted([
        os.path.join(TEMP_DIR, f)
        for f in os.listdir(TEMP_DIR)
        if f.endswith('.csv')
    ])

    print(f"\n{GREEN}Chunks encontrados: {len(chunk_files)}{NC}")

    # Começar do próximo chunk
    start_chunk = processed_chunks + 1
    print(f"\n{YELLOW}Iniciando importação do chunk {start_chunk}{NC}\n")

    total_imported = 0

    # Processar chunks restantes
    for i, chunk_file in enumerate(chunk_files, 1):
        chunk_num = processed_chunks + i

        print(f"{BOLD}{'='*60}{NC}")
        print(f"{BOLD}Chunk {chunk_num}/{processed_chunks + len(chunk_files)}{NC}")
        print(f"{BOLD}{'='*60}{NC}")

        start_time = time.time()
        success, imported = import_chunk(conn, chunk_file, chunk_num)
        elapsed = time.time() - start_time

        if success:
            total_imported += imported
            speed = imported / elapsed if elapsed > 0 else 0
            print(f"{BLUE}  Tempo: {elapsed:.1f}s | Velocidade: {speed:,.0f} registros/s{NC}")

            # VACUUM a cada 10 chunks
            if chunk_num % 10 == 0:
                print(f"\n{YELLOW}Otimizando banco de dados...{NC}")
                cursor = conn.cursor()
                cursor.execute("VACUUM ANALYZE portabilidade_historico")
                conn.commit()
                cursor.close()
        else:
            print(f"{RED}  Pulando para próximo chunk...{NC}")

    conn.close()

    # Resumo final
    print(f"\n{BOLD}╔════════════════════════════════════════════════════════════╗{NC}")
    print(f"{BOLD}║                    IMPORTAÇÃO CONCLUÍDA                    ║{NC}")
    print(f"{BOLD}╚════════════════════════════════════════════════════════════╝{NC}")
    print(f"\n{GREEN}✓ Registros importados nesta sessão: {total_imported:,}{NC}")

if __name__ == "__main__":
    main()