import csv
import io

import pytest

import hometown as mu
from hometown.cli import main


def test_casar_linhas():
    linhas = [{"cidade": "Braganca", "uf": "PA"}, {"cidade": "", "uf": "PA"}, {"cidade": "Xyzabc", "uf": "SP"}]
    out = mu.casar_linhas(linhas, "cidade", "uf")
    assert out[0]["codigo_ibge"] == 1501709 and out[0]["status"] == "exato"
    assert out[1]["status"] == "vazio"
    assert out[2]["status"] == "nao_encontrado"


def test_adicionar_ibge_pandas():
    pd = pytest.importorskip("pandas")
    df = pd.DataFrame({"cidade": ["Belém", "Belém", "Sta Barbara D Oeste", None], "uf": ["PA", "PB", "SP", "SP"]})
    out = mu.adicionar_ibge(df, "cidade", coluna_uf="uf")
    assert list(out["uf_oficial"][:3]) == ["PA", "PB", "SP"]
    assert str(out["codigo_ibge"].dtype) == "Int64"
    assert out["status"].iloc[3] == "vazio"


def test_cli_tabela(tmp_path, capsys):
    f = tmp_path / "dados.csv"
    f.write_text("cidade;uf;valor\nBraganca;PA;10\nSao Paulo;SP;20\n", encoding="utf-8")
    saida = tmp_path / "saida.csv"
    assert main(["tabela", str(f), "--coluna", "cidade", "--coluna-uf", "uf", "-o", str(saida)]) == 0
    linhas = list(csv.DictReader(io.StringIO(saida.read_text(encoding="utf-8")), delimiter=";"))
    assert [linha["codigo_ibge"] for linha in linhas] == ["1501709", "3550308"]
    assert "exato: 2" in capsys.readouterr().err


def test_cli_buscar_e_codigo(capsys):
    assert main(["buscar", "braganca", "pa"]) == 0
    assert "1501709" in capsys.readouterr().out
    assert main(["buscar", "Belém"]) == 1
    assert "mais de uma UF" in capsys.readouterr().out
    assert main(["codigo", "150170", "--json"]) == 0
    assert '"nome": "Bragança"' in capsys.readouterr().out
    assert main(["ddd", "91"]) == 0
    assert main(["proximo", "-1.05", "-46.77"]) == 0
