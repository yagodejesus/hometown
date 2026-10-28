<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo-dark.svg">
    <img src="assets/logo.svg" alt="hometown" width="420">
  </picture>
</p>

<p align="center">
  <a href="https://github.com/yagodejesus/hometown/actions/workflows/ci.yml"><img src="https://github.com/yagodejesus/hometown/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/hometown/"><img src="https://img.shields.io/pypi/v/hometown.svg" alt="PyPI"></a>
  <a href="https://pypi.org/project/hometown/"><img src="https://img.shields.io/pypi/pyversions/hometown.svg" alt="Python"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="MIT"></a>
</p>

**Os 5.571 municípios brasileiros, offline: de nomes digitados de qualquer jeito ao código IBGE certo.**

> 🇺🇸 *Offline lookup of all Brazilian municipalities: turn messy city names ("Sta Barbara D Oeste", "BRAGANCA PA") into official IBGE codes, with state, area code, coordinates and typo-tolerant matching. Zero dependencies.*

Quem já cruzou dados de saúde, educação, eleições ou vendas por cidade conhece o problema: uma planilha tem `Sta Barbara D Oeste`, outra `SANTA BARBARA DOESTE`, o IBGE tem `Santa Bárbara d'Oeste` — e existem cinco `Bom Jesus` em estados diferentes. O `hometown` resolve isso sem internet e sem chave de API.

```python
import hometown

hometown.buscar("Sta Barbara D Oeste")  # Municipio(nome="Santa Bárbara d'Oeste", uf="SP", codigo_ibge=3545803, ...)
hometown.buscar("BRAGANCA - PA").codigo_ibge  # 1501709
hometown.municipio(150170).nome  # 'Bragança'  (código de 6 dígitos, como no DATASUS)

r = hometown.casar("Belém")
r.status  # 'ambiguo'
[str(m) for m in r.alternativas]  # ['Belém/PA', 'Belém/PB', 'Belém/AL']
```

## Destaques

- **Offline e sem dependências**: a base completa (nome, UF, código IBGE de 6 e 7 dígitos, código SIAFI, DDD, coordenadas da sede, fuso horário e capital) vem dentro do pacote e carrega em ~0,1 s.
- **Entende nomes do mundo real**: sem acento, em maiúsculas, com hífen ou apóstrofo, abreviações (`Sta.`, `S.`, `N. Sra.`, `Mal.`, `Pres.`), apelidos (`Floripa`, `Sampa`, `BH`) e nomes antigos (`Embu`, `Parati`, `Moji Mirim`).
- **UF em qualquer formato**: `Bragança - PA`, `Bragança/PA`, `Bragança (PA)`, `Bragança, Pará` ou num parâmetro separado (`"PA"`, `15` ou `"Pará"`).
- **Honesto quando não sabe**: nomes que existem em várias UFs voltam como `ambiguo`, com as opções; erros de digitação voltam como `aproximado`, com o score; nada é "chutado" abaixo do limiar.
- **Feito para planilhas**: enriquece um `DataFrame` ou um CSV inteiro com uma linha, resolvendo cada nome repetido uma vez só.
- **Geografia**: distância entre municípios, município mais próximo de uma coordenada e municípios num raio.

## Instalação

```bash
pip install hometown
pip install "hometown[pandas]"   # para adicionar_ibge() em DataFrames
```

## Planilhas e DataFrames

```python
import pandas as pd
import hometown

df = pd.read_csv("atendimentos.csv")  # colunas "cidade" e "uf", escritas de qualquer jeito
df = hometown.adicionar_ibge(df, "cidade", coluna_uf="uf")
```

Novas colunas: `codigo_ibge`, `municipio_oficial`, `uf_oficial`, `score` (0–1) e `status` (`exato`, `aproximado`, `ambiguo`, `nao_encontrado` ou `vazio`). Filtre `status != "exato"` para revisar só o que precisa de atenção.

Pela linha de comando:

```bash
hometown tabela atendimentos.csv --coluna cidade --coluna-uf uf -o atendimentos_ibge.csv
# hometown: aproximado: 37, exato: 9.912, nao_encontrado: 4
```

## Linha de comando

```bash
hometown buscar braganca pa
# 1501709  Bragança/PA  (Pará, Norte) · DDD 91  [exato, score 1.00]

hometown buscar "Belém"          # lista as opções quando o nome é ambíguo
hometown codigo 150170 --json    # todos os dados de um código (6 ou 7 dígitos)
hometown ddd 91                  # municípios atendidos por um DDD
hometown proximo -1.05 -46.77    # município mais próximo de uma coordenada
```

## API

| Função | O que faz |
|---|---|
| `buscar(nome, uf=None, minimo=0.85)` | `Municipio` ou `None` (não achou ou é ambíguo) |
| `casar(nome, uf=None, minimo=0.85)` | `Correspondencia` com `municipio`, `score`, `status` e `alternativas` |
| `candidatos(nome, uf=None, limite=5)` | os mais parecidos, com score — bom para autocompletar |
| `municipio(codigo)` | por código IBGE de 7 ou 6 dígitos |
| `por_uf(uf)`, `por_ddd(ddd)`, `capitais()`, `todos()` | listas |
| `estado(sigla_codigo_ou_nome)`, `estados()` | as 27 UFs, com região |
| `distancia_km(a, b)` | entre municípios, códigos ou `(lat, lon)` |
| `mais_proximo(lat, lon, uf=None)`, `proximos(lat, lon, raio_km=50)` | busca geográfica pelas sedes |
| `adicionar_ibge(df, coluna, coluna_uf=None, uf=None)` | enriquece um `pandas.DataFrame` |
| `normalizar(texto)` | a forma canônica usada nas comparações |

Cada `Municipio` tem `codigo_ibge`, `codigo_6`, `nome`, `uf`, `estado`, `regiao`, `latitude`, `longitude`, `capital`, `ddd`, `fuso_horario`, `codigo_siafi` e `to_dict()`.

## Como a busca funciona

1. O texto é normalizado (sem acentos, minúsculas, pontuação vira espaço) e as abreviações são expandidas.
2. Se houver uma UF no fim do texto, as duas leituras são testadas — assim `Bom Jesus do Tocantins` não vira "Bom Jesus do" no Tocantins.
3. Correspondências exatas vencem. Sem elas, um índice de trigramas seleciona candidatos e a similaridade é calculada por três medidas (direta, por palavras ordenadas e sem espaços).
4. Nomes curtos precisam de similaridade maior (0,92) para não confundir `Belen` com outro município.

## Dados

Os dados vêm do projeto [kelvins/hometown-brasileiros](https://github.com/kelvins/hometown-brasileiros) (MIT), compilado a partir de fontes públicas do IBGE. Veja [`NOTICE.md`](src/hometown/dados/NOTICE.md). As coordenadas são as da **sede** do município, não o centro geográfico do território.

## Limitações

- Distritos, bairros e localidades não são municípios e não estão na base.
- A lista de apelidos e nomes antigos é pequena de propósito; contribuições são bem-vindas.

## Desenvolvimento

```bash
git clone https://github.com/yagodejesus/hometown && cd hometown
pip install -e ".[dev]"
pytest && ruff check .
```

## Licença

MIT © Yago de Jesus Martins. Dados: MIT © Kelvin S. do Prado / IBGE.
