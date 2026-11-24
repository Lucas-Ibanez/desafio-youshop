# Promessa Rastreável (MVP)

Liga **o que o produto pode prometer** (ficha da marca), **o que o creator prometeu** na peça que
gerou a venda e **por que o comprador pediu o dinheiro de volta**. Um servidor MCP com dois agentes
de IA (checador de conteúdo e classificador de devolução) e um painel devolvem isso a quem prometeu.

## Requisitos

- [uv](https://docs.astral.sh/uv/): instala o Python 3.12 do projeto (fixado em `.python-version`)
  e as dependências. Não precisa de `make`: os comandos ficam em `tasks.py`.
- Chave da API do Gemini (`GEMINI_API_KEY`). Sem chave, tudo funciona só com regras e com textos
  fixos, exceto a classificação de devoluções, que vai para revisão humana.
- Opcional: [Claude Code](https://claude.com/claude-code) para conversar com o servidor MCP.

## Instalação

```bash
git clone <repositório> && cd desafio-youshop
cp .env.example .env            # preencha GEMINI_API_KEY
uv run python tasks.py setup    # uv sync
```

## Passo a passo

```bash
uv run python tasks.py lint test             # ruff e testes sem rede
uv run python tasks.py db-reset seed simulate  # banco, dados fictícios e 600 vendas simuladas
uv run python tasks.py demo                  # exemplo do guia de ponta a ponta pelo MCP
uv run python tasks.py painel                # painel em http://localhost:8501
uv run python tasks.py eval                  # Teste 1 dos dois agentes (relatórios em eval/reports/)
```

Tarefas em sequência param na primeira falha. `uv run python tasks.py help` lista todas.
Nos documentos, `make <x>` significa `uv run python tasks.py <x>`.

| Tarefa | Faz |
|---|---|
| `setup` | `uv sync` |
| `lint` / `format` | ruff |
| `test` / `test-llm` | pytest sem rede / só os testes que chamam o Gemini |
| `db-reset` | apaga e recria `var/promessa.db` |
| `gold` | importa, anonimiza e confere os gabaritos (precisa de `data/raw/` e `docs/fontes/`, fora do git) |
| `seed` | 5 marcas, produtos, fichas v1 e creators fictícios |
| `simulate` | peças, links, 600 vendas e devoluções fictícias (`PROMESSA_SIMULATE_ARGS="--modo gabarito"` roda sem modelo) |
| `eval-checador` / `eval-classificador` / `eval` | Teste 1 contra os gabaritos da H2 e da H1 |
| `demo` | exemplo do guia pelo protocolo MCP, num banco só da demo (`var/demo.db`) |
| `painel` | painel Streamlit: marca, creator e Operações |
| `mcp` | servidor MCP em stdio (`python -m promessa.mcp_server`) |

### A demo

`tasks.py demo` sobe o servidor MCP como subprocesso e roda o exemplo do guia: ficha do Treino em
Casa (7 dias de garantia, 12 meses de acesso) → peça "acesso vitalício e 30 dias para testar"
bloqueada → peça corrigida e link gerado com as promessas presas → devolução "perdi o acesso, achei
que era para sempre" classificada como promessa / condição da oferta, **contradiz**, sem pesar na
creator → relatório do produto com o sinal "acesso vitalício" para a marca. Termina com
"Demo concluída" (cerca de 5 s com cache).

### O painel

| Página | Para quem | O que faz |
|---|---|---|
| 1 · Ficha | marca | versões, condições, regras com fonte, briefing, nova versão |
| 2 · Checador | creator | briefing, checagem com trechos coloridos, link rastreado, contestação |
| 3 · Fila de revisão | marca, Operações | bloqueios contestados e classificações com confiança baixa |
| 4 · Relatórios | todos | marca/Operações por produto ou creator; creator só os próprios números e a explicação |
| 5 · Avaliação | todos | metas e resultados do Teste 1 |

O papel é escolhido na barra lateral (não há login no MVP).

## Conectar no Claude Code

```bash
claude mcp add promessa -- uv run --directory <caminho absoluto do repositório> python -m promessa.mcp_server
claude mcp list        # promessa: ... ✔ Connected
```

O servidor usa o banco de `PROMESSA_DB_URL` (padrão `var/promessa.db`): rode
`db-reset seed simulate` antes. São 9 ferramentas (e `ping`): `get_product_facts`,
`upsert_product_facts`, `check_content`, `register_content_and_link`, `classify_refund`,
`get_promise_outcome_report`, `explain_refunds_to_creator`, `list_review_queue`, `submit_review`.

Três pedidos de exemplo (respostas reais de 24/11/2026, resumidas):

1. **"Confira esta legenda para o produto prod_magnesio, da creator cr_eli: 'Magnésio que seca barriga
   e turbina a imunidade! A vitamina B6 auxilia no funcionamento do sistema imune. Só hoje!'"**
   → bloqueada: tirar "seca barriga" (emagrecimento não tem alegação aprovada) e "turbina a
   imunidade"; manter a frase da IN 28 com as palavras exatas; confirmar se a oferta é mesmo só
   hoje; incluir #publi. Sugere uma legenda que passa.
2. **"Por que as vendas da cr_ana estão voltando neste mês?"** → 18 devoluções em 150 vendas: 7 pela
   promessa "Secar até 5KG EM 7 DIAS" (mudar o trecho); 3 esperavam "acesso vitalício", que não está
   na peça dela (sinal para a marca); 8 não têm a ver com ela (acesso, reembolso, cobrança).
3. **"Quais promessas sobre o prod_treino mais geram devolução?"** → da creator: "Secar até 5KG EM
   7 DIAS" (7, cr_ana); sinal para a marca: "acesso vitalício" (7 compradores de cr_ana e cr_bia
   acreditavam nisso sem estar nas peças; conferir o kit de divulgação); acesso e reembolso não pesam
   na creator.

## Resultados do Teste 1

Resumo em [docs/resultados.md](docs/resultados.md). O classificador atinge as três metas no `test`
(acurácia 83%, kappa 0,77, subtipo 74%) e passa no critério de corte; o checador bloqueia as 4
alegações proibidas, mas fica abaixo da meta de kappa (0,37) e de extração de promessas (71% com o
modelo). Os vazamentos (regras e paráfrase vindas da própria codificação) estão declarados lá.

## Limites do MVP

- **Dados:** vendas e devoluções são **simuladas** (sem dados da YouShop até a H5); produtos,
  marcas e creators são fictícios. A avaliação usa os gabaritos reais da H1 e da H2, codificados por
  uma pessoa.
- **Só texto:** sem vídeo, áudio ou imagem. A peça entra por envio voluntário (sem monitorar redes).
- **Nenhuma decisão automática tem consequência:** `bloquear` é um alerta forte; contestação e
  decisão são humanas; nada altera comissão ou alcance.
- **Não julga verdade científica:** compara com listas oficiais e com a ficha da marca. As alegações
  permitidas da IN 28 só cobrem magnésio e vitamina B6 (o suplemento fictício), e a página do PDF
  não pôde ser conferida.
- **Protótipo local:** sem login, multi-tenant ou nuvem; o papel é um parâmetro. O MCP está pronto
  para agentes externos, mas é interno no MVP.
- **Cota do Gemini (plano gratuito):** 15 chamadas/min e 500/dia por modelo. O cache em disco
  (`.cache/llm`) torna as rodadas repetidas rápidas e reprodutíveis; `LLM_OFFLINE=true` usa só o
  cache.

## Notas para Windows

- **Executáveis do `.venv` bloqueados.** O Controle de Aplicativo do Windows pode bloquear os `.exe`
  que o uv gera em `.venv/Scripts/`. Por isso o projeto sempre chama `python -m <módulo>`
  (`python -m pytest`, `python -m ruff`, `python -m streamlit`, `python -m promessa.mcp_server`).
- **Acentos e símbolos no console.** O `tasks.py` passa `PYTHONUTF8=1` e `PYTHONIOENCODING=utf-8`
  aos subprocessos; fora dele, exporte as duas variáveis se a saída sair com caracteres trocados.
- **Fim de linha.** O `.gitattributes` fixa LF no repositório.

## Documentos

- [docs/CONTEXTO.md](docs/CONTEXTO.md): o que é, stack, modelo de dados, regras dos agentes
- [docs/PLANO.md](docs/PLANO.md): tasks, andamento e roteiro da demo (seção 6)
- [docs/decisoes.md](docs/decisoes.md): decisões registradas (D1 a D37)
- [docs/resultados.md](docs/resultados.md): Teste 1

## Status

MVP concluído (T01 a T16), tag `v0.1-mvp`.
