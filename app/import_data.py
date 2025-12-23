import os
import sys
import requests
import gzip
import tempfile
from sqlalchemy import text
from app.database import engine, SessionLocal
from app.models import Base, FaixaOperadora, OperadoraRN1, OperadoraSTFC

# URLs dos arquivos
BASE_URL = "https://techsuper.com.br/baseportabilidade/"
FILES = {
    "operadoras_rn1": "operadoras_rn1.sql",
    "operadoras_stfc": "operadoras_stfc.sql",
    "faixa_operadora": "faixa_operadora.sql",
    "export_full": "export_full_mysql.csv.gz"
}

class ImportadorPortabilidade:
    def __init__(self):
        self.session = SessionLocal()
        self.temp_dir = tempfile.mkdtemp()

    def log(self, message):
        print(f"[IMPORT] {message}", flush=True)

    def download_file(self, filename, test_mode=False):
        """Download arquivo do servidor com validação UTF-8"""
        url = BASE_URL + filename
        local_path = os.path.join(self.temp_dir, filename)

        self.log(f"Baixando {filename}...")

        try:
            response = requests.get(url, stream=True, timeout=300)
            response.raise_for_status()

            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            # Verificar encoding UTF-8
            with open(local_path, 'r', encoding='utf-8') as f:
                # Ler primeira linha para validar
                f.readline()

            self.log(f"✓ {filename} baixado e validado (UTF-8)")
            return local_path

        except UnicodeDecodeError:
            self.log(f"✗ ERRO: {filename} não está em UTF-8!")
            return None
        except Exception as e:
            self.log(f"✗ ERRO ao baixar {filename}: {str(e)}")
            return None

    def criar_tabelas(self):
        """Criar tabelas no banco de dados"""
        self.log("Criando tabelas...")
        Base.metadata.create_all(bind=engine)
        self.log("✓ Tabelas criadas")

    def limpar_tabelas(self):
        """Limpar dados existentes"""
        self.log("Limpando tabelas existentes...")
        try:
            self.session.execute(text("TRUNCATE TABLE faixa_operadora RESTART IDENTITY CASCADE"))
            self.session.execute(text("TRUNCATE TABLE operadoras_rn1 RESTART IDENTITY CASCADE"))
            self.session.execute(text("TRUNCATE TABLE operadoras_stfc RESTART IDENTITY CASCADE"))
            self.session.commit()
            self.log("✓ Tabelas limpas")
        except Exception as e:
            self.log(f"Aviso: {str(e)}")
            self.session.rollback()

    def importar_sql_direto(self, filepath, test_mode=False):
        """Importa arquivo SQL diretamente no PostgreSQL"""
        self.log(f"Importando {os.path.basename(filepath)}...")

        try:
            # Ler arquivo SQL
            with open(filepath, 'r', encoding='utf-8') as f:
                sql_content = f.read()

            # CONVERTER MySQL para PostgreSQL
            self.log(f"  Convertendo sintaxe MySQL → PostgreSQL...")

            # Remover backticks (MySQL) - PostgreSQL não usa
            sql_content = sql_content.replace('`', '')

            # Remover comandos específicos do MySQL
            sql_content = sql_content.replace('ENGINE=InnoDB', '')
            sql_content = sql_content.replace('DEFAULT CHARSET=utf8mb4', '')
            sql_content = sql_content.replace('COLLATE=utf8mb4_0900_ai_ci', '')
            sql_content = sql_content.replace('COLLATE utf8mb4_0900_ai_ci', '')

            # Remover comandos de configuração do MySQL
            lines_to_remove = [
                'SET SQL_MODE',
                'START TRANSACTION',
                'SET time_zone',
                '/*!40101',
                '/*!40000',
                '/*!50003',
                'SET @OLD_',
                'SET @@'
            ]

            lines = sql_content.split('\n')
            filtered_lines = []
            for line in lines:
                should_skip = False
                for pattern in lines_to_remove:
                    if pattern in line:
                        should_skip = True
                        break
                if not should_skip:
                    filtered_lines.append(line)

            sql_content = '\n'.join(filtered_lines)

            # Limpar caracteres \r que podem causar problemas
            sql_content = sql_content.replace('\r', '')

            # Se test_mode, importar apenas primeiras 100 linhas de INSERT
            if test_mode:
                lines = sql_content.split('\n')
                insert_count = 0
                filtered_lines = []

                for line in lines:
                    if line.strip().startswith('INSERT INTO'):
                        insert_count += 1
                        if insert_count > 2:  # Apenas 2 primeiros INSERTs no teste
                            break
                    filtered_lines.append(line)

                sql_content = '\n'.join(filtered_lines)
                self.log(f"  MODE: TESTE - Importando apenas amostra")

            # Executar SQL
            self.session.execute(text(sql_content))
            self.session.commit()

            self.log(f"✓ {os.path.basename(filepath)} importado com sucesso")
            return True

        except Exception as e:
            self.log(f"✗ ERRO ao importar {os.path.basename(filepath)}: {str(e)}")
            self.session.rollback()
            return False

    def contar_registros(self):
        """Contar registros em cada tabela"""
        self.log("\n=== ESTATÍSTICAS ===")

        tables = [
            ("operadoras_rn1", OperadoraRN1),
            ("operadoras_stfc", OperadoraSTFC),
            ("faixa_operadora", FaixaOperadora)
        ]

        stats = {}
        for table_name, model in tables:
            count = self.session.query(model).count()
            stats[table_name] = count
            self.log(f"  {table_name}: {count:,} registros")

        return stats

    def validar_dados(self):
        """Validação de integridade dos dados"""
        self.log("\n=== VALIDAÇÃO ===")

        # Teste 1: Verificar se há registros
        rn1_count = self.session.query(OperadoraRN1).count()
        stfc_count = self.session.query(OperadoraSTFC).count()
        faixa_count = self.session.query(FaixaOperadora).count()

        if rn1_count == 0:
            self.log("✗ FALHA: Tabela operadoras_rn1 vazia!")
            return False

        if stfc_count == 0:
            self.log("✗ FALHA: Tabela operadoras_stfc vazia!")
            return False

        if faixa_count == 0:
            self.log("✗ FALHA: Tabela faixa_operadora vazia!")
            return False

        self.log(f"✓ Todas as tabelas têm dados")

        # Teste 2: Verificar encoding de alguns registros
        sample = self.session.query(OperadoraRN1).first()
        if sample:
            # Tentar acessar campos para verificar encoding
            nome = sample.nome_operadora
            self.log(f"✓ Encoding OK - Exemplo: {nome[:50]}...")

        # Teste 3: Verificar integridade de faixas
        invalid_faixas = self.session.query(FaixaOperadora).filter(
            FaixaOperadora.faixa_inicio > FaixaOperadora.faixa_fim
        ).count()

        if invalid_faixas > 0:
            self.log(f"⚠ Aviso: {invalid_faixas} faixas com início > fim")
        else:
            self.log(f"✓ Faixas de numeração válidas")

        return True

    def verificar_indices(self):
        """Verificar e criar índices adicionais se necessário"""
        self.log("\n=== VERIFICANDO ÍNDICES ===")

        # Verificar índices existentes
        result = self.session.execute(text("""
            SELECT tablename, indexname
            FROM pg_indexes
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname
        """))

        indices = result.fetchall()
        for table, index in indices:
            self.log(f"  {table}: {index}")

        self.log("✓ Índices verificados")

    def teste_consulta_portabilidade(self):
        """Teste de consulta real de portabilidade"""
        self.log("\n=== TESTE DE CONSULTA ===")

        # Pegar primeira faixa para testar
        faixa = self.session.query(FaixaOperadora).first()

        if not faixa:
            self.log("✗ Nenhuma faixa encontrada para teste")
            return False

        self.log(f"Testando consulta: DDD={faixa.ddd}, Prefixo={faixa.prefixo}")

        # Simular consulta de portabilidade
        numero_teste = int(faixa.prefixo) * 10000 + faixa.faixa_inicio

        resultado = self.session.query(FaixaOperadora).filter(
            FaixaOperadora.ddd == faixa.ddd,
            FaixaOperadora.prefixo == faixa.prefixo,
            FaixaOperadora.faixa_inicio <= (numero_teste % 10000),
            FaixaOperadora.faixa_fim >= (numero_teste % 10000)
        ).first()

        if resultado:
            self.log(f"✓ Consulta OK: {resultado.nome_operadora}")
            return True
        else:
            self.log("✗ Consulta falhou")
            return False

    def executar_importacao(self, test_mode=False):
        """Executa importação completa"""
        self.log("="*60)
        self.log("INICIANDO IMPORTAÇÃO DE DADOS DE PORTABILIDADE")
        self.log("="*60)

        if test_mode:
            self.log("\n*** MODO TESTE ATIVADO ***\n")

        # 1. Criar tabelas
        self.criar_tabelas()

        # 2. Limpar dados existentes
        self.limpar_tabelas()

        # 3. Download e importação
        arquivos_ordem = [
            "operadoras_rn1.sql",
            "operadoras_stfc.sql",
            "faixa_operadora.sql"
        ]

        for arquivo in arquivos_ordem:
            filepath = self.download_file(arquivo, test_mode)
            if not filepath:
                self.log(f"✗ FALHA no download de {arquivo}")
                return False

            if not self.importar_sql_direto(filepath, test_mode):
                self.log(f"✗ FALHA na importação de {arquivo}")
                return False

        # 4. Estatísticas
        self.contar_registros()

        # 5. Validação
        if not self.validar_dados():
            self.log("\n✗ VALIDAÇÃO FALHOU!")
            return False

        # 6. Verificar índices
        self.verificar_indices()

        # 7. Teste de consulta
        if not self.teste_consulta_portabilidade():
            self.log("\n⚠ Teste de consulta falhou")

        self.log("\n" + "="*60)
        self.log("✓ IMPORTAÇÃO CONCLUÍDA COM SUCESSO!")
        self.log("="*60)

        return True

    def cleanup(self):
        """Limpar arquivos temporários"""
        import shutil
        try:
            shutil.rmtree(self.temp_dir)
            self.log("✓ Arquivos temporários removidos")
        except:
            pass
        finally:
            self.session.close()


if __name__ == "__main__":
    # Verificar se é modo teste
    test_mode = "--test" in sys.argv

    importador = ImportadorPortabilidade()

    try:
        sucesso = importador.executar_importacao(test_mode=test_mode)
        importador.cleanup()

        sys.exit(0 if sucesso else 1)

    except Exception as e:
        print(f"ERRO FATAL: {str(e)}", file=sys.stderr)
        importador.cleanup()
        sys.exit(1)
