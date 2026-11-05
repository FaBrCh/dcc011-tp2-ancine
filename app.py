import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

import consultas

PASTA = Path(__file__).resolve().parent
BANCO = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else PASTA / "tp2.db"

AZUL, LARANJA, VERDE, CINZA = "#2a78d6", "#eb6834", "#1baf7a", "#b5b3ad"
TINTA, TINTA_2, GRADE, FAIXA = "#0b0b0b", "#52514e", "#e4e3df", "#f0efec"
LOCALE = alt.Locale(number=alt.NumberLocale(decimal=",", thousands=".", grouping=[3], currency=["R$ ", ""]))
SEGMENTOS_FOMENTO = {"Salas de exibição": True, "Demais segmentos": False, "Todos": None}
MESES = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
         "novembro", "dezembro")
ANOS_COMPLETOS = "anos completos"


@st.cache_data(show_spinner=False, max_entries=64)
def dados(consulta):
    return consulta.executar(BANCO)


def consultar_mostrando_sql(consulta, titulo="Ver o SQL desta visualização"):
    with st.expander(titulo):
        st.code(consulta.sql.strip(), language="sql")
        if consulta.parametros:
            st.caption("Valores dos marcadores ?, na ordem: " + ", ".join(map(str, consulta.parametros)))
    return dados(consulta)


def br(valor, casas=0):
    return f"{valor:_.{casas}f}".replace(".", ",").replace("_", ".")


def metricas(pares):
    for coluna, (rotulo, valor) in zip(st.columns(len(pares)), pares):
        coluna.metric(rotulo, valor)


def intervalo_de_anos():
    anos = dados(consultas.anos_cpb()).iloc[0]
    return int(anos["menor"]), int(anos["maior"])


def eixo_anos(inicio, fim, campo="ano"):
    return alt.X(f"{campo}:Q", title=None, axis=alt.Axis(format="d", tickMinStep=1),
                 scale=alt.Scale(domain=[inicio, fim], zero=False, nice=False))


def desenhar(grafico, altura=320):
    grafico = (grafico.properties(height=altura)
               .configure(locale=LOCALE, tooltipFormat=alt.FormatConfig(numberFormat=","))
               .configure_view(stroke=None)
               .configure_mark(color=AZUL)
               .configure_bar(cornerRadiusEnd=4)
               .configure_line(strokeWidth=2, point=alt.OverlayMarkDef(size=60, filled=True))
               .configure_axis(gridColor=GRADE, domainColor=GRADE, tickColor=GRADE, labelColor=TINTA_2,
                               titleColor=TINTA_2, labelFontSize=11, titleFontSize=11, titleFontWeight="normal")
               .configure_axisQuantitative(tickCount=8, labelOverlap=True)
               .configure_title(anchor="start", fontSize=14, color=TINTA)
               .configure_legend(orient="top", title=None, labelColor=TINTA_2, labelFontSize=11))
    st.altair_chart(grafico, theme=None, width="stretch")


def barras_horizontais(tabela, categoria, valor, titulo, rotulo_eixo, dicas, cor=alt.Undefined):
    desenhar(alt.Chart(tabela, title=titulo).mark_bar(height={"band": 0.7}).encode(
        x=alt.X(f"{valor}:Q", title=rotulo_eixo),
        y=alt.Y(f"{categoria}:N", sort="-x", title=None, axis=alt.Axis(labelLimit=340)),
        color=cor,
        tooltip=dicas,
    ), 24 * len(tabela) + 40)


def pagina_inicial():
    st.markdown(
        "Registro público do audiovisual brasileiro (ANCINE), modelado no SQLite pelo notebook `tp2.ipynb`. "
        "Cada aba retoma uma das quatro investigações do relatório e refaz as consultas com os filtros escolhidos."
    )
    contagem = consultar_mostrando_sql(consultas.contagem_tuplas(), "Ver o SQL da contagem de tuplas")
    por_tabela = dict(zip(contagem["tabela"], contagem["tuplas"]))
    metricas([("tuplas no banco", br(contagem["total"].iloc[0])), ("obras", br(por_tabela["obra"])),
              ("empresas", br(por_tabela["empresa"])), ("salas", br(por_tabela["sala"]))])
    esquerda, direita = st.columns([1, 2.4])
    with esquerda:
        st.subheader("Tuplas por tabela")
        st.dataframe(contagem, hide_index=True, width="stretch", column_order=["tabela", "tuplas"],
                     column_config={"tuplas": st.column_config.NumberColumn(format="localized")})
    with direita:
        st.subheader("Diagrama ER")
        st.image(str(PASTA / "diagramas" / "diagrama_er.svg"), width="stretch")
    with st.expander("Diagrama relacional"):
        st.image(str(PASTA / "diagramas" / "diagrama_relacional.svg"), width="stretch")


def evolucao():
    st.markdown("Obras com CPB emitido por ano, separadas pelo tipo de requerente (Consultas 6 e 9 do relatório).")
    menor, maior = intervalo_de_anos()
    ultimo_mes = int(dados(consultas.anos_cpb())["ultimo_mes"].iloc[0])
    c1, c2, c3 = st.columns([1.4, 1, 1])
    inicio, fim = c1.slider("Anos de emissão do CPB", menor, maior, (menor, maior), key="anos_evolucao")
    tipos = c2.multiselect("Tipo de obra", dados(consultas.tipos_de_obra())["tipo"],
                           placeholder="Todos os tipos", key="tipos_evolucao")
    ufs = c3.multiselect("UF do requerente", dados(consultas.lista_ufs())["uf"], placeholder="Todas as UFs",
                         key="ufs_evolucao")

    por_tipo = consultar_mostrando_sql(consultas.obras_por_ano(inicio, fim, tipos, ufs))
    if por_tipo.empty:
        st.info("Nenhuma obra com esses filtros.")
        return
    parcial = fim == maior and ultimo_mes < 12
    rotulo_parcial = f"{maior} parcial (até {MESES[ultimo_mes - 1]})"
    trechos = por_tipo.assign(trecho=ANOS_COMPLETOS)
    if parcial:
        trechos = pd.concat([trechos[trechos["ano"] != maior],
                             por_tipo[por_tipo["ano"] >= maior - 1].assign(trecho=rotulo_parcial)])
    cor = alt.Color("requerente:N", scale=alt.Scale(domain=consultas.REQUERENTES, range=[AZUL, LARANJA, VERDE]))
    linhas = alt.Chart(trechos, title="Obras registradas por ano e tipo de requerente").mark_line(point=False).encode(
        x=eixo_anos(inicio, fim),
        y=alt.Y("obras:Q", title="obras com CPB emitido"),
        color=cor,
        strokeDash=alt.StrokeDash("trecho:N", scale=alt.Scale(domain=[ANOS_COMPLETOS, rotulo_parcial],
                                                              range=[[1, 0], [4, 3]])),
    )
    pontos = alt.Chart(por_tipo).mark_point(filled=True, size=60, strokeWidth=2, opacity=1).encode(
        x=eixo_anos(inicio, fim), y="obras:Q", color=cor, stroke=cor,
        fill=alt.condition(alt.datum.ano == (maior if parcial else None), alt.value("white"), cor),
        tooltip=[alt.Tooltip("ano:Q", format="d"), "requerente:N", alt.Tooltip("obras:Q")])
    faixa = alt.Chart(pd.DataFrame({"de": [2019.5], "ate": [2021.5], "meio": [2020.5], "rotulo": ["pandemia"]}))
    sombra = faixa.mark_rect(color=FAIXA, clip=True).encode(x=eixo_anos(inicio, fim, "de"), x2="ate:Q")
    texto = faixa.mark_text(baseline="top", dy=4, color=TINTA_2, fontSize=11, clip=True).encode(
        x=eixo_anos(inicio, fim, "meio"), y=alt.value(0), text="rotulo:N")
    desenhar(sombra + texto + linhas + pontos, 360)

    variacao = consultar_mostrando_sql(consultas.total_anual(inicio, fim, tipos, ufs),
                                       "Ver o SQL do total anual e da variação")
    variacao["variacao_pct"] = variacao["variacao_pct"].map(lambda v: "" if pd.isna(v) else br(v, 1))
    st.dataframe(variacao, hide_index=True, width="stretch", height=240,
                 column_config={"ano": st.column_config.NumberColumn(format="%d"),
                                "variacao_pct": st.column_config.TextColumn("variação sobre o ano anterior (%)",
                                                                            alignment="right")})
    if parcial:
        st.caption(f"A variação de {maior} compara janeiro a {MESES[ultimo_mes - 1]} com o ano inteiro de "
                   f"{maior - 1}.")


def concentracao():
    st.markdown("Quem registra as obras e em que segmentos essas empresas atuam (Consultas 3 e 7 do relatório).")
    c1, c2 = st.columns(2)
    top_n = c1.slider("Quantas empresas mostrar (top N)", 5, 30, 10, key="top_n")
    uf = c2.selectbox("UF do requerente", dados(consultas.lista_ufs())["uf"], index=None,
                      placeholder="Todas as UFs", key="uf_concentracao")

    ranking = consultar_mostrando_sql(consultas.ranking_requerentes(top_n, uf))
    if ranking.empty:
        st.info("Nenhuma empresa requerente nessa UF.")
        return
    st.caption(f"As {len(ranking)} primeiras somam {br(ranking['pct_acumulado'].iloc[-1], 2)}% das "
               f"{br(ranking['obras_no_recorte'].iloc[0])} obras {'com requerente em ' + uf if uf else 'do país'} "
               f"(empresas e pessoas físicas), entre {br(ranking['empresas_requerentes'].iloc[0])} empresas "
               "requerentes.")
    barras_horizontais(
        ranking, "razao_social", "obras", f"As {len(ranking)} empresas que mais registraram obras", "obras registradas",
        ["razao_social:N", "uf:N", alt.Tooltip("obras:Q"), alt.Tooltip("pct_obras:Q", title="% das obras"),
         alt.Tooltip("pct_acumulado:Q", title="% acumulado")])

    segmentos = consultar_mostrando_sql(consultas.segmentos_requerentes(uf), "Ver o SQL dos segmentos de atividade")
    desenhar(alt.Chart(segmentos, title="Segmentos em que atuam as empresas requerentes").mark_bar().encode(
        x=alt.X("pct_obras:Q", title="% das obras de empresas com atividades cadastradas"),
        y=alt.Y("segmento:N", sort="-x", title=None),
        yOffset=alt.YOffset("medida:N", sort=consultas.MEDIDAS),
        color=alt.Color("medida:N", scale=alt.Scale(domain=consultas.MEDIDAS, range=[AZUL, LARANJA])),
        tooltip=["segmento:N", "medida:N", alt.Tooltip("pct_obras:Q", title="% das obras")],
    ), 300)


def parque_exibidor():
    st.markdown("Salas em funcionamento com assentos e município informados, o mesmo recorte da Consulta 10 "
                "(Consultas 1, 5, 8 e 10 do relatório).")
    ufs = st.multiselect("UF do complexo", dados(consultas.lista_ufs())["uf"], placeholder="Todas as UFs",
                         key="ufs_parque")

    por_uf = consultar_mostrando_sql(consultas.salas_por_uf(ufs))
    if por_uf.empty:
        st.info("Nenhuma sala em funcionamento nessas UFs.")
        return
    totais = por_uf.iloc[0]
    metricas([("salas em funcionamento", br(totais["total_salas"])), ("assentos", br(totais["total_assentos"])),
              ("assentos para cadeirantes", br(totais["total_pct_cadeirantes"], 2) + "%")])
    dicas = ["uf:N", alt.Tooltip("salas:Q"), alt.Tooltip("assentos:Q"),
             alt.Tooltip("assentos_cadeirantes:Q", title="assentos para cadeirantes"),
             alt.Tooltip("pct_cadeirantes:Q", title="% para cadeirantes"),
             alt.Tooltip("salas_abaixo_referencia:Q", title=f"salas abaixo de {consultas.REFERENCIA_PCT}%")]
    desenhar(alt.Chart(por_uf, title="Assentos em funcionamento por UF").mark_bar().encode(
        x=alt.X("uf:N", sort="-y", title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("assentos:Q", title="assentos"), tooltip=dicas))

    titulo = f"Assentos para cadeirantes por UF, contra a referência de {consultas.REFERENCIA_PCT}% da lotação"
    barras = alt.Chart(por_uf, title=titulo).mark_bar().encode(
        x=alt.X("uf:N", sort="y", title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("pct_cadeirantes:Q", title="% dos assentos para cadeirantes",
                scale=alt.Scale(domain=[0, max(consultas.REFERENCIA_PCT, por_uf["pct_cadeirantes"].max()) + 0.4])),
        color=alt.Color("referencia:N", scale=alt.Scale(domain=consultas.REFERENCIAS, range=[LARANJA, AZUL])),
        tooltip=dicas)
    referencia = alt.Chart(pd.DataFrame({"y": [consultas.REFERENCIA_PCT],
                                           "rotulo": [f"referência de {consultas.REFERENCIA_PCT}% da lotação"]}))
    regra = referencia.mark_rule(color=TINTA, strokeWidth=1).encode(y="y:Q")
    rotulo = referencia.mark_text(align="left", baseline="bottom", dx=4, dy=-3, color=TINTA, fontSize=11).encode(
        x=alt.value(0), y="y:Q", text="rotulo:N")
    desenhar(barras + regra + rotulo)

    grupos = consultar_mostrando_sql(consultas.grupos_exibidores(ufs), "Ver o SQL da fatia dos grupos exibidores")
    barras_horizontais(
        grupos, "grupo_exibidor", "pct_assentos",
        f"Fatia dos assentos por grupo exibidor ({consultas.MAIORES_GRUPOS} maiores; cinza: sem grupo)",
        "% dos assentos no filtro", ["grupo_exibidor:N", alt.Tooltip("complexos:Q"),
                                     alt.Tooltip("salas:Q"), alt.Tooltip("assentos:Q"),
                                     alt.Tooltip("pct_assentos:Q", title="% dos assentos")],
        alt.condition(alt.datum.grupo_exibidor == consultas.SEM_GRUPO, alt.value(CINZA), alt.value(AZUL)))

    st.subheader("Salas")
    st.caption("Clique no cabeçalho de uma coluna para ordenar.")
    salas = consultar_mostrando_sql(consultas.salas(ufs), "Ver o SQL da tabela de salas")
    st.dataframe(salas, hide_index=True, width="stretch", height=380,
                 column_config={"municipio": "município", "uf": "UF", "grupo_exibidor": "grupo exibidor",
                                "assentos_cadeirantes": "assentos para cadeirantes",
                                "pct_cadeirantes": st.column_config.NumberColumn("% para cadeirantes", format="%.2f")})


def fomento():
    st.markdown("Parcela das obras com projeto de fomento indireto (leis federais de incentivo), "
                "por tipo de obra e por período (Consultas 2 e 4 do relatório).")
    menor, maior = intervalo_de_anos()
    c1, c2 = st.columns([1.4, 1])
    inicio, fim = c1.slider("Anos de emissão do CPB", menor, maior, (2015, maior), key="anos_fomento")
    segmento = c2.radio("Segmento de destinação", list(SEGMENTOS_FOMENTO), horizontal=True, key="segmento_fomento")
    para_salas = SEGMENTOS_FOMENTO[segmento]

    por_tipo = consultar_mostrando_sql(consultas.fomento_por_tipo(inicio, fim, para_salas))
    if por_tipo.empty:
        st.info(f"Nenhum tipo de obra com ao menos {consultas.MINIMO_OBRAS} obras nesse filtro.")
        return
    totais = por_tipo.iloc[0]
    metricas([("obras no filtro", br(totais["total_obras"])), ("com fomento indireto", br(totais["total_com_fomento"])),
              ("parcela com fomento", br(totais["total_pct"], 1) + "%")])
    barras_horizontais(
        por_tipo, "tipo", "pct_com_fomento", f"Obras com fomento indireto por tipo ({inicio} a {fim})",
        "% das obras do tipo", ["tipo:N", alt.Tooltip("obras:Q"),
                                alt.Tooltip("com_fomento:Q", title="com fomento"),
                                alt.Tooltip("pct_com_fomento:Q", title="% com fomento")])

    por_ano = consultar_mostrando_sql(consultas.fomento_por_ano(inicio, fim, para_salas),
                                      "Ver o SQL da evolução anual")
    desenhar(alt.Chart(por_ano, title="Parcela das obras com fomento indireto por ano do CPB").mark_line().encode(
        x=eixo_anos(inicio, fim),
        y=alt.Y("pct_com_fomento:Q", title="% das obras com fomento"),
        tooltip=[alt.Tooltip("ano:Q", format="d"), alt.Tooltip("obras:Q"),
                 alt.Tooltip("com_fomento:Q", title="com fomento"),
                 alt.Tooltip("pct_com_fomento:Q", title="% com fomento")]))
    st.caption(f"Só entram tipos e anos com ao menos {consultas.MINIMO_OBRAS} obras no filtro.")


st.set_page_config(page_title="TP2: cinema brasileiro em dados", layout="wide")
st.title("Cinema brasileiro em dados")
st.caption("DCC011 Introdução a Banco de Dados, UFMG, 2026/2. Trabalho Prático 2: dados abertos da ANCINE.")

if not BANCO.exists():
    st.error(f"O banco `{BANCO}` não foi encontrado. Execute o notebook `tp2.ipynb` primeiro: "
             "ele baixa os dados da ANCINE e cria o `tp2.db` na pasta do app.")
    st.stop()

abas = st.tabs(["Início", "I. Evolução e pandemia", "II. Concentração da produção", "III. Parque exibidor",
                "IV. Fomento indireto"], on_change="rerun", key="aba")
for aba, pagina in zip(abas, [pagina_inicial, evolucao, concentracao, parque_exibidor, fomento]):
    if aba.open:
        with aba:
            pagina()
