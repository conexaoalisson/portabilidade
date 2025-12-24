from sqlalchemy import Column, Integer, String, Text, Index, DateTime, BigInteger
from app.database import Base

class FaixaOperadora(Base):
    __tablename__ = "faixa_operadora"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome_operadora = Column(String(100))
    tipo_numero = Column(String(1))
    ddi_ddd = Column(String(10))
    ddd = Column(String(5), index=True)  # Índice para consultas por DDD
    prefixo = Column(String(10), index=True)  # Índice para consultas por prefixo
    faixa_inicio = Column(Integer)
    faixa_fim = Column(Integer)
    sigla_operadora = Column(String(10))
    estado = Column(String(2), index=True)  # Índice para consultas por estado
    codigo_regiao = Column(String(10))

    __table_args__ = (
        # Índice composto para consulta de portabilidade (DDD + Prefixo + Faixa)
        Index('idx_ddd_prefixo_faixa', 'ddd', 'prefixo', 'faixa_inicio', 'faixa_fim'),
        # Índice para consulta por operadora
        Index('idx_sigla_operadora', 'sigla_operadora'),
    )


class OperadoraRN1(Base):
    __tablename__ = "operadoras_rn1"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome_operadora = Column(String(150))
    cnpj = Column(String(20), index=True)  # Índice para consultas por CNPJ
    rn1_prefixo = Column(String(10), unique=True, index=True)  # Prefixo RN1 único


class OperadoraSTFC(Base):
    __tablename__ = "operadoras_stfc"

    id = Column(Integer, primary_key=True, autoincrement=True)
    eot = Column(String(10), index=True)  # EOT (permite duplicatas nos dados de origem)
    nome_fantasia = Column(String(150))
    razao_social = Column(String(200))
    csp = Column(String(10))
    tipo_servico = Column(String(50))
    modalidade_banda = Column(String(50))
    area_prestacao = Column(String(100))
    holding = Column(String(150))
    cnpj = Column(String(25), index=True)
    inscricao_estadual = Column(String(50))
    contato = Column(String(100))
    email = Column(String(150))
    fone = Column(String(100))
    endereco_nf = Column(Text)
    endereco_correspondencia = Column(Text)
    uf = Column(String(2), index=True)
    regiao = Column(String(10))
    concessao = Column(String(5))
    rn1 = Column(String(10), index=True)
    spid = Column(String(10), index=True)  # SPID (permite duplicatas nos dados de origem)


class PortabilidadeHistorico(Base):
    __tablename__ = "portabilidade_historico"

    id = Column(Integer, primary_key=True, autoincrement=True)
    spid_origem = Column(String(10), index=True)  # Campo 1
    flag_1 = Column(BigInteger)  # Campo 2
    data_criacao = Column(String(50))  # Campo 3 - timestamp
    telefone = Column(BigInteger, index=True)  # Campo 4 - número completo
    codigo_1 = Column(BigInteger)  # Campo 5
    spid_destino = Column(String(10))  # Campo 6
    codigo_operadora = Column(String(10))  # Campo 7
    codigo_completo = Column(String(10), index=True)  # Campo 8
    flag_2 = Column(BigInteger)  # Campo 9
    flag_3 = Column(BigInteger)  # Campo 10
    status = Column(String(20))  # Campo 11 - new/old/etc
    flag_4 = Column(BigInteger)  # Campo 12
    data_atualizacao = Column(String(50))  # Campo 13 - timestamp
    flag_5 = Column(BigInteger)  # Campo 14
    data_nula_1 = Column(String(50))  # Campo 15
    flag_6 = Column(BigInteger)  # Campo 16
    flag_7 = Column(BigInteger)  # Campo 17
    flag_8 = Column(BigInteger)  # Campo 18
    data_nula_2 = Column(String(50))  # Campo 19

    __table_args__ = (
        Index('idx_telefone', 'telefone'),
        Index('idx_spid_origem', 'spid_origem'),
        Index('idx_codigo_completo', 'codigo_completo'),
    )
