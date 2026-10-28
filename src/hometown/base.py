"""Modelos e carregamento da base de municípios (IBGE)."""

from __future__ import annotations

import csv
import gzip
import io
import re
import unicodedata
from collections import defaultdict
from dataclasses import asdict, dataclass
from functools import lru_cache
from importlib import resources
from typing import Any

__all__ = ["Estado", "Municipio", "Base", "base", "normalizar", "normalizar_basico"]


@dataclass(frozen=True, slots=True)
class Estado:
    codigo: int
    sigla: str
    nome: str
    regiao: str
    latitude: float
    longitude: float

    def __str__(self) -> str:
        return self.nome


@dataclass(frozen=True, slots=True)
class Municipio:
    codigo_ibge: int
    nome: str
    uf: str
    latitude: float
    longitude: float
    capital: bool
    ddd: int
    fuso_horario: str
    codigo_siafi: str

    @property
    def codigo_6(self) -> int:
        """Código IBGE de 6 dígitos (sem o dígito verificador), usado pelo DATASUS e outros sistemas."""
        return self.codigo_ibge // 10

    @property
    def codigo_uf(self) -> int:
        return self.codigo_ibge // 100_000

    @property
    def estado(self) -> Estado:
        return base().estados[self.uf]

    @property
    def regiao(self) -> str:
        return self.estado.regiao

    def __str__(self) -> str:
        return f"{self.nome}/{self.uf}"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.update(codigo_6=self.codigo_6, estado=self.estado.nome, regiao=self.regiao)
        return d


# Abreviações comuns em cadastros ("Sta. Bárbara", "S. José", "N. Sra.", "Mal. Deodoro")
ABREVIACOES = {
    "sta": "santa",
    "sto": "santo",
    "s": "sao",
    "sj": "sao jose",
    "n": "nossa",
    "nsa": "nossa",
    "ns": "nossa senhora",
    "sra": "senhora",
    "sr": "senhor",
    "mal": "marechal",
    "pres": "presidente",
    "pdte": "presidente",
    "gov": "governador",
    "dr": "doutor",
    "cel": "coronel",
    "sen": "senador",
    "dep": "deputado",
    "eng": "engenheiro",
    "prof": "professor",
    "fco": "francisco",
    "jd": "jardim",
    "vl": "vila",
    "gal": "general",
    "gen": "general",
    "tte": "tenente",
    "cap": "capitao",
    "pe": "padre",
    "bel": "belo",
    "cach": "cachoeira",
    "mte": "monte",
    "fca": "francisca",
    "moji": "mogi",
}

# Apelidos e nomes antigos muito usados → (nome oficial, UF)
APELIDOS = {
    "sampa": ("São Paulo", "SP"),
    "floripa": ("Florianópolis", "SC"),
    "bh": ("Belo Horizonte", "MG"),
    "poa": ("Porto Alegre", "RS"),
    "bsb": ("Brasília", "DF"),
    "cwb": ("Curitiba", "PR"),
    "ssa": ("Salvador", "BA"),
    "sjc": ("São José dos Campos", "SP"),
    "sjrp": ("São José do Rio Preto", "SP"),
    "embu": ("Embu das Artes", "SP"),
    "parati": ("Paraty", "RJ"),
}


def normalizar_basico(texto: str) -> str:
    """Minúsculas, sem acentos e com pontuação trocada por espaço."""
    s = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s).split())


def normalizar(texto: str) -> str:
    """Forma canônica para comparação: ``"Sta. Bárbara D'Oeste"`` → ``"santa barbara d oeste"``."""
    return " ".join(ABREVIACOES.get(t, t) for t in normalizar_basico(texto).split())


def _trigramas(s: str) -> set[str]:
    p = f"  {s} "
    return {p[i : i + 3] for i in range(len(p) - 2)}


class Base:
    def __init__(self) -> None:
        pacote = resources.files("hometown") / "dados"
        self.estados: dict[str, Estado] = {}
        with (pacote / "estados.csv").open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                e = Estado(
                    int(r["codigo"]), r["sigla"], r["nome"], r["regiao"], float(r["latitude"]), float(r["longitude"])
                )
                self.estados[e.sigla] = e
        self.estado_por_codigo = {e.codigo: e for e in self.estados.values()}
        self.estado_por_nome = {normalizar_basico(e.nome): e for e in self.estados.values()}

        bruto = gzip.decompress((pacote / "municipios.csv.gz").read_bytes()).decode("utf-8")
        self.lista: list[Municipio] = []
        for r in csv.DictReader(io.StringIO(bruto)):
            self.lista.append(
                Municipio(
                    codigo_ibge=int(r["codigo_ibge"]),
                    nome=r["nome"],
                    uf=r["uf"],
                    latitude=float(r["latitude"]),
                    longitude=float(r["longitude"]),
                    capital=r["capital"] == "1",
                    ddd=int(r["ddd"]),
                    fuso_horario=r["fuso_horario"],
                    codigo_siafi=r["codigo_siafi"],
                )
            )
        self.por_codigo = {m.codigo_ibge: m for m in self.lista}
        self.por_codigo_6 = {m.codigo_6: m for m in self.lista}
        self.por_nome: dict[str, list[Municipio]] = defaultdict(list)
        self.por_compacto: dict[str, list[Municipio]] = defaultdict(list)
        self.por_uf: dict[str, list[Municipio]] = defaultdict(list)
        self.por_ddd: dict[int, list[Municipio]] = defaultdict(list)
        self.normal: dict[int, str] = {}
        self.indice: dict[str, list[int]] = defaultdict(list)
        for i, m in enumerate(self.lista):
            n = normalizar(m.nome)
            self.normal[m.codigo_ibge] = n
            self.por_nome[n].append(m)
            self.por_compacto[n.replace(" ", "")].append(m)
            self.por_uf[m.uf].append(m)
            self.por_ddd[m.ddd].append(m)
            for t in _trigramas(n):
                self.indice[t].append(i)
        self.apelidos: dict[str, Municipio] = {}
        for apelido, (nome, uf) in APELIDOS.items():
            achados = [m for m in self.por_nome.get(normalizar(nome), []) if m.uf == uf]
            if achados:
                self.apelidos[apelido] = achados[0]


@lru_cache(maxsize=1)
def base() -> Base:
    """Carrega a base uma única vez (≈ 50 ms)."""
    return Base()
