#!/usr/bin/env python3
"""
Conversor de SQL MySQL para PostgreSQL
Converte os arquivos SQL baixados do servidor para formato PostgreSQL
"""

import os
import re

def convert_mysql_to_postgres(mysql_file, postgres_file):
    """Converte arquivo SQL de MySQL para PostgreSQL"""

    print(f"Convertendo {mysql_file} → {postgres_file}...")

    with open(mysql_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Remover backticks
    content = content.replace('`', '')

    # 2. Remover ENGINE, CHARSET, COLLATE
    content = content.replace(' ENGINE=InnoDB', '')
    content = content.replace(' DEFAULT CHARSET=utf8mb4', '')
    content = content.replace(' COLLATE=utf8mb4_0900_ai_ci', '')
    content = content.replace(' COLLATE utf8mb4_0900_ai_ci', '')

    # 3. Remover caracteres \r
    content = content.replace('\r', '')

    # 4. Filtrar linhas com comandos MySQL
    lines_to_remove_patterns = [
        r'^SET SQL_MODE',
        r'^START TRANSACTION',
        r'^SET time_zone',
        r'^/\*!40101',
        r'^/\*!40000',
        r'^/\*!50003',
        r'^SET @OLD_',
        r'^SET @@',
        r'^-- phpMyAdmin',
        r'^-- version',
        r'^-- https://www',
        r'^-- Host:',
        r'^-- Tempo de',
        r'^-- Versão do',
        r'^-- Banco de dados:',
    ]

    lines = content.split('\n')
    filtered_lines = []
    skip_create = False

    for line in lines:
        # Pular linhas de configuração MySQL
        should_skip = False
        for pattern in lines_to_remove_patterns:
            if re.match(pattern, line.strip()):
                should_skip = True
                break

        if should_skip:
            continue

        # Detectar e pular CREATE TABLE (models do SQLAlchemy já criam)
        if re.match(r'^CREATE TABLE\s+', line.strip()):
            skip_create = True
            continue

        # Detectar fim do CREATE TABLE
        if skip_create:
            # Fim do CREATE TABLE quando encontrar ) seguido de ;
            if re.match(r'^\)\s*;?\s*$', line.strip()):
                skip_create = False
            continue

        # Pular linhas vazias consecutivas
        if line.strip() == '' and filtered_lines and filtered_lines[-1].strip() == '':
            continue

        filtered_lines.append(line)

    # 5. Remover COMMIT no final
    content = '\n'.join(filtered_lines)
    content = content.replace('COMMIT;', '')

    # 6. Limpar espaços no final
    content = content.strip() + '\n'

    # Salvar arquivo convertido
    with open(postgres_file, 'w', encoding='utf-8') as f:
        f.write(content)

    # Estatísticas
    original_lines = len(open(mysql_file, 'r').readlines())
    converted_lines = len(open(postgres_file, 'r').readlines())

    print(f"  ✓ Convertido: {original_lines} → {converted_lines} linhas")
    print(f"  ✓ Removidas: {original_lines - converted_lines} linhas")

def main():
    """Converte todos os arquivos SQL"""

    input_dir = "dados_portabilidade"
    output_dir = "sql_postgres"

    # Criar diretório de saída
    os.makedirs(output_dir, exist_ok=True)

    # Arquivos para converter
    files = [
        "operadoras_rn1.sql",
        "operadoras_stfc.sql",
        "faixa_operadora.sql"
    ]

    print("="*60)
    print("CONVERSOR MySQL → PostgreSQL")
    print("="*60)
    print()

    for filename in files:
        mysql_file = os.path.join(input_dir, filename)
        postgres_file = os.path.join(output_dir, filename)

        if os.path.exists(mysql_file):
            convert_mysql_to_postgres(mysql_file, postgres_file)
        else:
            print(f"⚠ Arquivo não encontrado: {mysql_file}")

    print()
    print("="*60)
    print("✓ CONVERSÃO CONCLUÍDA")
    print("="*60)
    print()
    print(f"Arquivos convertidos salvos em: {output_dir}/")
    print()
    print("Próximos passos:")
    print("1. git add sql_postgres/")
    print("2. git commit -m 'Adiciona arquivos SQL convertidos para PostgreSQL'")
    print("3. git push")

if __name__ == "__main__":
    main()
