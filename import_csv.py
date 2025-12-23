#!/usr/bin/env python3
"""
Importador do arquivo CSV completo de portabilidade
"""
import csv
import sys
from app.database import engine, SessionLocal
from app.models import Base, PortabilidadeHistorico

def criar_tabela():
    """Criar tabela portabilidade_historico"""
    print("[CSV] Criando tabela portabilidade_historico...")
    Base.metadata.create_all(bind=engine)
    print("[CSV] ✓ Tabela criada")

def limpar_tabela():
    """Limpar tabela existente"""
    session = SessionLocal()
    try:
        print("[CSV] Limpando tabela...")
        session.query(PortabilidadeHistorico).delete()
        session.commit()
        print("[CSV] ✓ Tabela limpa")
    except Exception as e:
        print(f"[CSV] Aviso: {e}")
        session.rollback()
    finally:
        session.close()

def importar_csv(arquivo_csv, limite=None):
    """Importar dados do CSV"""
    session = SessionLocal()

    try:
        print(f"[CSV] Importando dados de {arquivo_csv}...")

        with open(arquivo_csv, 'r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter=';')

            registros = []
            contador = 0

            for linha in reader:
                if len(linha) != 19:
                    print(f"[CSV] ⚠ Linha com {len(linha)} campos (esperado 19), pulando...")
                    continue

                registro = PortabilidadeHistorico(
                    spid_origem=linha[0],
                    flag_1=int(linha[1]) if linha[1].isdigit() else 0,
                    data_criacao=linha[2],
                    telefone=int(linha[3]) if linha[3].isdigit() else 0,
                    codigo_1=int(linha[4]) if linha[4].isdigit() else 0,
                    spid_destino=linha[5],
                    codigo_operadora=linha[6],
                    codigo_completo=linha[7],
                    flag_2=int(linha[8]) if linha[8].isdigit() else 0,
                    flag_3=int(linha[9]) if linha[9].isdigit() else 0,
                    status=linha[10],
                    flag_4=int(linha[11]) if linha[11].isdigit() else 0,
                    data_atualizacao=linha[12],
                    flag_5=int(linha[13]) if linha[13].isdigit() else 0,
                    data_nula_1=linha[14],
                    flag_6=int(linha[15]) if linha[15].isdigit() else 0,
                    flag_7=int(linha[16]) if linha[16].isdigit() else 0,
                    flag_8=int(linha[17]) if linha[17].isdigit() else 0,
                    data_nula_2=linha[18]
                )

                registros.append(registro)
                contador += 1

                # Commit em lotes de 10.000
                if len(registros) >= 10000:
                    session.bulk_save_objects(registros)
                    session.commit()
                    print(f"[CSV] Importados {contador:,} registros...")
                    registros = []

                # Limite de teste
                if limite and contador >= limite:
                    print(f"[CSV] Limite de {limite:,} registros atingido")
                    break

            # Commit final
            if registros:
                session.bulk_save_objects(registros)
                session.commit()

            print(f"[CSV] ✓ Total importado: {contador:,} registros")
            return contador

    except Exception as e:
        print(f"[CSV] ✗ ERRO: {e}")
        session.rollback()
        return 0
    finally:
        session.close()

def contar_registros():
    """Contar registros importados"""
    session = SessionLocal()
    try:
        total = session.query(PortabilidadeHistorico).count()
        print(f"[CSV] Total de registros na tabela: {total:,}")
        return total
    finally:
        session.close()

if __name__ == "__main__":
    modo_teste = "--test" in sys.argv

    print("="*60)
    print("IMPORTAÇÃO CSV - PORTABILIDADE HISTÓRICO")
    print("="*60)

    if modo_teste:
        print("\n*** MODO TESTE - Importando apenas 50.000 registros ***\n")

    # 1. Criar tabela
    criar_tabela()

    # 2. Limpar dados existentes
    limpar_tabela()

    # 3. Importar CSV
    arquivo = "dados_csv/amostra.csv" if modo_teste else "dados_csv/export_full_mysql.csv"
    limite = 50000 if modo_teste else None

    total = importar_csv(arquivo, limite)

    # 4. Contar registros
    contar_registros()

    print("\n" + "="*60)
    if total > 0:
        print("✓ IMPORTAÇÃO CONCLUÍDA COM SUCESSO!")
    else:
        print("✗ IMPORTAÇÃO FALHOU!")
    print("="*60)
