"""hometown — os municípios brasileiros offline: nome ↔ código IBGE, DDD, coordenadas e busca."""

__version__ = "0.1.0"

from .base import Estado, Municipio, normalizar
from .busca import (
    Candidato,
    Correspondencia,
    buscar,
    candidatos,
    capitais,
    casar,
    distancia_km,
    estado,
    estados,
    mais_proximo,
    municipio,
    por_ddd,
    por_uf,
    proximos,
    todos,
)
from .tabela import adicionar_ibge, casar_linhas

__all__ = [
    "__version__",
    "Candidato",
    "Correspondencia",
    "Estado",
    "Municipio",
    "adicionar_ibge",
    "buscar",
    "candidatos",
    "capitais",
    "casar",
    "casar_linhas",
    "distancia_km",
    "estado",
    "estados",
    "mais_proximo",
    "municipio",
    "normalizar",
    "por_ddd",
    "por_uf",
    "proximos",
    "todos",
]
