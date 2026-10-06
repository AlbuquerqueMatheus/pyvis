"""Motor do PyVis: executa o código do aluno e grava cada passo da execução."""

from .avaliador import avaliar
from .estrutura import analisar
from .rastreador import calcular_voltas, rastrear

__all__ = ["analisar", "api", "avaliar", "calcular_voltas", "executar", "executar_json", "rastrear"]

_DA_API = ("api", "executar", "executar_json")


def __getattr__(nome):
    # A API (atividade, modelos, narrador e diário) só carrega quando alguém
    # pede: quem só valida eventos não precisa dos modelos de concepção.
    if nome in _DA_API:
        import importlib

        api = importlib.import_module(__name__ + ".api")
        return api if nome == "api" else getattr(api, nome)
    raise AttributeError(f"module {__name__!r} has no attribute {nome!r}")
