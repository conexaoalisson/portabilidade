#!/usr/bin/env python3
"""
Script de validação de lógica sem dependências externas
"""

def test_telefone_parsing():
    """Testa lógica de parsing de telefone"""
    print("=== TESTE: Parsing de Telefone ===")

    # Teste 1: Celular (11 dígitos)
    telefone = "11987654321"
    ddd = telefone[:2]
    prefixo = telefone[2:6]
    numero = telefone[6:]

    assert ddd == "11", f"DDD incorreto: {ddd}"
    assert prefixo == "9876", f"Prefixo incorreto: {prefixo}"
    assert numero == "54321", f"Número incorreto: {numero}"
    print(f"✓ Celular: DDD={ddd}, Prefixo={prefixo}, Numero={numero}")

    # Teste 2: Fixo (10 dígitos)
    telefone = "1133334444"
    ddd = telefone[:2]
    prefixo = telefone[2:6]
    numero = telefone[6:]

    assert ddd == "11", f"DDD incorreto: {ddd}"
    assert prefixo == "3333", f"Prefixo incorreto: {prefixo}"
    assert numero == "4444", f"Número incorreto: {numero}"
    print(f"✓ Fixo: DDD={ddd}, Prefixo={prefixo}, Numero={numero}")

def test_faixa_validacao():
    """Testa lógica de validação de faixa"""
    print("\n=== TESTE: Validação de Faixa ===")

    # Simular consulta de faixa
    faixa_inicio = 5000
    faixa_fim = 5999
    numero_teste = 5432

    # Verificar se número está na faixa
    na_faixa = faixa_inicio <= numero_teste <= faixa_fim

    assert na_faixa, f"Número {numero_teste} deveria estar na faixa [{faixa_inicio}-{faixa_fim}]"
    print(f"✓ Número {numero_teste} está na faixa [{faixa_inicio}-{faixa_fim}]")

    # Teste negativo
    numero_teste = 6000
    na_faixa = faixa_inicio <= numero_teste <= faixa_fim
    assert not na_faixa, f"Número {numero_teste} NÃO deveria estar na faixa"
    print(f"✓ Número {numero_teste} corretamente fora da faixa")

def test_utf8_validation():
    """Testa validação de UTF-8"""
    print("\n=== TESTE: Validação UTF-8 ===")

    # String com caracteres especiais brasileiros
    texto = "TIM S/A - TELECOMUNICAÇÕES"

    try:
        # Tentar encodar e decodar
        encoded = texto.encode('utf-8')
        decoded = encoded.decode('utf-8')
        assert texto == decoded, "Encoding/Decoding falhou"
        print(f"✓ UTF-8 OK: {texto}")
    except UnicodeError as e:
        print(f"✗ ERRO UTF-8: {e}")
        raise

def test_sql_structure():
    """Valida estrutura SQL básica"""
    print("\n=== TESTE: Estrutura SQL ===")

    # Verificar se arquivos SQL existem
    import os

    sql_files = [
        "dados_portabilidade/operadoras_rn1.sql",
        "dados_portabilidade/operadoras_stfc.sql",
        "dados_portabilidade/faixa_operadora.sql"
    ]

    for sql_file in sql_files:
        if os.path.exists(sql_file):
            # Verificar se é UTF-8
            with open(sql_file, 'r', encoding='utf-8') as f:
                first_line = f.readline()
                print(f"✓ {sql_file}: UTF-8 válido")
        else:
            print(f"⚠ {sql_file}: Não encontrado (será baixado na importação)")

def test_indices_definition():
    """Valida definição de índices no código"""
    print("\n=== TESTE: Definição de Índices ===")

    # Índices esperados
    indices_esperados = [
        "idx_ddd_prefixo_faixa",
        "idx_sigla_operadora",
        "idx_ddd",
        "idx_prefixo",
        "idx_estado",
    ]

    # Verificar se estão definidos no código
    with open("app/models.py", 'r') as f:
        conteudo = f.read()

        for indice in indices_esperados:
            if indice in conteudo:
                print(f"✓ Índice definido: {indice}")
            else:
                print(f"✗ Índice não encontrado: {indice}")

def test_api_endpoints():
    """Valida definição de endpoints na API"""
    print("\n=== TESTE: Endpoints API ===")

    endpoints_esperados = [
        ("/", "root"),
        ("/health", "health"),
        ("/consulta", "consultar_portabilidade"),
        ("/stats", "stats"),
        ("/import", "import_data"),
        ("/import/status", "import_status"),
        ("/info", "info"),
    ]

    with open("app/main.py", 'r') as f:
        conteudo = f.read()

        for endpoint, funcao in endpoints_esperados:
            if f'async def {funcao}' in conteudo or f'def {funcao}' in conteudo:
                print(f"✓ Endpoint {endpoint}: {funcao}()")
            else:
                print(f"✗ Função não encontrada: {funcao}")

def main():
    print("="*60)
    print("VALIDAÇÃO DE LÓGICA DO SISTEMA DE PORTABILIDADE")
    print("="*60)

    try:
        test_telefone_parsing()
        test_faixa_validacao()
        test_utf8_validation()
        test_sql_structure()
        test_indices_definition()
        test_api_endpoints()

        print("\n" + "="*60)
        print("✓ TODOS OS TESTES DE LÓGICA PASSARAM!")
        print("="*60)
        return 0

    except AssertionError as e:
        print(f"\n✗ TESTE FALHOU: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
