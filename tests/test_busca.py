import pytest

import hometown as mu


@pytest.mark.parametrize(
    "entrada",
    ["Bragança", "BRAGANCA PA", "Braganca - PA", "Bragança/PA", "bragança (pa)", "Bragança, Pará", "  braganca-pa "],
)
def test_variacoes_de_escrita_com_uf(entrada):
    r = mu.casar(entrada, None if "pa" in entrada.lower() else "PA")
    assert r.status == "exato" and r.municipio.codigo_ibge == 1501709


@pytest.mark.parametrize(
    "entrada,oficial",
    [
        ("Sta Barbara D Oeste", "Santa Bárbara d'Oeste"),
        ("S. Jose dos Campos", "São José dos Campos"),
        ("N. Sra. do Socorro", "Nossa Senhora do Socorro"),
        ("Mal. Deodoro", "Marechal Deodoro"),
        ("Xique Xique", "Xique-Xique"),
        ("Moji Mirim", "Mogi Mirim"),
        ("Olho d Agua das Flores", "Olho d'Água das Flores"),
        ("Floripa", "Florianópolis"),
        ("Parati", "Paraty"),
    ],
)
def test_abreviacoes_apelidos_e_nomes_antigos(entrada, oficial):
    assert mu.buscar(entrada).nome == oficial


def test_erros_de_digitacao():
    r = mu.casar("Sao Jose do Rio Preeto")
    assert r.status == "aproximado" and r.municipio.nome == "São José do Rio Preto"
    assert mu.buscar("Ananindeuaa", "PA").nome == "Ananindeua"


def test_ambiguo_sem_uf_e_resolvido_com_uf():
    r = mu.casar("Belém")
    assert r.status == "ambiguo" and r.municipio is None
    assert {m.uf for m in r.alternativas} >= {"PA", "PB", "AL"}
    assert mu.buscar("Belém", "PA").codigo_ibge == 1501402
    assert mu.buscar("Belém", 15).uf == "PA"
    assert mu.buscar("Belém", "Pará").uf == "PA"


def test_nome_que_termina_com_nome_de_estado():
    r = mu.casar("Bom Jesus do Tocantins", "PA")
    assert r.municipio.uf == "PA"


def test_nao_encontrado_traz_sugestoes():
    r = mu.casar("Cidade Que Nao Existe")
    assert r.status == "nao_encontrado" and not r
    assert len(r.alternativas) <= 3


def test_nomes_curtos_exigem_mais_semelhanca():
    assert mu.buscar("Belen") is None  # não "chuta" um município parecido


def test_candidatos_ordenados():
    c = mu.candidatos("sao jose", "SC", limite=3)
    assert c[0].municipio.nome == "São José" and c[0].score == 1.0
    assert [x.score for x in c] == sorted((x.score for x in c), reverse=True)


def test_codigos_de_6_e_7_digitos():
    assert mu.municipio(1501709).nome == "Bragança"
    assert mu.municipio("150170").nome == "Bragança"
    assert mu.municipio(1501709).codigo_6 == 150170
    with pytest.raises(KeyError):
        mu.municipio(9999999)


def test_dados_do_municipio():
    m = mu.municipio(1501402)
    assert (m.nome, m.uf, m.capital, m.ddd, m.regiao, m.estado.nome) == ("Belém", "PA", True, 91, "Norte", "Pará")
    assert m.to_dict()["codigo_6"] == 150140
    assert str(m) == "Belém/PA"


def test_listas():
    assert len(mu.todos()) >= 5570
    assert len(mu.capitais()) == 27
    assert len(mu.estados()) == 27
    assert all(m.uf == "PA" for m in mu.por_uf("pa"))
    assert {m.uf for m in mu.por_ddd(91)} == {"PA"}
    assert mu.estado("Pará").sigla == "PA" and mu.estado(15).sigla == "PA"


def test_geografia():
    belem, sp = mu.buscar("Belém", "PA"), mu.buscar("São Paulo", "SP")
    assert 2400 < mu.distancia_km(belem, sp) < 2550
    assert mu.distancia_km(belem, belem) == 0
    assert mu.mais_proximo(-1.0536, -46.7656).nome == "Bragança"
    perto = mu.proximos(belem.latitude, belem.longitude, raio_km=30)
    assert perto[0][0] == belem and all(km <= 30 for _, km in perto)
    assert any(m.nome == "Ananindeua" for m, _ in perto)


def test_normalizar():
    assert mu.normalizar("Sta. Bárbara D'Oeste") == "santa barbara d oeste"


def test_desempenho_em_lote():
    import time

    nomes = [m.nome.upper() for m in mu.todos()] * 2
    t = time.perf_counter()
    achados = sum(1 for n in nomes if mu.casar(n).status in ("exato", "ambiguo"))
    assert achados == len(nomes)
    assert time.perf_counter() - t < 10
