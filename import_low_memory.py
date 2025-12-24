#!/usr/bin/env python3
"""
Importador otimizado para baixo uso de memória
- Processa linha por linha sem carregar chunk inteiro
- Usa batch de apenas 1000 registros por vez
- Libera memória agressivamente
"""
import os
import sys
import psycopg2
import gc
from io import StringIO

# Configurações
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('POSTGRES_DB', 'portabilidade'),
    'user': os.getenv('POSTGRES_USER', 'portabilidade'),
    'password': os.getenv('POSTGRES_PASSWORD', 'portabilidade123')
}

CSV_FILE = '/app/data/export_full_mysql.csv'
BATCH_SIZE = 1000  # Apenas 1000 registros por vez na memória

# Cores
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
BLUE = '\033[0;34m'
NC = '\033[0m'

def get_current_count(conn):
    """Obtém contagem atual"""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM portabilidade_historico")
    count = cursor.fetchone()[0]
    cursor.close()
    return count

def process_batch(conn, batch):
    """Processa um pequeno batch de registros"""
    if not batch:
        return 0

    cursor = conn.cursor()

    # Criar buffer temporário
    buffer = StringIO()
    for line in batch:
        buffer.write(line)

    buffer.seek(0)

    try:
        # Criar tabela temporária
        cursor.execute("""
            CREATE TEMP TABLE IF NOT EXISTS temp_import (
                campo1 TEXT, campo2 TEXT, campo3 TEXT, campo4 TEXT, campo5 TEXT,
                campo6 TEXT, campo7 TEXT, campo8 TEXT, campo9 TEXT, campo10 TEXT,
                campo11 TEXT, campo12 TEXT, campo13 TEXT, campo14 TEXT, campo15 TEXT,
                campo16 TEXT, campo17 TEXT, campo18 TEXT, campo19 TEXT
            )
        """)

        # Limpar temp
        cursor.execute("TRUNCATE temp_import")

        # COPY batch pequeno
        cursor.copy_expert(
            "COPY temp_import FROM STDIN WITH DELIMITER ';' CSV",
            buffer
        )

        # Inserir com tratamento
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
                CASE WHEN campo4 ~ '^[0-9]+$' AND LENGTH(campo4) <= 15
                     THEN campo4::BIGINT ELSE NULL END,
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
                CASE WHEN campo15 = '0000-00-00 00:00:00' THEN NULL
                     ELSE campo15::VARCHAR(50) END,
                NULLIF(campo16, '')::BIGINT,
                NULLIF(campo17, '')::BIGINT,
                NULLIF(campo18, '')::BIGINT,
                CASE WHEN campo19 = '0000-00-00 00:00:00' THEN NULL
                     ELSE campo19::VARCHAR(50) END
            FROM temp_import
            ON CONFLICT DO NOTHING
        """)

        inserted = cursor.rowcount
        conn.commit()

        # Limpar temp
        cursor.execute("DROP TABLE IF EXISTS temp_import")
        conn.commit()

        return inserted

    except Exception as e:
        conn.rollback()
        print(f"{RED}Erro no batch: {str(e)[:50]}...{NC}")
        return 0

    finally:
        cursor.close()
        buffer.close()
        del buffer
        del batch
        gc.collect()

def main():
    print(f"{GREEN}=== IMPORTADOR LOW MEMORY ==={NC}\n")

    # Conectar
    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_session(autocommit=False)

    # Verificar situação
    start_count = get_current_count(conn)
    print(f"Registros atuais: {start_count:,}")

    if not os.path.exists(CSV_FILE):
        print(f"{RED}Arquivo não encontrado: {CSV_FILE}{NC}")
        return

    # Processar arquivo
    batch = []
    total_processed = 0
    lines_read = 0

    print(f"\n{YELLOW}Processando arquivo...{NC}")
    print(f"Batch size: {BATCH_SIZE} registros\n")

    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        # Pular linhas já importadas
        print(f"{BLUE}Pulando {start_count:,} linhas já importadas...{NC}")
        for _ in range(start_count):
            f.readline()
            lines_read += 1
            if lines_read % 1000000 == 0:
                print(f"  Puladas {lines_read:,} linhas...")

        print(f"{GREEN}Iniciando importação...{NC}\n")

        # Processar restante
        for line in f:
            batch.append(line)

            if len(batch) >= BATCH_SIZE:
                inserted = process_batch(conn, batch)
                total_processed += inserted
                batch = []  # Limpar batch

                # Status
                if total_processed % 10000 == 0:
                    current = start_count + total_processed
                    print(f"Importados: {current:,} total ({inserted} no último batch)")

                # VACUUM a cada 100k registros
                if total_processed % 100000 == 0:
                    print(f"{YELLOW}Executando VACUUM...{NC}")
                    cursor = conn.cursor()
                    cursor.execute("VACUUM portabilidade_historico")
                    cursor.close()
                    gc.collect()

        # Processar último batch
        if batch:
            inserted = process_batch(conn, batch)
            total_processed += inserted

    conn.close()

    print(f"\n{GREEN}=== IMPORTAÇÃO CONCLUÍDA ==={NC}")
    print(f"Registros importados: {total_processed:,}")
    print(f"Total no banco: {start_count + total_processed:,}")

if __name__ == "__main__":
    main()