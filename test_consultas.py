import unittest
from pathlib import Path

import consultas

BANCO = Path(__file__).resolve().parent / "tp2.db"


def linha(dados, coluna, valor):
    return dados[dados[coluna] == valor].iloc[0]


@unittest.skipUnless(BANCO.exists(), "execute o tp2.ipynb antes para criar o tp2.db")
class ConsultasReproduzemORelatorio(unittest.TestCase):
    def test_numeros_publicados_no_notebook(self):
        anual = consultas.total_anual(2002, 2026).executar(BANCO)
        por_tipo = consultas.obras_por_ano(2019, 2020).executar(BANCO)
        independentes = por_tipo[por_tipo["requerente"] == consultas.REQUERENTES[0]]
        ranking = consultas.ranking_requerentes(10).executar(BANCO)
        segmentos = consultas.segmentos_requerentes().executar(BANCO)
        qualquer = segmentos[segmentos["medida"] == consultas.MEDIDAS[0]]
        principal = segmentos[segmentos["medida"] == consultas.MEDIDAS[1]]
        grupos = consultas.grupos_exibidores().executar(BANCO)
        por_uf = consultas.salas_por_uf().executar(BANCO)
        salas_todas = consultas.fomento_por_tipo(2002, 2026, para_salas=True).executar(BANCO)
        salas_2015 = consultas.fomento_por_tipo(2015, 2026, para_salas=True).executar(BANCO)
        casos = [
            ("total de tuplas (seção 3.7)", consultas.contagem_tuplas().executar(BANCO)["total"].iloc[0], 249570),
            ("obras em 2019 (Consulta 9)", linha(anual, "ano", 2019)["obras"], 3545),
            ("obras em 2020 (Consulta 9)", linha(anual, "ano", 2020)["obras"], 2942),
            ("variação 2020 (Consulta 9)", linha(anual, "ano", 2020)["variacao_pct"], -17.0),
            ("recorde de 2025 (Consulta 9)", linha(anual, "ano", 2025)["obras"], 3978),
            ("independentes 2019 e 2020 (Consulta 9)", independentes["obras"].tolist(), [1426, 1009]),
            ("maior requerente (Consulta 3)", ranking["obras"].iloc[0], 2650),
            ("fatia do maior requerente (Consulta 3)", ranking["pct_obras"].iloc[0], 4.19),
            ("fatia das 10 maiores (Consulta 3)", ranking["pct_acumulado"].iloc[-1], 13.11),
            ("obras no recorte sem filtro (Consulta 3)", ranking["obras_no_recorte"].iloc[0], 63255),
            ("empresas requerentes (Consulta 3)", ranking["empresas_requerentes"].iloc[0], 8180),
            ("produção, qualquer (Consulta 7)", linha(qualquer, "segmento", "Produção")["pct_obras"], 88.1),
            ("distribuição, qualquer (Consulta 7)", linha(qualquer, "segmento", "Distribuição")["pct_obras"], 49.3),
            ("TV como principal (Consulta 7)", linha(principal, "segmento", "Programação e TV")["pct_obras"], 16.0),
            ("fatia da Cinemark (Consulta 8)", linha(grupos, "grupo_exibidor", "CINEMARK")["pct_assentos"], 19.2),
            ("salas em funcionamento (Consulta 10)", por_uf["total_salas"].iloc[0], 3721),
            ("assentos em funcionamento (Consulta 10)", por_uf["total_assentos"].iloc[0], 709900),
            ("cadeirantes no país (Consulta 10)", round(por_uf["total_pct_cadeirantes"].iloc[0], 2), 1.93),
            ("salas abaixo de 2% (Consulta 10)", por_uf["salas_abaixo_referencia"].sum(), 1553),
            ("cadeirantes no DF (Consulta 10)", linha(por_uf, "uf", "DF")["pct_cadeirantes"], 1.50),
            ("ficção para salas (Consulta 4)", linha(salas_todas, "tipo", "FICÇÃO")["pct_com_fomento"], 25.8),
            ("ficção para salas desde 2015 (Consulta 4)",
             linha(salas_2015, "tipo", "FICÇÃO")["pct_com_fomento"], 19.4),
        ]
        for nome, obtido, esperado in casos:
            with self.subTest(nome):
                self.assertEqual(obtido, esperado)

    def test_valor_escolhido_vai_como_parametro_e_nao_como_sql(self):
        hostil = "SP') OR 1 = 1 OR uf IN ('RJ"
        for nome, consulta in [("salas por UF", consultas.salas(ufs=[hostil])),
                               ("ranking por UF", consultas.ranking_requerentes(5, uf=hostil)),
                               ("obras por tipo", consultas.obras_por_ano(2002, 2026, tipos=[hostil]))]:
            with self.subTest(nome):
                self.assertIn(hostil, consulta.parametros)
                self.assertTrue(consulta.executar(BANCO).empty)


if __name__ == "__main__":
    unittest.main()
