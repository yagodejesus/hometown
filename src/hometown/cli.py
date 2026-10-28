"""Linha de comando: ``hometown --help``."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from . import __version__
from .busca import candidatos, casar, mais_proximo, municipio, por_ddd
from .tabela import COLUNAS, casar_linhas, ler_csv


def _mostrar(m, extra: str = "") -> None:
    print(f"{m.codigo_ibge}  {m.nome}/{m.uf}  ({m.estado.nome}, {m.regiao}) · DDD {m.ddd}{extra}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="hometown", description="Municípios brasileiros: nome ↔ código IBGE, offline.")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="comando", required=True)

    b = sub.add_parser("buscar", help="encontra um município pelo nome")
    b.add_argument("nome", nargs="+")
    b.add_argument("--uf")
    b.add_argument("--json", action="store_true")

    c = sub.add_parser("codigo", help="dados de um código IBGE (6 ou 7 dígitos)")
    c.add_argument("codigo")
    c.add_argument("--json", action="store_true")

    d = sub.add_parser("ddd", help="municípios de um DDD")
    d.add_argument("ddd", type=int)

    pr = sub.add_parser("proximo", help="município mais próximo de uma coordenada")
    pr.add_argument("latitude", type=float)
    pr.add_argument("longitude", type=float)

    t = sub.add_parser("tabela", help="adiciona o código IBGE a um CSV")
    t.add_argument("arquivo")
    t.add_argument("--coluna", required=True, help="coluna com o nome do município")
    t.add_argument("--coluna-uf", help="coluna com a UF")
    t.add_argument("--uf", help="UF fixa para todas as linhas")
    t.add_argument("--minimo", type=float, default=0.85, help="similaridade mínima (0–1)")
    t.add_argument("-o", "--saida", help="CSV de saída (padrão: stdout)")

    a = p.parse_args(argv)

    if a.comando == "buscar":
        nome = " ".join(a.nome)
        r = casar(nome, a.uf)
        if a.json:
            print(
                json.dumps(
                    {
                        "status": r.status,
                        "score": r.score,
                        "municipio": r.municipio.to_dict() if r.municipio else None,
                        "alternativas": [m.to_dict() for m in r.alternativas],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0 if r else 1
        if r.municipio:
            _mostrar(r.municipio, f"  [{r.status}, score {r.score:.2f}]")
            return 0
        if r.status == "ambiguo":
            print(f'"{nome}" existe em mais de uma UF — informe a UF:')
            for m in r.alternativas:
                _mostrar(m)
        else:
            print(f'Nenhum município corresponde a "{nome}". Mais parecidos:')
            for cand in candidatos(nome, a.uf, 3):
                _mostrar(cand.municipio, f"  [score {cand.score:.2f}]")
        return 1

    if a.comando == "codigo":
        try:
            m = municipio(a.codigo)
        except (KeyError, ValueError):
            print(f"Código IBGE desconhecido: {a.codigo}", file=sys.stderr)
            return 1
        print(json.dumps(m.to_dict(), ensure_ascii=False, indent=2)) if a.json else _mostrar(m)
        return 0

    if a.comando == "ddd":
        for m in sorted(por_ddd(a.ddd), key=lambda m: m.nome):
            _mostrar(m)
        return 0

    if a.comando == "proximo":
        _mostrar(mais_proximo(a.latitude, a.longitude))
        return 0

    bruto = Path(a.arquivo).read_bytes()
    try:
        texto = bruto.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = bruto.decode("cp1252")
    linhas, delimitador = ler_csv(texto)
    if linhas and a.coluna not in linhas[0]:
        print(f"Coluna '{a.coluna}' não encontrada. Colunas: {', '.join(linhas[0])}", file=sys.stderr)
        return 2
    saida = casar_linhas(linhas, a.coluna, a.coluna_uf, a.uf, a.minimo)
    destino = open(a.saida, "w", encoding="utf-8", newline="") if a.saida else sys.stdout
    campos = list(linhas[0].keys()) + [c for c in COLUNAS if c not in linhas[0]] if linhas else list(COLUNAS)
    w = csv.DictWriter(destino, fieldnames=campos, delimiter=delimitador, lineterminator="\n")
    w.writeheader()
    w.writerows(saida)
    if a.saida:
        destino.close()
    status = {}
    for linha in saida:
        status[linha["status"]] = status.get(linha["status"], 0) + 1
    print("hometown: " + ", ".join(f"{k}: {v}" for k, v in sorted(status.items())), file=sys.stderr)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
