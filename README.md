# Cinema brasileiro em dados (TP2 de Banco de Dados)

Trabalho Prático 2 de DCC011 Introdução a Banco de Dados (turma TB, UFMG, 2026/2). Usa os dados abertos da ANCINE sobre obras audiovisuais, empresas do setor e salas de exibição. O banco é modelado e carregado no SQLite, consultado em SQL e visualizado num app Streamlit.

**App online:** https://tp2-cinema-ancine.streamlit.app

## Prazos

| Quando | O quê |
|:---|:---|
| qua 18/11, 23:59 | Entrega no Moodle: .zip com `tp2.ipynb` e `tp2.pdf` |
| seg 23/11 | Apresentação em sala: 10 min mais 3 de perguntas |

## O que tem aqui

| Arquivo | O que é |
|:---|:---|
| `tp2.ipynb` | O relatório, nas 7 seções do template: carga, normalização, diagramas e as 10 consultas com análises |
| `tp2.pdf` | O notebook executado e exportado em PDF (vai na entrega) |
| `app.py` e `consultas.py` | O app Streamlit (vale até 20% extra). Todo o SQL fica em `consultas.py` |
| `test_consultas.py` | Confere que o app reproduz os números do relatório |
| `diagramas/` | Diagrama ER e diagrama relacional (SVG e PNG) |
| `dados/` | Os arquivos da ANCINE baixados em 03/11/2026 |
| `enunciado.pdf`, `template-professor.ipynb`, `proposta.pdf` | Enunciado, template do professor e a proposta enviada em 28/10 |
| `exportar_pdf.py` | Gera o `tp2.pdf` a partir do notebook |

## Como rodar

Precisa de Python 3.11 ou mais novo e do Graphviz instalado no sistema (`brew install graphviz` no Mac, `sudo apt install graphviz` no Ubuntu; no Windows, o instalador de graphviz.org).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
jupyter nbconvert --to notebook --execute --inplace tp2.ipynb
streamlit run app.py
```

O notebook cria o banco `tp2.db` na pasta, e o app lê esse banco. Se o `tp2.db` não existir, o próprio app executa o notebook para criá-lo na primeira visita (leva cerca de um minuto). Também dá para abrir o `tp2.ipynb` no Jupyter ou no VS Code e rodar célula por célula.

Para rodar os testes: `python -m unittest test_consultas`.

Para gerar o PDF: `playwright install chromium` uma vez, depois `python exportar_pdf.py`.

## App online

O app roda no Streamlit Community Cloud a partir da branch `main`: todo push na `main` atualiza o app. O `packages.txt` instala o Graphviz que o notebook usa ao montar o banco. Sem visitas por 12 horas, o app hiberna; quem abrir o link clica em "Yes, get this app back up!" e espera um ou dois minutos.

## Sobre os dados

As análises citam números da carga de 03/11/2026, e os arquivos dessa carga estão em `dados/`. O notebook só baixa da ANCINE o que não estiver nessa pasta. Não apague `dados/`: a ANCINE atualiza os arquivos todo mês, e uma carga nova muda as contagens e deixa os textos das análises errados.

## Como contribuir

1. Clone o repositório e crie uma branch com o seu nome: `git checkout -b caetano`.
2. Faça a sua parte, rode o notebook do início ao fim e rode os testes.
3. Abra um pull request e avise no grupo.

O `.ipynb` dá conflito fácil no Git. Antes de editar o notebook, avise no grupo para duas pessoas não mexerem nele ao mesmo tempo. O PDF final é gerado uma vez só, por uma pessoa, depois que tudo estiver fechado.

## O que falta

- [ ] Seção 2: nome e matrícula de todos os membros
- [ ] Seção 7: autoavaliação. Cada membro descreve o que realmente fez
- [ ] Cada membro revisar a parte que vai apresentar e ajustar o que achar melhor
- [ ] Citar o link do app na seção 6.6 do notebook
- [ ] Slides da apresentação
- [ ] Gerar o PDF final e enviar o .zip no Moodle até 18/11, 23:59
