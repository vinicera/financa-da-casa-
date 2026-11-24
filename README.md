# Finança da Casa

Controle financeiro para casas compartilhadas, feito em **Python**. Com ele dá
para organizar o dinheiro do mês em **caixinhas** (Aluguel, Mercado, Reserva…),
lançar **gastos** e **entradas**, acompanhar **parcelamentos** e ver quanto do
dinheiro ainda está **livre** no ciclo e se os gastos estão no ritmo.

Tecnologias: Python 3.11+, FastAPI (servidor web e API), Jinja2 (páginas HTML)
e pytest (testes). Os dados ficam num arquivo JSON.

## Como rodar

```bash
# 1. Criar e ativar o ambiente virtual
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux / macOS

# 2. Instalar as dependências
pip install -r requirements-dev.txt

# 3. (Opcional) Carregar dados de exemplo
python -m app.exemplo

# 4. Subir o servidor
uvicorn app.main:app --reload
```

Depois abra <http://127.0.0.1:8000>. A documentação interativa da API fica em
<http://127.0.0.1:8000/docs>.

Para rodar os testes:

```bash
pytest
```

## Funcionalidades

| Tela | O que faz |
|---|---|
| **Resumo** | Dinheiro livre do ciclo, quanto dá para gastar por dia, ritmo de gasto, situação de cada caixinha e próximos vencimentos. |
| **Gastos** | Lança, exclui e ordena gastos (data, valor ou descrição). Navega entre ciclos. |
| **Entradas** | Registra renda e entradas extras do ciclo. |
| **Caixinhas** | Cria caixinhas de três tipos: conta fixa, variável e reserva. |
| **Parcelas** | Cadastra compras parceladas, mostra o cronograma e marca parcelas como pagas. |
| **Desfazer** | Botão no topo que desfaz a última ação, quantas vezes for preciso. |

**Ciclo financeiro:** o "mês" pode começar em qualquer dia (por exemplo, no dia
do salário). Com início no dia 20, o ciclo vai do dia 20 ao dia 19 do mês
seguinte.

## Estrutura do projeto

```
app/
├── estruturas/          Estruturas de dados implementadas do zero
│   ├── pilha.py           Pilha com nós encadeados (histórico do Desfazer)
│   ├── fila_prioridade.py Heap binário mínimo (próximos vencimentos)
│   ├── ordenacao.py       Merge sort (ordenar gastos)
│   └── busca.py           Busca binária (gastos de um ciclo)
├── modelos/             Classes do domínio
│   ├── dinheiro.py        Valor monetário em centavos, com operadores
│   ├── ciclo.py           Ciclo financeiro
│   ├── caixinha.py        Caixinha (abstrata) → ContaFixa, Variavel, Reserva
│   ├── lancamento.py      Lancamento (abstrata) → Gasto, Entrada
│   ├── parcelamento.py    Parcelamento e Parcela
│   ├── acoes.py           Ações que podem ser desfeitas (padrão Command)
│   ├── casa.py            Casa: reúne tudo e calcula o resumo
│   └── erros.py           Exceções do sistema
├── repositorio.py       Persistência: Repositorio (abstrata) → JSON / memória
├── estado.py            Casa carregada em memória + trava para concorrência
├── api.py               Rotas da API JSON
├── paginas.py           Rotas das páginas HTML
├── main.py              Montagem da aplicação FastAPI
├── exemplo.py           Dados de exemplo
├── templates/           HTML (Jinja2)
└── static/              CSS
tests/                   Testes automatizados (pytest)
```

## Conceitos aplicados

### Programação Orientada a Objetos

| Conceito | Onde |
|---|---|
| Classes e objetos | Todo o pacote `app/modelos/` |
| Encapsulamento | `Caixinha.nome` e `Caixinha.aporte` validados por `@property`; atributos internos da `Casa` (`_gastos`, `_historico`) |
| Herança | `Caixinha` → `ContaFixa`, `Variavel`, `Reserva`; `Lancamento` → `Gasto`, `Entrada`; `ErroDeNegocio` → `NaoEncontrado` |
| Polimorfismo | `alocado_da_renda()`, `acumula_entre_ciclos()` e `dica()` respondem diferente em cada tipo de caixinha; `Acao.desfazer()` |
| Abstração | Classes abstratas (`ABC`): `Caixinha`, `Lancamento`, `Acao`, `Repositorio` |
| Composição | A `Casa` é composta por caixinhas, gastos, entradas e parcelamentos |
| Sobrecarga de operadores | `Dinheiro`: `+`, `-`, `*`, `<`, `str()` |
| Métodos de classe / fábrica | `Dinheiro.de_texto()`, `Caixinha.criar()`, `Caixinha.de_dict()`, `CicloFinanceiro.da_data()` |
| Imutabilidade | `Dinheiro`, `CicloFinanceiro` e `Parcela` são `dataclass(frozen=True)` |
| Padrão de projeto Command | `modelos/acoes.py` + Desfazer |
| Padrão Repository | `repositorio.py` |

### Estrutura de Dados

| Estrutura / algoritmo | Onde | Complexidade |
|---|---|---|
| Pilha (lista encadeada) | `estruturas/pilha.py`: histórico do Desfazer | empilhar/desempilhar O(1) |
| Heap / fila de prioridade | `estruturas/fila_prioridade.py`: próximos vencimentos | inserir/remover O(log n) |
| Merge sort | `estruturas/ordenacao.py`: ordenação dos gastos | O(n log n), estável |
| Busca binária | `estruturas/busca.py`: gastos de um ciclo, inserção ordenada | O(log n) |
| Tabela hash (`dict`) | `Casa._caixinhas`, `Casa._parcelamentos`: acesso por id | O(1) em média |
| Lista ordenada | `Casa._gastos`, `Casa._entradas`, mantidas por data | busca O(log n) |

## Regras de negócio principais

- **Dinheiro em centavos inteiros.** `0.1 + 0.2` em ponto flutuante dá
  `0.30000000000000004`; por isso todo valor é guardado como `int` em centavos.
- **Dinheiro livre** = o que entrou no ciclo − o que já tem destino. Um real
  tem destino quando está reservado no aporte de uma caixinha ou quando já foi
  gasto além do que estava reservado.
- **Caixinha sem aporte:** os gastos dela saem direto do dinheiro livre.
- **Reserva:** só o valor guardado sai da renda; sacar da reserva não consome
  a renda do mês.
- **Ritmo:** compara a porcentagem do previsto que já foi gasta com a
  porcentagem do ciclo que já passou (margem de 10 pontos).
- **Parcelas:** a última parcela absorve a diferença do arredondamento; um
  vencimento no dia 31 cai no último dia dos meses mais curtos.
