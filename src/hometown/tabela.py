"""Enriquecimento de tabelas: adiciona o código IBGE a planilhas com nomes de cidades."""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable
from typing import Any

from .busca import casar

__all__ = ["adicionar_ibge", "casar_linhas", "COLUNAS"]

COLUNAS = ("codigo_ibge", "municipio_oficial", "uf_oficial", "score", "status")


def _resultado(nome: Any, uf: Any, minimo: float) -> dict[str, Any]:
    if nome is None or (isinstance(nome, float) and nome != nome) or not str(nome).strip():
        return dict.fromkeys(COLUNAS) | {"status": "vazio"}
    try:
        c = casar(str(nome), str(uf).strip() if uf not in (None, "") and uf == uf else None, minimo)
    except KeyError:  # UF inválida
        c = casar(str(nome), None, minimo)
    m = c.municipio
    return {
        "codigo_ibge": m.codigo_ibge if m else None,
        "municipio_oficial": m.nome if m else None,
        "uf_oficial": m.uf if m else None,
        "score": c.score,
        "status": c.status,
    }


def casar_linhas(
    linhas: Iterable[dict[str, Any]],
    coluna: str,
    coluna_uf: str | None = None,
    uf: str | None = None,
    minimo: float = 0.85,
) -> list[dict[str, Any]]:
    """Recebe dicts (ex.: de ``csv.DictReader``) e devolve cópias com as colunas de :data:`COLUNAS`."""
    saida = []
    for linha in linhas:
        valor_uf = linha.get(coluna_uf) if coluna_uf else uf
        saida.append({**linha, **_resultado(linha.get(coluna), valor_uf, minimo)})
    return saida


def adicionar_ibge(
    df: Any, coluna: str, coluna_uf: str | None = None, uf: str | None = None, minimo: float = 0.85
) -> Any:
    """Devolve uma cópia do ``pandas.DataFrame`` com ``codigo_ibge``, ``municipio_oficial``, ``uf_oficial``,
    ``score`` e ``status``. Nomes repetidos são resolvidos uma única vez (cache)."""
    import pandas as pd

    ufs = df[coluna_uf] if coluna_uf else pd.Series([uf] * len(df), index=df.index)
    resultados = [_resultado(n, u, minimo) for n, u in zip(df[coluna], ufs)]
    extra = pd.DataFrame(resultados, index=df.index, columns=list(COLUNAS))
    extra["codigo_ibge"] = extra["codigo_ibge"].astype("Int64")
    return pd.concat([df.drop(columns=[c for c in COLUNAS if c in df.columns]), extra], axis=1)


def ler_csv(texto: str) -> tuple[list[dict[str, str]], str]:
    amostra = texto[:5000]
    try:
        delimitador = csv.Sniffer().sniff(amostra, delimiters=",;\t|").delimiter
    except csv.Error:
        delimitador = ","
    return list(csv.DictReader(io.StringIO(texto), delimiter=delimitador)), delimitador
