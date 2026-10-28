"""Busca de municípios por nome (tolerante a erros), código, DDD e coordenadas."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from functools import lru_cache

from .base import Estado, Municipio, base, normalizar, normalizar_basico

__all__ = [
    "Candidato",
    "Correspondencia",
    "buscar",
    "candidatos",
    "capitais",
    "casar",
    "distancia_km",
    "estado",
    "estados",
    "mais_proximo",
    "municipio",
    "por_ddd",
    "por_uf",
    "proximos",
    "todos",
]


@dataclass(frozen=True)
class Candidato:
    municipio: Municipio
    score: float


@dataclass(frozen=True)
class Correspondencia:
    """Resultado de :func:`casar`.

    ``status`` é ``"exato"``, ``"aproximado"``, ``"ambiguo"`` (mesmo nome em várias UFs)
    ou ``"nao_encontrado"``.
    """

    entrada: str
    municipio: Municipio | None
    score: float
    status: str
    alternativas: tuple[Municipio, ...] = field(default_factory=tuple)

    def __bool__(self) -> bool:
        return self.municipio is not None


# ------------------------------------------------------------------ consultas simples
def todos() -> list[Municipio]:
    return list(base().lista)


def estados() -> list[Estado]:
    return list(base().estados.values())


def estado(chave: str | int) -> Estado:
    """Por sigla (``"PA"``), código IBGE (``15``) ou nome (``"Pará"``)."""
    b = base()
    if isinstance(chave, int) or str(chave).isdigit():
        return b.estado_por_codigo[int(chave)]
    s = str(chave).strip()
    if s.upper() in b.estados:
        return b.estados[s.upper()]
    return b.estado_por_nome[normalizar_basico(s)]


def _uf(uf: str | int | None) -> str | None:
    return None if uf in (None, "") else estado(uf).sigla


def municipio(codigo: int | str) -> Municipio:
    """Por código IBGE de 7 dígitos ou de 6 dígitos (sem DV). Levanta ``KeyError`` se não existir."""
    c = int(str(codigo).strip())
    b = base()
    if c in b.por_codigo:
        return b.por_codigo[c]
    if c in b.por_codigo_6:
        return b.por_codigo_6[c]
    raise KeyError(f"código IBGE desconhecido: {codigo}")


def por_uf(uf: str | int) -> list[Municipio]:
    return list(base().por_uf[_uf(uf)])


def por_ddd(ddd: int | str) -> list[Municipio]:
    return list(base().por_ddd[int(ddd)])


def capitais() -> list[Municipio]:
    return [m for m in base().lista if m.capital]


# ------------------------------------------------------------------------ geografia
def _coords(x: Municipio | int | str | tuple[float, float]) -> tuple[float, float]:
    if isinstance(x, Municipio):
        return x.latitude, x.longitude
    if isinstance(x, tuple):
        return x
    m = municipio(x)
    return m.latitude, m.longitude


def distancia_km(
    a: Municipio | int | str | tuple[float, float], b: Municipio | int | str | tuple[float, float]
) -> float:
    """Distância em linha reta (fórmula de haversine) entre municípios, códigos ou coordenadas."""
    (la1, lo1), (la2, lo2) = _coords(a), _coords(b)
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = p2 - p1, math.radians(lo2 - lo1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0088 * math.asin(math.sqrt(h))


def proximos(
    latitude: float, longitude: float, raio_km: float = 50, limite: int | None = None, uf: str | None = None
) -> list[tuple[Municipio, float]]:
    """Municípios (sede) num raio, do mais perto ao mais longe."""
    sigla = _uf(uf)
    res = [(m, distancia_km((latitude, longitude), m)) for m in base().lista if sigla is None or m.uf == sigla]
    res = sorted((r for r in res if r[1] <= raio_km), key=lambda r: r[1])
    return res[:limite] if limite else res


def mais_proximo(latitude: float, longitude: float, uf: str | None = None) -> Municipio:
    """Município cuja sede está mais perto do ponto."""
    sigla = _uf(uf)
    return min(
        (m for m in base().lista if sigla is None or m.uf == sigla),
        key=lambda m: distancia_km((latitude, longitude), m),
    )


# ----------------------------------------------------------------------------- nomes
def _separar_uf(texto: str) -> list[tuple[str, str | None]]:
    """Interpretações possíveis de ``texto``: com e sem uma UF no final."""
    b = base()
    basico = normalizar_basico(texto)
    tokens = basico.split()
    opcoes: list[tuple[str, str | None]] = []
    if len(tokens) >= 2 and tokens[-1].upper() in b.estados:
        opcoes.append((" ".join(tokens[:-1]), tokens[-1].upper()))
    for nome_estado, e in sorted(b.estado_por_nome.items(), key=lambda kv: -len(kv[0])):
        if basico.endswith(" " + nome_estado) and len(basico) > len(nome_estado) + 1:
            opcoes.append((basico[: -len(nome_estado) - 1], e.sigla))
            break
    opcoes.append((basico, None))
    return [(normalizar(n), uf) for n, uf in opcoes]


def _similaridade(a: str, b: str) -> float:
    direta = SequenceMatcher(None, a, b, autojunk=False).ratio()
    ordenada = SequenceMatcher(None, " ".join(sorted(a.split())), " ".join(sorted(b.split())), autojunk=False).ratio()
    compacta = SequenceMatcher(None, a.replace(" ", ""), b.replace(" ", ""), autojunk=False).ratio()
    return max(direta, ordenada, compacta)


def _aproximados(nome: str, uf: str | None, limite: int) -> list[Candidato]:
    b = base()
    contagem: Counter[int] = Counter()
    for t in {f"  {nome} "[i : i + 3] for i in range(len(nome) + 1)}:
        for idx in b.indice.get(t, ()):
            contagem[idx] += 1
    pre = [b.lista[i] for i, _ in contagem.most_common(60)]
    if uf:
        pre = [m for m in pre if m.uf == uf] or [m for m in b.por_uf[uf]]
    pontuados = [Candidato(m, round(_similaridade(nome, b.normal[m.codigo_ibge]), 4)) for m in pre]
    pontuados.sort(key=lambda c: (-c.score, c.municipio.nome))
    return pontuados[:limite]


def candidatos(nome: str, uf: str | int | None = None, limite: int = 5) -> list[Candidato]:
    """Os ``limite`` municípios mais parecidos com ``nome`` (score de 0 a 1)."""
    sigla = _uf(uf)
    vistos: dict[int, Candidato] = {}
    for texto, uf_texto in _separar_uf(nome):
        alvo = sigla or uf_texto
        if sigla and uf_texto and sigla != uf_texto:
            continue
        for c in _aproximados(texto, alvo, limite):
            atual = vistos.get(c.municipio.codigo_ibge)
            if atual is None or c.score > atual.score:
                vistos[c.municipio.codigo_ibge] = c
    return sorted(vistos.values(), key=lambda c: (-c.score, c.municipio.nome))[:limite]


@lru_cache(maxsize=65_536)
def _casar(nome: str, sigla: str | None, minimo: float) -> Correspondencia:
    b = base()
    interpretacoes = _separar_uf(nome)
    for texto, uf_texto in interpretacoes:
        if sigla and uf_texto and sigla != uf_texto:
            continue
        alvo = sigla or uf_texto
        exatos = b.por_nome.get(texto) or b.por_compacto.get(texto.replace(" ", "")) or []
        if alvo:
            exatos = [m for m in exatos if m.uf == alvo]
        if len(exatos) == 1:
            return Correspondencia(nome, exatos[0], 1.0, "exato")
        if len(exatos) > 1:
            return Correspondencia(nome, None, 1.0, "ambiguo", tuple(exatos))
    apelido = b.apelidos.get(normalizar(nome))
    if apelido and (sigla is None or apelido.uf == sigla):
        return Correspondencia(nome, apelido, 1.0, "exato")
    melhores = candidatos(nome, sigla, limite=5)
    curto = len(normalizar(nome).replace(" ", "")) <= 8
    if not melhores or melhores[0].score < (max(minimo, 0.92) if curto else minimo):
        alternativas = tuple(c.municipio for c in melhores[:3])
        return Correspondencia(nome, None, melhores[0].score if melhores else 0.0, "nao_encontrado", alternativas)
    topo = melhores[0]
    empatados = [c.municipio for c in melhores if c.score == topo.score]
    if len(empatados) > 1 and len({m.uf for m in empatados}) > 1 and not sigla:
        return Correspondencia(nome, None, topo.score, "ambiguo", tuple(empatados))
    return Correspondencia(nome, topo.municipio, topo.score, "aproximado", tuple(c.municipio for c in melhores[1:3]))


def casar(nome: str, uf: str | int | None = None, minimo: float = 0.85) -> Correspondencia:
    """Encontra o município oficial que corresponde a um nome digitado de qualquer jeito.

    Aceita acentos faltando, abreviações (``Sta.``, ``S.``, ``N. Sra.``), hífens e apóstrofos,
    a UF no próprio texto (``"Bragança - PA"``, ``"Bragança/PA"``, ``"Bragança, Pará"``) e
    pequenos erros de digitação.
    """
    return _casar(nome.strip(), _uf(uf), minimo)


def buscar(nome: str, uf: str | int | None = None, minimo: float = 0.85) -> Municipio | None:
    """Atalho para :func:`casar` que devolve só o município (ou ``None`` se não achar ou for ambíguo)."""
    return casar(nome, uf, minimo).municipio
