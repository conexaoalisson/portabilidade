#!/usr/bin/env python3
"""
Importador linha por linha - mínimo uso de memória
- Processa 1 registro por vez
- Commit a cada 100 registros
- Zero acumulação de memória
"""
import os
import psycopg2
import gc
import time

# Config
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('POSTGRES_DB', 'portabilidade'),
    'user': os.getenv('POSTGRES_USER', 'portabilidade'),
    'password': os.getenv('POSTGRES_PASSWORD', 'portabilidade123')
}

CSV_FILE = '/app/data/export_full_mysql.csv'
COMMIT_INTERVAL = 100  # Commit a cada 100 registros

print("=== IMPORTADOR LINHA POR LINHA ===\n")
print("Modo: Ultra economia de memória")
print(f"Commit a cada: {COMMIT_INTERVAL} registros\n")

# Conectar
conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor()

# SQL de inserção
insert_sql = """
INSERT INTO portabilidade_historico (
    spid_origem, flag_1, data_criacao, telefone, codigo_1,
    spid_destino, codigo_operadora, codigo_completo,
    flag_2, flag_3, status, flag_4, data_atualizacao,
    flag_5, data_nula_1, flag_6, flag_7, flag_8, data_nula_2
) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
ON CONFLICT DO NOTHING
"""

# Verificar quantos já foram importados
cursor.execute("SELECT COUNT(*) FROM portabilidade_historico")
skip_lines = cursor.fetchone()[0]
print(f"Registros existentes: {skip_lines:,}")

if not os.path.exists(CSV_FILE):
    print(f"Erro: Arquivo não encontrado: {CSV_FILE}")
    exit(1)

# Processar
success = 0
errors = 0
start_time = time.time()

with open(CSV_FILE, 'r', encoding='utf-8', errors='ignore') as f:
    # Pular linhas já processadas
    if skip_lines > 0:
        print(f"Pulando {skip_lines:,} linhas...")
        for _ in range(skip_lines):
            f.readline()

    print("\nIniciando importação...\n")

    for line_num, line in enumerate(f, skip_lines + 1):
        try:
            # Parse linha
            fields = line.strip().split(';')
            if len(fields) < 19:
                continue

            # Preparar dados
            data = (
                fields[0],  # spid_origem
                int(fields[1]) if fields[1] and fields[1].isdigit() else None,
                fields[2],  # data_criacao
                int(fields[3]) if fields[3] and fields[3].isdigit() and len(fields[3]) <= 15 else None,
                int(fields[4]) if fields[4] and fields[4].isdigit() else None,
                fields[5],  # spid_destino
                fields[6],  # codigo_operadora
                fields[7],  # codigo_completo
                int(fields[8]) if fields[8] and fields[8].isdigit() else None,
                int(fields[9]) if fields[9] and fields[9].isdigit() else None,
                fields[10], # status
                int(fields[11]) if fields[11] and fields[11].isdigit() else None,
                fields[12], # data_atualizacao
                int(fields[13]) if fields[13] and fields[13].isdigit() else None,
                None if fields[14] == '0000-00-00 00:00:00' else fields[14],
                int(fields[15]) if fields[15] and fields[15].isdigit() else None,
                int(fields[16]) if fields[16] and fields[16].isdigit() else None,
                int(fields[17]) if fields[17] and fields[17].isdigit() else None,
                None if fields[18] == '0000-00-00 00:00:00' else fields[18]
            )

            cursor.execute(insert_sql, data)
            success += 1

            # Commit periodicamente
            if success % COMMIT_INTERVAL == 0:
                conn.commit()

            # Status
            if success % 10000 == 0:
                elapsed = time.time() - start_time
                speed = success / elapsed if elapsed > 0 else 0
                print(f"Importados: {line_num:,} | Velocidade: {speed:.0f} reg/s")

            # Liberar memória
            if success % 1000 == 0:
                gc.collect()

        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"Erro linha {line_num}: {str(e)[:50]}")

# Commit final
conn.commit()
cursor.close()
conn.close()

print(f"\n=== CONCLUÍDO ===")
print(f"Sucesso: {success:,}")
print(f"Erros: {errors:,}")
print(f"Tempo: {(time.time() - start_time)/60:.1f} minutos")