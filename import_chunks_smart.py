#!/usr/bin/env python3
"""
Importador inteligente de histórico de portabilidade
- Divide arquivo em chunks de 1M registros
- Usa COPY para velocidade máxima
- Fallback para INSERT linha por linha em caso de erro
- Progresso visual em tempo real
- Otimizado para liberar memória após cada chunk
"""
import os
import sys
import time
import psycopg2
from psycopg2 import sql
from datetime import datetime
import tempfile
import subprocess
from io import StringIO
import gc  # Garbage collector para liberar memória

# Configurações
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('POSTGRES_DB', 'portabilidade'),
    'user': os.getenv('POSTGRES_USER', 'portabilidade'),
    'password': os.getenv('POSTGRES_PASSWORD', 'portabilidade123')
}

INPUT_FILE = '/tmp/export_full_mysql.csv'
CHUNK_SIZE = 1000000  # 1 milhão de linhas por chunk
TEMP_DIR = '/tmp/portabilidade_chunks'

# Cores para output
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
BLUE = '\033[0;34m'
BOLD = '\033[1m'
NC = '\033[0m'  # No Color

def print_progress_bar(current, total, prefix='', suffix='', decimals=1, length=50, fill='█'):
    """Barra de progresso visual"""
    percent = ("{0:." + str(decimals) + "f}").format(100 * (current / float(total)))
    filled_length = int(length * current // total)
    bar = fill * filled_length + '░' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end='', flush=True)

def count_lines(filename):
    """Conta linhas do arquivo rapidamente"""
    print(f"{YELLOW}Contando linhas do arquivo...{NC}")
    result = subprocess.run(['wc', '-l', filename], capture_output=True, text=True)
    return int(result.stdout.split()[0])

def split_file_into_chunks(filename, chunk_size):
    """Divide arquivo em chunks menores"""
    os.makedirs(TEMP_DIR, exist_ok=True)

    print(f"\n{BOLD}1. DIVIDINDO ARQUIVO EM CHUNKS{NC}")
    print(f"{YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")

    total_lines = count_lines(filename)
    total_chunks = (total_lines // chunk_size) + (1 if total_lines % chunk_size else 0)

    print(f"Total de linhas: {total_lines:,}")
    print(f"Linhas por chunk: {chunk_size:,}")
    print(f"Total de chunks: {total_chunks}\n")

    chunk_files = []
    current_chunk = 0
    current_lines = 0
    chunk_file = None
    chunk_writer = None

    with open(filename, 'r', encoding='utf-8') as infile:
        for line_num, line in enumerate(infile, 1):
            # Novo chunk
            if current_lines == 0:
                if chunk_file:
                    chunk_file.close()

                current_chunk += 1
                chunk_filename = os.path.join(TEMP_DIR, f'chunk_{current_chunk:04d}.csv')
                chunk_files.append(chunk_filename)
                chunk_file = open(chunk_filename, 'w', encoding='utf-8')

            chunk_file.write(line)
            current_lines += 1

            # Progresso
            if line_num % 100000 == 0:
                print_progress_bar(line_num, total_lines,
                                 prefix=f'Dividindo',
                                 suffix=f'Chunk {current_chunk}/{total_chunks}')

            # Fechar chunk atual
            if current_lines >= chunk_size:
                current_lines = 0

    if chunk_file:
        chunk_file.close()

    print(f"\n{GREEN}✓ Arquivo dividido em {len(chunk_files)} chunks{NC}\n")
    return chunk_files

def create_temp_table(conn):
    """Cria tabela temporária para staging"""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TEMP TABLE IF NOT EXISTS staging_portabilidade (
            campo1 TEXT,
            campo2 TEXT,
            campo3 TEXT,
            campo4 TEXT,
            campo5 TEXT,
            campo6 TEXT,
            campo7 TEXT,
            campo8 TEXT,
            campo9 TEXT,
            campo10 TEXT,
            campo11 TEXT,
            campo12 TEXT,
            campo13 TEXT,
            campo14 TEXT,
            campo15 TEXT,
            campo16 TEXT,
            campo17 TEXT,
            campo18 TEXT,
            campo19 TEXT
        )
    """)
    conn.commit()
    cursor.close()

def import_chunk_with_copy(conn, chunk_file, chunk_num, total_chunks):
    """Tenta importar chunk usando COPY (mais rápido)"""
    cursor = conn.cursor()

    try:
        # Limpar staging
        cursor.execute("TRUNCATE staging_portabilidade")

        # COPY para staging
        print(f"{BLUE}Importando com COPY...{NC}", end='', flush=True)
        with open(chunk_file, 'r', encoding='utf-8') as f:
            cursor.copy_expert(
                "COPY staging_portabilidade FROM STDIN WITH DELIMITER ';' CSV",
                f
            )

        # Inserir na tabela final com tratamento
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

        # Limpar staging após inserção
        cursor.execute("TRUNCATE staging_portabilidade")
        conn.commit()

        print(f"\r{GREEN}✓ COPY bem-sucedido: {rows_inserted:,} registros{NC}")
        return True, rows_inserted, 0

    except Exception as e:
        conn.rollback()
        print(f"\r{RED}✗ COPY falhou: {str(e)[:50]}...{NC}")
        return False, 0, 0
    finally:
        cursor.close()

def import_chunk_with_insert(conn, chunk_file, chunk_num, total_chunks):
    """Importa chunk linha por linha (mais lento mas resiliente)"""
    cursor = conn.cursor()

    print(f"{YELLOW}Modo INSERT linha por linha...{NC}")

    insert_sql = """
        INSERT INTO portabilidade_historico (
            spid_origem, flag_1, data_criacao, telefone, codigo_1,
            spid_destino, codigo_operadora, codigo_completo,
            flag_2, flag_3, status, flag_4, data_atualizacao,
            flag_5, data_nula_1, flag_6, flag_7, flag_8, data_nula_2
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
    """

    total_lines = sum(1 for line in open(chunk_file, 'r', encoding='utf-8'))
    success_count = 0
    error_count = 0

    with open(chunk_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                # Parse linha
                fields = line.strip().split(';')
                if len(fields) < 19:
                    error_count += 1
                    continue

                # Preparar dados
                data = (
                    fields[0],                               # spid_origem
                    int(fields[1]) if fields[1] else None,   # flag_1
                    fields[2],                               # data_criacao
                    int(fields[3]) if fields[3] and fields[3].isdigit() else None,  # telefone
                    int(fields[4]) if fields[4] else None,   # codigo_1
                    fields[5],                               # spid_destino
                    fields[6],                               # codigo_operadora
                    fields[7],                               # codigo_completo
                    int(fields[8]) if fields[8] else None,   # flag_2
                    int(fields[9]) if fields[9] else None,   # flag_3
                    fields[10],                              # status
                    int(fields[11]) if fields[11] else None, # flag_4
                    fields[12],                              # data_atualizacao
                    int(fields[13]) if fields[13] else None, # flag_5
                    None if fields[14] == '0000-00-00 00:00:00' else fields[14],  # data_nula_1
                    int(fields[15]) if fields[15] else None, # flag_6
                    int(fields[16]) if fields[16] else None, # flag_7
                    int(fields[17]) if fields[17] else None, # flag_8
                    None if fields[18] == '0000-00-00 00:00:00' else fields[18]   # data_nula_2
                )

                cursor.execute(insert_sql, data)
                success_count += 1

                # Commit a cada 10k registros
                if success_count % 10000 == 0:
                    conn.commit()

            except Exception as e:
                error_count += 1
                if error_count <= 5:  # Mostrar apenas primeiros 5 erros
                    print(f"{RED}  Erro linha {line_num}: {str(e)[:50]}...{NC}")

            # Progresso
            if line_num % 1000 == 0:
                print_progress_bar(line_num, total_lines,
                                 prefix='INSERT',
                                 suffix=f'OK: {success_count:,} | Erros: {error_count:,}')

    conn.commit()
    cursor.close()

    print(f"\n{GREEN}✓ INSERT concluído: {success_count:,} OK, {error_count:,} erros{NC}")
    return True, success_count, error_count

def import_all_chunks(chunk_files):
    """Importa todos os chunks"""
    print(f"\n{BOLD}2. IMPORTANDO CHUNKS PARA O BANCO{NC}")
    print(f"{YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")

    conn = psycopg2.connect(**DB_CONFIG)
    create_temp_table(conn)

    total_success = 0
    total_errors = 0

    for i, chunk_file in enumerate(chunk_files, 1):
        chunk_size = os.path.getsize(chunk_file) / 1024 / 1024  # MB
        print(f"\n{BOLD}Chunk {i}/{len(chunk_files)}{NC} ({chunk_size:.1f} MB)")
        print("─" * 60)

        start_time = time.time()

        # Tentar COPY primeiro
        success, imported, errors = import_chunk_with_copy(conn, chunk_file, i, len(chunk_files))

        # Se COPY falhar, usar INSERT
        if not success:
            success, imported, errors = import_chunk_with_insert(conn, chunk_file, i, len(chunk_files))

        elapsed = time.time() - start_time
        speed = imported / elapsed if elapsed > 0 else 0

        print(f"Tempo: {elapsed:.1f}s | Velocidade: {speed:,.0f} registros/s")

        total_success += imported
        total_errors += errors

        # Limpar arquivo do chunk após processamento
        os.remove(chunk_file)

        # Forçar limpeza de memória
        gc.collect()

        # Executar VACUUM ANALYZE a cada 10 chunks para otimizar banco
        if i % 10 == 0:
            print(f"\n{YELLOW}Otimizando banco de dados...{NC}")
            cursor = conn.cursor()
            cursor.execute("VACUUM ANALYZE portabilidade_historico")
            conn.commit()
            cursor.close()

    conn.close()

    # Limpar diretório temporário
    print(f"\n{YELLOW}Limpando diretório temporário...{NC}")
    if os.path.exists(TEMP_DIR):
        os.rmdir(TEMP_DIR)

    return total_success, total_errors

def main():
    print(f"{BOLD}╔════════════════════════════════════════════════════════════╗{NC}")
    print(f"{BOLD}║         IMPORTADOR INTELIGENTE DE PORTABILIDADE            ║{NC}")
    print(f"{BOLD}╚════════════════════════════════════════════════════════════╝{NC}")

    if not os.path.exists(INPUT_FILE):
        print(f"{RED}✗ Arquivo não encontrado: {INPUT_FILE}{NC}")
        return

    file_size = os.path.getsize(INPUT_FILE) / 1024 / 1024 / 1024  # GB
    print(f"\nArquivo: {INPUT_FILE}")
    print(f"Tamanho: {file_size:.1f} GB")
    print(f"Chunk size: {CHUNK_SIZE:,} linhas")

    start_total = time.time()

    try:
        # Dividir arquivo
        chunk_files = split_file_into_chunks(INPUT_FILE, CHUNK_SIZE)

        # Importar chunks
        total_success, total_errors = import_all_chunks(chunk_files)

        # Resumo final
        elapsed_total = time.time() - start_total
        print(f"\n{BOLD}╔════════════════════════════════════════════════════════════╗{NC}")
        print(f"{BOLD}║                    IMPORTAÇÃO CONCLUÍDA                    ║{NC}")
        print(f"{BOLD}╚════════════════════════════════════════════════════════════╝{NC}")
        print(f"\n{GREEN}✓ Registros importados: {total_success:,}{NC}")
        if total_errors > 0:
            print(f"{RED}✗ Registros com erro: {total_errors:,}{NC}")
        print(f"\nTempo total: {elapsed_total/60:.1f} minutos")
        print(f"Velocidade média: {total_success/elapsed_total:,.0f} registros/s")

    except KeyboardInterrupt:
        print(f"\n\n{RED}✗ Importação interrompida pelo usuário{NC}")
    except Exception as e:
        print(f"\n\n{RED}✗ Erro fatal: {e}{NC}")

if __name__ == "__main__":
    main()