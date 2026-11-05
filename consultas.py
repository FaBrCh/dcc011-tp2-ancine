import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

TABELAS = ("municipio", "empresa", "atividade_economica", "empresa_atividade", "obra",
           "projeto_fomento", "obra_fomento", "complexo", "sala")
REQUERENTES = ("empresa brasileira independente", "demais empresas", "pessoa física")
MEDIDAS = ("exerce a atividade (qualquer)", "como atividade principal")
REFERENCIA_PCT = 2
REFERENCIAS = (f"abaixo de {REFERENCIA_PCT}%", f"{REFERENCIA_PCT}% ou mais")
SEM_GRUPO = "(sem grupo)"
MAIORES_GRUPOS = 12
MINIMO_OBRAS = 20


@dataclass(frozen=True)
class Consulta:
    sql: str
    parametros: tuple = ()

    def executar(self, banco):
        with closing(sqlite3.connect(Path(banco).resolve().as_uri() + "?mode=ro", uri=True)) as con:
            return pd.read_sql_query(self.sql, con, params=self.parametros)


OBRA_DETALHADA = f"""
WITH obra_detalhada AS (
    SELECT CAST(substr(o.data_emissao_cpb, 1, 4) AS INTEGER) AS ano, o.tipo, o.cnpj_requerente,
           COALESCE(me.uf, mp.uf) AS uf,
           CASE WHEN o.cnpj_requerente IS NULL THEN '{REQUERENTES[2]}'
                WHEN e.brasileira_independente = 1 THEN '{REQUERENTES[0]}'
                ELSE '{REQUERENTES[1]}' END AS requerente
    FROM obra o
    LEFT JOIN empresa e ON e.cnpj = o.cnpj_requerente
    LEFT JOIN municipio me ON me.id_municipio = e.id_municipio
    LEFT JOIN municipio mp ON mp.id_municipio = o.id_municipio_requerente_pf
)"""

SALA_EM_FUNCIONAMENTO = f"""
WITH sala_uf AS (
    SELECT s.nome AS sala, c.nome AS complexo, m.nome AS municipio, m.uf,
           COALESCE(e.grupo_exibidor, '{SEM_GRUPO}') AS grupo_exibidor,
           c.registro_complexo, s.assentos, s.assentos_cadeirantes
    FROM sala s
    JOIN complexo c ON c.registro_complexo = s.registro_complexo
    JOIN municipio m ON m.id_municipio = c.id_municipio
    JOIN empresa e ON e.cnpj = c.cnpj_exibidor
    WHERE s.situacao = 'EM FUNCIONAMENTO' AND s.assentos > 0
)"""

OBRA_COM_FOMENTO = """
WITH obra_com_fomento AS (
    SELECT o.tipo, CAST(substr(o.data_emissao_cpb, 1, 4) AS INTEGER) AS ano,
           o.segmento_destinacao = 'SALAS DE EXIBIÇÃO' AS para_salas,
           EXISTS (SELECT 1 FROM obra_fomento f WHERE f.cpb = o.cpb) AS fomentada
    FROM obra o
)"""


def _em(coluna, valores):
    valores = tuple(valores)
    return (f"{coluna} IN ({', '.join('?' * len(valores))})" if valores else "", valores)


def _entre(coluna, inicio, fim):
    return f"{coluna} BETWEEN ? AND ?", (inicio, fim)


def _onde(*filtros):
    condicoes = [condicao for condicao, _ in filtros if condicao]
    parametros = tuple(valor for _, valores in filtros for valor in valores)
    return ("WHERE " + " AND ".join(condicoes) if condicoes else ""), parametros


def contagem_tuplas():
    contagens = "\nUNION ALL\n".join(f"SELECT '{t}' AS tabela, COUNT(*) AS tuplas FROM {t}" for t in TABELAS)
    return Consulta(f"SELECT tabela, tuplas, SUM(tuplas) OVER () AS total FROM (\n{contagens}\n)")


def lista_ufs():
    return Consulta("SELECT DISTINCT uf FROM municipio ORDER BY uf")


def tipos_de_obra():
    return Consulta("SELECT DISTINCT tipo FROM obra ORDER BY tipo")


def anos_cpb():
    return Consulta("SELECT CAST(MIN(substr(data_emissao_cpb, 1, 4)) AS INTEGER) AS menor,\n"
                    "       CAST(MAX(substr(data_emissao_cpb, 1, 4)) AS INTEGER) AS maior,\n"
                    "       CAST(substr(MAX(data_emissao_cpb), 6, 2) AS INTEGER) AS ultimo_mes\nFROM obra")


def _filtro_obras(inicio, fim, tipos, ufs):
    return _onde(_entre("ano", inicio, fim), _em("tipo", tipos), _em("uf", ufs))


def obras_por_ano(inicio, fim, tipos=(), ufs=()):
    filtro, parametros = _filtro_obras(inicio, fim, tipos, ufs)
    return Consulta(f"""{OBRA_DETALHADA}
SELECT ano, requerente, COUNT(*) AS obras
FROM obra_detalhada
{filtro}
GROUP BY ano, requerente
ORDER BY ano""", parametros)


def total_anual(inicio, fim, tipos=(), ufs=()):
    filtro, parametros = _filtro_obras(inicio, fim, tipos, ufs)
    return Consulta(f"""{OBRA_DETALHADA},
anual AS (SELECT ano, COUNT(*) AS obras FROM obra_detalhada {filtro} GROUP BY ano)
SELECT ano, obras, ROUND(100.0 * obras / LAG(obras) OVER (ORDER BY ano) - 100, 1) AS variacao_pct
FROM anual
ORDER BY ano""", parametros)


def ranking_requerentes(top_n, uf=None):
    filtro, parametros = _onde(_em("uf", [uf] if uf else []))
    return Consulta(f"""{OBRA_DETALHADA},
por_requerente AS (
    SELECT cnpj_requerente, uf, COUNT(*) AS obras, SUM(COUNT(*)) OVER () AS obras_no_recorte
    FROM obra_detalhada
    {filtro}
    GROUP BY cnpj_requerente
)
SELECT e.razao_social, p.uf, p.obras,
       ROUND(100.0 * p.obras / p.obras_no_recorte, 2) AS pct_obras,
       ROUND(100.0 * SUM(p.obras) OVER (ORDER BY p.obras DESC ROWS UNBOUNDED PRECEDING) / p.obras_no_recorte, 2)
           AS pct_acumulado,
       COUNT(*) OVER () AS empresas_requerentes,
       p.obras_no_recorte
FROM por_requerente p
JOIN empresa e ON e.cnpj = p.cnpj_requerente
ORDER BY p.obras DESC
LIMIT ?""", (*parametros, top_n))


def segmentos_requerentes(uf=None):
    filtro, parametros = _onde(_em("m.uf", [uf] if uf else []))
    return Consulta(f"""
WITH obra_empresa AS MATERIALIZED (
    SELECT o.cpb, ea.classificacao, a.segmento
    FROM obra o
    JOIN empresa e ON e.cnpj = o.cnpj_requerente
    LEFT JOIN municipio m ON m.id_municipio = e.id_municipio
    JOIN empresa_atividade ea ON ea.cnpj = e.cnpj
    JOIN atividade_economica a ON a.id_atividade = ea.id_atividade
    {filtro}
),
total AS (SELECT COUNT(DISTINCT cpb) AS obras FROM obra_empresa)
SELECT segmento, '{MEDIDAS[0]}' AS medida, ROUND(100.0 * COUNT(DISTINCT cpb) / total.obras, 1) AS pct_obras
FROM obra_empresa CROSS JOIN total
GROUP BY segmento
UNION ALL
SELECT segmento, '{MEDIDAS[1]}',
       ROUND(100.0 * COUNT(DISTINCT CASE WHEN classificacao = 'PRINCIPAL' THEN cpb END) / total.obras, 1)
FROM obra_empresa CROSS JOIN total
GROUP BY segmento""", parametros)


def salas_por_uf(ufs=()):
    filtro, parametros = _onde(_em("uf", ufs))
    return Consulta(f"""{SALA_EM_FUNCIONAMENTO}
SELECT uf, COUNT(*) AS salas, SUM(assentos) AS assentos,
       SUM(assentos_cadeirantes) AS assentos_cadeirantes,
       ROUND(100.0 * SUM(assentos_cadeirantes) / SUM(assentos), 2) AS pct_cadeirantes,
       CASE WHEN 100.0 * SUM(assentos_cadeirantes) / SUM(assentos) < {REFERENCIA_PCT} THEN '{REFERENCIAS[0]}'
            ELSE '{REFERENCIAS[1]}' END AS referencia,
       SUM(100.0 * assentos_cadeirantes / assentos < {REFERENCIA_PCT}) AS salas_abaixo_referencia,
       SUM(COUNT(*)) OVER () AS total_salas,
       SUM(SUM(assentos)) OVER () AS total_assentos,
       100.0 * SUM(SUM(assentos_cadeirantes)) OVER () / SUM(SUM(assentos)) OVER () AS total_pct_cadeirantes
FROM sala_uf
{filtro}
GROUP BY uf
ORDER BY assentos DESC""", parametros)


def grupos_exibidores(ufs=()):
    filtro, parametros = _onde(_em("uf", ufs))
    return Consulta(f"""{SALA_EM_FUNCIONAMENTO}
SELECT grupo_exibidor, COUNT(DISTINCT registro_complexo) AS complexos, COUNT(*) AS salas,
       SUM(assentos) AS assentos,
       ROUND(100.0 * SUM(assentos) / SUM(SUM(assentos)) OVER (), 1) AS pct_assentos
FROM sala_uf
{filtro}
GROUP BY grupo_exibidor
ORDER BY assentos DESC
LIMIT {MAIORES_GRUPOS}""", parametros)


def salas(ufs=()):
    filtro, parametros = _onde(_em("uf", ufs))
    return Consulta(f"""{SALA_EM_FUNCIONAMENTO}
SELECT sala, complexo, municipio, uf, grupo_exibidor, assentos, assentos_cadeirantes,
       ROUND(100.0 * assentos_cadeirantes / assentos, 2) AS pct_cadeirantes
FROM sala_uf
{filtro}
ORDER BY assentos DESC""", parametros)


def _filtro_fomento(inicio, fim, para_salas):
    return _onde(_entre("ano", inicio, fim), _em("para_salas", () if para_salas is None else (para_salas,)))


def fomento_por_tipo(inicio, fim, para_salas=None):
    filtro, parametros = _filtro_fomento(inicio, fim, para_salas)
    return Consulta(f"""{OBRA_COM_FOMENTO}
SELECT tipo, COUNT(*) AS obras, SUM(fomentada) AS com_fomento,
       ROUND(100.0 * SUM(fomentada) / COUNT(*), 1) AS pct_com_fomento,
       SUM(COUNT(*)) OVER () AS total_obras,
       SUM(SUM(fomentada)) OVER () AS total_com_fomento,
       100.0 * SUM(SUM(fomentada)) OVER () / SUM(COUNT(*)) OVER () AS total_pct
FROM obra_com_fomento
{filtro}
GROUP BY tipo
HAVING COUNT(*) >= {MINIMO_OBRAS}
ORDER BY pct_com_fomento DESC""", parametros)


def fomento_por_ano(inicio, fim, para_salas=None):
    filtro, parametros = _filtro_fomento(inicio, fim, para_salas)
    return Consulta(f"""{OBRA_COM_FOMENTO}
SELECT ano, COUNT(*) AS obras, SUM(fomentada) AS com_fomento,
       ROUND(100.0 * SUM(fomentada) / COUNT(*), 1) AS pct_com_fomento
FROM obra_com_fomento
{filtro}
GROUP BY ano
HAVING COUNT(*) >= {MINIMO_OBRAS}
ORDER BY ano""", parametros)
