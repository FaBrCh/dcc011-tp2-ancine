import subprocess
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

CSS = """
@page { size: A4; margin: 14mm 11mm 14mm 11mm; }
body { font-size: 10pt; margin: 0 !important; padding: 0 !important; }
.jp-RenderedHTMLCommon { padding-right: 0 !important; }
.jp-InputPrompt, .jp-OutputPrompt { display: none !important; }
.jp-Cell { padding: 2px 0 !important; }
pre, code, .jp-RenderedText pre, .CodeMirror pre, .highlight pre {
    white-space: pre-wrap !important; word-break: break-word !important; font-size: 7.6pt !important;
}
.jp-RenderedHTMLCommon table { font-size: 7.4pt !important; table-layout: auto; }
.jp-RenderedHTMLCommon td, .jp-RenderedHTMLCommon th { padding: 1px 4px !important; }
.jp-RenderedImage img, .jp-RenderedSVG svg, .jp-RenderedSVG img { max-width: 100% !important; height: auto !important; }
.jp-OutputArea-output { break-inside: avoid; }
@page paisagem { size: A4 landscape; margin: 6mm; }
.diagrama-er, .diagrama-relacional { page: paisagem; }
.diagrama-er svg, .diagrama-relacional svg { width: 100%; height: auto; max-height: 192mm; }
"""


def exportar(notebook):
    notebook = Path(notebook).resolve()
    with tempfile.TemporaryDirectory() as pasta:
        subprocess.run([sys.executable, "-m", "jupyter", "nbconvert", "--to", "html", str(notebook),
                        "--output-dir", pasta, "--output", "relatorio"], check=True)
        html = Path(pasta) / "relatorio.html"
        with sync_playwright() as p:
            navegador = p.chromium.launch()
            pagina = navegador.new_page()
            pagina.goto(html.as_uri(), wait_until="networkidle")
            pagina.add_style_tag(content=CSS)
            pagina.pdf(path=str(notebook.with_suffix(".pdf")), format="A4", print_background=True,
                       prefer_css_page_size=True)
            navegador.close()


if __name__ == "__main__":
    exportar(sys.argv[1] if len(sys.argv) > 1 else "tp2.ipynb")
