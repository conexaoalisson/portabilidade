#!/usr/bin/env python3
"""
Monitor de importação com progresso em tempo real
"""
import time
import sys
from sqlalchemy import create_engine, text
from database import DATABASE_URL


def draw_progress_bar(current, total, width=50):
    """Desenha barra de progresso"""
    percent = int((current / total) * 100) if total > 0 else 0
    filled = int((width * current) / total) if total > 0 else 0

    bar = '█' * filled + '░' * (width - filled)
    sys.stdout.write(f'\r[{bar}] {percent:3d}% ({current:,}/{total:,})')
    sys.stdout.flush()


def monitor_import():
    """Monitora importação em tempo real"""
    engine = create_engine(DATABASE_URL)

    tables = [
        ('operadoras_rn1', 312),      # Estimativas
        ('operadoras_stfc', 2439),
        ('faixa_operadora', 234765)
    ]

    print("\n📊 MONITORAMENTO DE IMPORTAÇÃO EM TEMPO REAL\n")

    for table_name, estimated_total in tables:
        print(f"\n{table_name}:")

        last_count = 0
        no_change_count = 0

        while True:
            try:
                with engine.connect() as conn:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    current_count = result.scalar()

                draw_progress_bar(current_count, estimated_total)

                # Se não houver mudança por 5 verificações, considerar completo
                if current_count == last_count:
                    no_change_count += 1
                    if no_change_count > 5:
                        print(f" ✓ Completo!")
                        break
                else:
                    no_change_count = 0

                last_count = current_count
                time.sleep(0.5)

            except Exception as e:
                print(f"\n❌ Erro ao monitorar {table_name}: {e}")
                break

    # Resumo final
    print("\n\n📈 RESUMO FINAL:")
    print("─" * 40)

    total_records = 0
    with engine.connect() as conn:
        for table_name, _ in tables:
            try:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                count = result.scalar()
                print(f"{table_name:20} {count:>10,} registros")
                total_records += count
            except:
                print(f"{table_name:20} {'Erro':>10}")

    print("─" * 40)
    print(f"{'TOTAL':20} {total_records:>10,} registros")
    print("\n✅ Monitoramento concluído!\n")


if __name__ == "__main__":
    monitor_import()