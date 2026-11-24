# Promessa Rastreável · Contexto do projeto

> Documento de contexto para quem constrói o MVP (Lucas + Claude Code). Leia antes de qualquer task do `PLANO.md`.
> Versão 1 · 23/11/2026 · Prazo do MVP: **24/11/2026, 18h**.
> Fontes: `MVP Promessa Rastreável: guia de construção` (23/11) e as validações H1 a H4 do projeto "Case YouShop".

---

## 0. Como usar este documento

- No repositório, este arquivo fica em `docs/CONTEXTO.md` e o plano em `docs/PLANO.md`. O `CLAUDE.md` da raiz é curto e aponta para os dois (modelo na seção 17.3).
- **Fonte de verdade de produto:** o guia de construção (`docs/fontes/guia-mvp.md`). **Fonte de verdade técnica:** este arquivo. Se houver conflito, este arquivo vence e a divergência vai para `docs/decisoes.md`.
- Tudo o que uma pessoa lê (alertas, explicações, painel, relatórios) é em **português do Brasil, linguagem simples**. Código, nomes de tabelas e colunas são em inglês; valores de enum que aparecem para o usuário ficam em português sem acento (`bloquear`, `contradiz`).
- Quando algo aqui estiver ambíguo, escolha a opção **mais simples** que respeite os princípios da seção 5 e registre a escolha em `docs/decisoes.md`.

---

## 1. O que estamos construindo

**Uma frase:** um servidor MCP com dois agentes de IA e um painel que liga **o que o produto pode prometer**, **o que o creator prometeu na peça que gerou a venda** e **por que o comprador pediu o dinheiro de volta**.

**A afirmação que o MVP precisa provar:**
> Dá para ligar, de forma automática e auditável, a devolução à promessa que gerou a venda e devolver isso a quem prometeu.

Tudo o que não serve a essa prova fica fora.

**Os quatro módulos:**

| # | Módulo | Em uma linha |
|---|---|---|
| 1 | Ficha de promessas do produto | A marca declara, com versão, as condições da oferta e as alegações permitidas e proibidas, com a fonte de cada uma. |
| 2 | Checador de conteúdo (Agente 1) | Recebe o texto da peça e devolve, por trecho, `bloquear`, `revisar` ou `registrar`. Compara condição anunciada com a da ficha. |
| 3 | Promessa registrada na venda | O link rastreado só nasce depois da checagem e carrega a peça e a versão da ficha. Cada venda herda isso. |
| 4 | Classificador de devolução e retorno (Agente 2) | Classifica o motivo do comprador, liga à promessa registrada (`confirma`, `contradiz`, `sem_relacao`) e monta relatório por creator e produto, com explicação simples para o creator. |

---

## 2. Por que: evidências que viram requisito

Cada número abaixo veio das validações e se traduz numa exigência concreta de código.

| Evidência | Origem | Requisito no código |
|---|---|---|
| 25,6% de 172 compradores reclamam de promessa (15,7% explícita). Acesso (34,3%) e processo (32,0%) são maiores. | H1 | O classificador **separa promessa de acesso e processo**. Só promessa explícita ligada pesa no creator. |
| Quando o comprador diz onde foi convencido, 64,7% é promessa (vs 22,9%). 80% não dizem o canal. | H1 | O link guarda o canal **sempre** (`content_piece.channel`, `tracked_link.actor_type`). |
| 52% das promessas explícitas são condição da oferta (vitalício, garantia, bônus, recorrência, custo oculto). Caso real: anúncio com 30 dias de garantia, checkout com 7. | H1 | A ficha **começa pelas condições da oferta**. O checador compara condição anunciada × ficha de forma **determinística**. |
| 55% de 60 anúncios com indício de irregularidade; 12 de 13 em suplementos; 4 com alegação da lista proibida da Anvisa. | H2 | Lista proibida por categoria vira `bloquear`. Indícios viram `revisar`. |
| Marcas 67,9% vs creators 43,8%. | H2 | A **ficha é da marca** e a checagem vale para peça enviada pela marca também (`submitted_by`). |
| 36,7% das peças têm promessa verificável (prazo, número, condição). | H2 | O checador **extrai** a promessa normalizada (`extracted`) para virar `registered_promise`. |
| Sinais baratos: urgência vencida, grafia disfarçada (`m0unj@r0`), nome do produto que já é alegação, venda fora da plataforma. | H2 | Camada 1 de regras determinísticas, com normalização de grafia. |
| 0 de 9 plataformas diz o que **aquele** produto pode prometer; 0 confere antes de publicar; 0 de 5 de infoproduto exige identificação publicitária. | H3 | `get_product_facts` devolve um **briefing** para o creator no momento do link, com a instrução de identificação (`#publi`). |
| Regras da Anvisa em revisão desde 05/08/2026; IN 28 atualizada várias vezes. | H3 | **Regras são dados versionados** (YAML com fonte e versão). Trocar lista não muda código. |
| Hotmart, Kiwify e Eduzz têm origem da venda e motivo do reembolso, mas não ligam um ao outro nem à promessa. Hotmart e Kiwify lançaram MCP em nov/2026. | H4 | O diferencial é a **costura** promessa × motivo × creator, exposta via MCP. |
| TikTok Shop já dá nota ao creator, mas por média de avaliação. | H4 | O retorno ao creator explica **o porquê** e **qual trecho mudar**, não só um número. |

**Limites que o código precisa respeitar (das próprias validações):** reclamação não é reembolso; a H2 viu só texto; uma pessoa codificou tudo; as regras do checador foram escritas a partir da mesma auditoria que serve de gabarito (risco de vazamento, seção 14.4).

---

## 3. Escopo

### 3.1 Dentro do MVP (até 24/11, 18h)

- Ficha versionada e imutável, com regras oficiais materializadas por versão.
- Checador em duas camadas (regras + modelo), com três saídas por trecho e comparação com a ficha.
- Registro da peça, das promessas e do link rastreado; bloqueio impede o link até ajuste ou revisão humana.
- Classificador de devolução com a taxonomia da H1 e ligação com a promessa registrada.
- Relatórios por creator e por produto, explicação em linguagem simples para o creator.
- Servidor MCP como porta de entrada (stdio), utilizável no Claude Code ou Claude Desktop.
- Painel simples (Streamlit) com as visões de marca, creator e Operações.
- **Teste 1** do guia: avaliação dos dois agentes contra os gabaritos da H2 (60 anúncios) e da H1 (172 compradores).
- Simulador de vendas e devoluções para a demo (produtos e creators fictícios).

### 3.2 Fora do MVP (não construir)

| Fora | Por quê |
|---|---|
| Vídeo, áudio, OCR | Só texto (legenda, roteiro, transcrição colada). Vídeo é a fase seguinte. |
| Monitorar redes sozinho | A peça entra por envio voluntário. Evita vigilância. |
| Punir, bloquear publicação, cortar comissão | `bloquear` é alerta forte; decisão é humana. |
| Julgar verdade científica ou "resultado" de infoproduto | Só compara com listas oficiais e com o que a marca declarou. |
| Abrir o MCP a agentes externos (ideia D, fase 2) | O servidor nasce pronto, mas no MVP é interno. |
| Antifraude de pagamento | Fraude é só uma categoria do classificador. |
| Autenticação, multi-tenant, deploy em nuvem | Protótipo local. O papel (`marca`, `creator`, `operacoes`) é um parâmetro, não um login. |
| Integração real com checkout da YouShop | A ficha é a fonte das condições do checkout (premissa, seção 18). Vendas e devoluções vêm do simulador. |
| Teste 2 (piloto) | Depende das respostas da YouShop (H5). O MVP só deixa as métricas instrumentadas. |

---

## 4. Atores e fluxo

| Ator | O que faz no MVP | Papel no código |
|---|---|---|
| Marca / produtor | Cria e versiona a ficha; revisa bloqueios contestados; vê relatório do produto. | `marca` |
| Creator | Recebe o briefing; cola a peça; corrige; gera link; contesta bloqueio; lê a explicação das devoluções. | `creator` |
| Operações YouShop | Fila de revisão (bloqueios contestados, classificações de baixa confiança); relatórios. | `operacoes` |
| Pipeline de reembolso | Envia cada devolução para classificação. No MVP, é o simulador. | `sistema` |

```
ANTES DA VENDA
 Marca ──upsert_product_facts──▶ Ficha v1 (condições + regras com fonte)
                                     │
 Creator ──get_product_facts──▶ briefing ("pode / não pode / condições exatas / #publi")
 Creator ──check_content(texto)──▶ trechos: bloquear | revisar | registrar
          └─ corrige e reenvia (nova peça, parent_piece_id) ──▶ sem bloqueio pendente
 Creator ──register_content_and_link(peça)──▶ tracked_link + registered_promise[]

 ══════════════ venda (sale herda link → peça → versão da ficha) ══════════════

DEPOIS DA VENDA
 Pipeline ──classify_refund(venda, motivo)──▶ causa/subcausa + crença do comprador
                                              └─ liga à promessa: confirma | contradiz | sem_relacao
 Marca/Ops ──get_promise_outcome_report──▶ taxas por causa, promessas contestadas, sinais para a marca
 Creator ──explain_refunds_to_creator──▶ "o que voltou, por quê, o que não é com você, qual trecho mudar"

 Dois retornos: o creator muda a próxima peça; a marca corrige a ficha, o checkout ou o kit de divulgação.
```

---

## 5. Arquitetura

```
 ┌──────────────────────┐    ┌──────────────────────┐    ┌──────────────────────┐
 │ Claude Code/Desktop  │    │ scripts/demo_e2e.py  │    │ Painel (Streamlit)   │
 │ (cliente MCP)        │    │ (cliente MCP stdio)  │    │ app/                 │
 └──────────┬───────────┘    └──────────┬───────────┘    └──────────┬───────────┘
            │ MCP (stdio)               │ MCP (stdio)               │ chamada direta
            ▼                           ▼                           │ (decisão D3)
 ┌─────────────────────────────────────────────────┐                │
 │ src/promessa/mcp_server.py  (ferramentas finas) │                │
 └──────────────────────┬──────────────────────────┘                │
                        ▼                                           ▼
 ┌──────────────────────────────────────────────────────────────────────────────┐
 │ Camada de serviços (toda a lógica de negócio)                                │
 │ facts · checker · links · refunds · reports · review                          │
 └───────┬────────────────────┬───────────────────────┬─────────────────────────┘
         ▼                    ▼                       ▼
 ┌──────────────┐   ┌───────────────────┐   ┌───────────────────────────────┐
 │ db (SQLite / │   │ rules (YAML       │   │ llm (API do Gemini, saída      │
 │ SQLAlchemy)  │   │ versionado)       │   │ estruturada, cache em disco)   │
 └──────────────┘   └───────────────────┘   └───────────────────────────────┘
```

**Princípios (valem para toda task):**

1. **MCP é a porta de entrada; serviços são a lógica.** Ferramentas MCP só validam entrada, chamam um serviço e serializam a saída. Nenhuma regra de negócio dentro de `mcp_server.py` nem do painel.
2. **Regras são dados.** Listas, padrões e taxonomia vivem em `data/rules/*.yaml`, com `fonte`, `referencia` e `versao`. Código não contém termos proibidos.
3. **Determinístico antes de modelo.** Regra barata primeiro; o modelo entra onde a regra não alcança e para escrever explicação. O modelo **não** rebaixa uma decisão de regra.
4. **Versão em tudo, nada é editado.** Ficha, peça e regras materializadas são imutáveis. Mudança = nova versão. Isso prova o que valia no dia da venda (CDC art. 30).
5. **Toda decisão automática deixa rastro; nenhuma tem consequência sozinha.** Cada saída grava origem (regra ou modelo), modelo, versão do prompt e explicação. Cada revisão humana grava quem decidiu.
6. **Reprodutível.** Chamadas ao modelo com temperatura 0 e cache em disco; simulador com semente fixa; avaliação roda offline depois da primeira vez.

---

## 6. Stack

| Camada | Escolha | Por quê |
|---|---|---|
| Linguagem | Python 3.12 | Sugerida no guia; SDK oficial de MCP e do Gemini. |
| Ambiente e dependências | `uv` (+ `uv.lock`) | Instala e roda rápido; um comando para tudo. |
| Servidor MCP | SDK oficial `mcp` 2.x (classe `MCPServer` em `mcp.server.mcpserver`), transporte stdio; cliente `mcp.Client` (em memória nos testes ou stdio) | Padrão para Claude Code/Desktop; mesmo servidor serve agentes externos na fase 2. |
| Modelo de linguagem | Gemini via SDK `google-genai`, saída estruturada nativa (`response_mime_type="application/json"` + `response_schema` com o modelo Pydantic), temperatura 0 | JSON validável com Pydantic; reprodutível. |
| Modelos (configuráveis) | Checador, classificador e explicação: `gemini-3.5-flash-lite` (D25) | Rápido (~1 s por chamada) e dentro da cota da chave; o `gemini-3.6-flash` levou ~40 s por chamada e estourou a cota (D24). Trocar por variável de ambiente; escolha final pelo split de desenvolvimento. |
| Banco | SQLite (arquivo `var/promessa.db`) via SQLAlchemy 2.x | Protótipo sem servidor; troca para Postgres por URL. |
| Validação e esquemas | Pydantic v2 | Entrada/saída de ferramentas, YAML de regras, saída do modelo. |
| Regras e seeds | YAML (`pyyaml`) | Legível pela marca e pelo jurídico; versionável no git. |
| Painel | Streamlit | Painel web em horas, em Python, reaproveitando os serviços. |
| Avaliação | `pandas`, `scikit-learn` (kappa de Cohen, matriz de confusão) | Métricas padrão sem reinventar. |
| Qualidade | `pytest`, `ruff` (lint + format) | Testes rápidos; marcador `llm` para testes que usam o modelo. |
| Configuração | `python-dotenv` + `pydantic-settings` (ou `os.environ` simples) | `.env` local, nada de segredo no código. |

Versões: use a mais recente estável de cada pacote no momento da instalação e fixe no `uv.lock`. Se alguma API do SDK `mcp` diferir do descrito aqui, siga a documentação do pacote instalado e registre em `docs/decisoes.md`.

---

## 7. Estrutura de pastas

```
desafio-youshop/                  # repositório; projeto Python `promessa-rastreavel`, pacote `promessa`
├── CLAUDE.md                     # curto: aponta para docs/ e lista comandos (modelo na seção 17.3)
├── README.md                     # como instalar, rodar, testar, demonstrar
├── tasks.py                      # executor de tarefas em Python puro (seção 17.2; substitui o make)
├── pyproject.toml                # dependências, pytest (marcador llm) e ruff
├── uv.lock
├── .python-version               # 3.12
├── .env.example                  # variáveis da seção 17.1, sem valores secretos
├── .gitignore                    # .env, var/, data/raw/, docs/fontes/, .cache/, __pycache__/
├── .gitattributes                # fim de linha LF
│
├── docs/
│   ├── CONTEXTO.md               # este arquivo
│   ├── PLANO.md                  # tasks em ordem
│   ├── decisoes.md               # registro curto de decisões (D1, D2, ...)
│   ├── resultados.md             # resumo do Teste 1 (gerado/atualizado na T16)
│   └── fontes/                   # guia do MVP + validações H1–H4 (FORA DO GIT: nomes reais; só o README entra)
│
├── data/
│   ├── raw/                      # h2_auditoria.csv, h1_amostra1.csv, h1_amostra2.csv, anon_map.yaml (FORA DO GIT: têm nomes)
│   ├── gold/                     # gabaritos anonimizados (JSONL) + splits.json + recodificacao/
│   ├── rules/                    # regras como dados (YAML versionado, seção 10)
│   │   ├── normalizacao.yaml
│   │   ├── suplemento_proibidas.yaml
│   │   ├── suplemento_in28_permitidas.yaml
│   │   ├── cosmetico_proibidas.yaml
│   │   ├── padroes_h2.yaml       # prazo+resultado, renda+número, urgência, medicamento
│   │   ├── condicoes_oferta.yaml # padrões de garantia, acesso, recorrência, bônus, custo
│   │   └── taxonomia_devolucao.yaml
│   └── seeds/
│       ├── marcas_produtos.yaml  # 5 produtos fictícios + ficha v1
│       ├── creators.yaml
│       └── cenarios_relacao.yaml # casos de teste da relação confirma/contradiz/sem_relacao
│
├── src/promessa/
│   ├── __init__.py
│   ├── config.py                 # leitura do .env, thresholds, nomes de modelos
│   ├── errors.py                 # exceções de domínio com código (BLOQUEIO_PENDENTE, ...)
│   ├── db/
│   │   ├── models.py             # tabelas (seção 8)
│   │   ├── session.py            # engine, sessão, create_all, triggers de imutabilidade
│   │   └── enums.py
│   ├── rules/
│   │   ├── schema.py             # modelos Pydantic dos YAML
│   │   ├── loader.py             # carrega e valida; `python -m promessa.rules.loader --check`
│   │   ├── normalize.py          # normalização que preserva posições (seção 11.2)
│   │   └── match.py              # casamento de termos e padrões (sintaxe da D20)
│   ├── llm/
│   │   ├── client.py             # complete_json(): Gemini com saída estruturada (response_schema), retry, cache, log
│   │   ├── cache.py
│   │   └── prompts/              # checker_v1.md, classifier_v1.md, linker_v1.md, explainer_v1.md
│   ├── facts/
│   │   ├── service.py            # ficha: criar versão, ler vigente, briefing, materializar regras
│   │   └── seed.py               # carga de data/seeds/ (usada por scripts/seed.py e testes)
│   ├── checker/
│   │   ├── models.py             # CheckContext, Finding, resultado (D23)
│   │   ├── segment.py            # divide em trechos com offsets
│   │   ├── deterministic.py      # camada 1: listas e padrões
│   │   ├── offer_conditions.py   # camada 1: condições anunciadas × ficha
│   │   ├── llm_layer.py          # camada 2
│   │   └── service.py            # orquestra, aplica precedência, persiste
│   ├── links/service.py          # registra promessas e gera link
│   ├── refunds/
│   │   ├── classifier.py         # causa, subcausa, crença do comprador
│   │   ├── linker.py             # relação com a promessa registrada
│   │   └── service.py
│   ├── reports/
│   │   ├── service.py            # métricas por creator e produto
│   │   └── explain.py            # texto simples para o creator
│   ├── review/service.py         # fila e decisões humanas
│   ├── privacy.py                # remoção de dados pessoais do motivo
│   └── mcp_server.py             # MCPServer (mcp 2.x) + ferramentas (seção 9); `python -m promessa.mcp_server`
│
├── app/
│   ├── painel.py                 # entrada do Streamlit
│   └── pages/                    # 1_Ficha.py, 2_Checador.py, 3_Fila_de_revisao.py, 4_Relatorios.py, 5_Avaliacao.py
│
├── scripts/
│   ├── import_gold.py            # CSV → JSONL anonimizado + conferência de contagens
│   ├── blind_sample.py           # amostra cega para recodificação humana
│   ├── seed.py                   # carrega marcas, produtos, fichas, creators
│   ├── simulate.py               # peças, links, vendas e devoluções sintéticas
│   └── demo_e2e.py               # exemplo do guia, de ponta a ponta, via cliente MCP
│
├── eval/
│   ├── metrics.py
│   ├── eval_checker.py           # Teste 1 do checador (H2)
│   ├── eval_classifier.py        # Teste 1 do classificador (H1)
│   ├── agreement.py              # concordância humano × humano (recodificação cega)
│   └── reports/                  # *.md, *.json, erros_*.csv
│
├── var/                          # banco SQLite (fora do git)
└── tests/
    ├── conftest.py               # banco em memória, fixtures de produtos
    ├── mcp_helpers.py            # call_tool(): cliente MCP em memória, devolve dict
    ├── test_config.py
    ├── test_tasks.py
    ├── test_models.py
    ├── test_rules.py
    ├── test_checker_deterministic.py
    ├── test_checker_llm.py       # @pytest.mark.llm
    ├── test_links.py
    ├── test_refunds.py
    ├── test_reports.py
    ├── test_privacy.py
    └── test_mcp_tools.py         # pelo protocolo MCP: em memória e por subprocesso stdio
```

---

## 8. Modelo de dados

São as **10 entidades do guia** mais **3 de apoio** (`brand`, `creator`, `review_event`). Dinheiro em centavos (inteiro). Datas em UTC, exibidas em America/Sao_Paulo.

### 8.1 Tabelas

| Tabela | Colunas principais | Regras |
|---|---|---|
| `brand` | `id` (texto, ex. `mk_movimento`), `name` | Apoio. |
| `creator` | `id` (ex. `cr_ana`), `handle`, `display_name` | Apoio. |
| `product` | `id` (ex. `prod_treino`), `brand_id`, `name`, `category` | `category` ∈ `suplemento`, `cosmetico`, `infoproduto_renda`, `infoproduto_outro`. Decide quais listas oficiais se aplicam. |
| `product_facts` | `id`, `product_id`, `version`, `guarantee_days`, `access_type`, `access_months`, `recurrence`, `auto_renewal`, `bonuses` (JSON lista), `extra_costs` (JSON lista de `{descricao, valor_mensal_cents}`), `valid_from`, `created_by`, `created_at` | **Imutável** (trigger bloqueia UPDATE e DELETE). Única por `(product_id, version)`. `guarantee_days ≥ 7` (CDC art. 49). `access_type` ∈ `vitalicio`, `prazo`, `assinatura`, `nao_aplica` (produto físico); `prazo` exige `access_months`. `recurrence` ∈ `unica`, `mensal`, `anual`. Vigente = maior `valid_from ≤ agora`. |
| `claim_rule` | `id`, `facts_id`, `rule_key` (ex. `SUP-EMAG`), `text`, `kind`, `source`, `reference`, `output`, `payload` (JSON: tema, termos, padrões, `junto_de`, sugestão; D22) | Uma linha por regra aplicável **àquela versão** da ficha. `kind` ∈ `permitida`, `proibida`. `source` ∈ `IN28`, `ANVISA`, `RDC752`, `CONAR`, `CDC`, `MARCA`. `reference` = `arquivo.yaml@versao` ou URL. `output` ∈ `bloquear`, `revisar` (só para proibidas). Regras oficiais são **copiadas** dos YAML na criação da versão. |
| `content_piece` | `id` (uuid), `creator_id`, `product_id`, `facts_id`, `text`, `url`, `channel`, `published_since`, `submitted_by`, `parent_piece_id`, `submitted_at` | **Imutável.** Correção = nova peça com `parent_piece_id`. `channel` ∈ `instagram`, `tiktok`, `youtube`, `whatsapp`, `outro`. `submitted_by` ∈ `creator`, `marca`. `published_since` (opcional) serve para urgência vencida. |
| `check_result` | `id`, `piece_id`, `span_start`, `span_end`, `excerpt`, `output`, `rule_key`, `source`, `reason_type`, `explanation`, `suggestion`, `extracted` (JSON), `model`, `prompt_version`, `confidence`, `review_status`, `reviewed_by`, `reviewed_at`, `created_at` | Um por trecho marcado. `output` ∈ `bloquear`, `revisar`, `registrar`. `source` ∈ `regra`, `modelo`. `review_status` ∈ `nao_aplicavel`, `contestado`, `mantido`, `revertido`. |
| `registered_promise` | `id`, `piece_id`, `check_result_id`, `type`, `attribute`, `value`, `unit`, `normalized_text`, `approval` | Criada no `register_content_and_link`. `type` ∈ `condicao_oferta`, `resultado`, `alegacao`. `attribute` ∈ `garantia`, `acesso`, `recorrencia`, `bonus`, `custo`, `resultado`, `outro`. `approval` ∈ `registrada` (veio de `registrar`), `em_revisao` (veio de `revisar`). |
| `tracked_link` | `id` (código curto base32, 8 caracteres), `creator_id`, `product_id`, `piece_id`, `facts_id`, `actor_type`, `url`, `disclosure_text`, `created_at` | Só existe após checagem sem bloqueio pendente. `actor_type` ∈ `humano`, `agente` (o "canal humano ou agente" do guia). |
| `sale` | `id`, `link_id`, `amount_cents`, `commission_cents`, `created_at` | Herda creator, peça e ficha pelo link. |
| `refund_event` | `id`, `sale_id`, `type`, `reason_text`, `created_at` | `type` ∈ `reembolso`, `chargeback`, `ticket`. `reason_text` já passou por `privacy.scrub`. |
| `refund_classification` | `id`, `refund_id`, `cause`, `subcause`, `buyer_belief` (JSON), `channel_mentioned`, `linked_promise_id`, `relation`, `confidence`, `explanation`, `model`, `prompt_version`, `review_status`, `reviewed_by`, `reviewed_at`, `created_at` | `cause` e `subcause` da taxonomia (seção 12.1). `relation` ∈ `confirma`, `contradiz`, `sem_relacao`, `nao_aplicavel`. |
| `review_event` | `id`, `target_type`, `target_id`, `action`, `actor`, `actor_role`, `note`, `payload` (JSON), `created_at` | **Só inserção** (log de auditoria). `action` ∈ `contestar`, `manter`, `reverter`, `aprovar`, `reclassificar`. |

### 8.2 Correspondência com o guia

| Guia | Código |
|---|---|
| `product_facts.garantia_dias / tipo_acesso / recorrência / bônus[] / custos_extras[]` | `guarantee_days / access_type (+ access_months) / recurrence (+ auto_renewal) / bonuses / extra_costs` |
| `claim_rule.facts_version` | `claim_rule.facts_id` (FK para a versão exata) |
| `content_piece.canal` | `content_piece.channel` (rede onde a peça roda) |
| `tracked_link.canal (humano ou agente)` | `tracked_link.actor_type` |
| `check_result.saída / regra_acionada / modelo / revisado_por` | `output / rule_key / model (+ prompt_version) / reviewed_by` |
| `refund_classification.promessa_ligada_id / relação` | `linked_promise_id / relation` |

### 8.3 Invariantes que os testes precisam cobrir

1. UPDATE ou DELETE em `product_facts`, `content_piece` e `review_event` falha no banco.
2. Não existe `tracked_link` cuja peça tenha `check_result` com `output = bloquear` e `review_status ≠ revertido`.
3. `tracked_link.facts_id = content_piece.facts_id` e é a versão vigente no momento da geração.
4. Toda `refund_classification` com `relation ∈ {confirma, contradiz}` tem `linked_promise_id` ou `buyer_belief` preenchido.
5. Nenhum texto de `refund_event.reason_text` aparece em saídas de papel `creator`.

---

## 9. Ferramentas MCP

Servidor: `src/promessa/mcp_server.py`, nome `promessa-rastreavel`, transporte stdio. Saídas em JSON (modelos Pydantic). Erros de domínio sobem como erro da ferramenta com mensagem `CODIGO: explicação em português`.

| # | Ferramenta | Entrada | Saída | Quem chama |
|---|---|---|---|---|
| 1 | `get_product_facts` | `product_id`, `version?` | ficha (condições), regras com fonte, `briefing` (texto curto para o creator) | creator (app), checador, agentes externos (fase 2) |
| 2 | `upsert_product_facts` | `product_id`, condições, `brand_rules[]`, `created_by` | `{version, warnings[]}` (ex.: nome do produto contém alegação) | marca |
| 3 | `check_content` | `product_id`, `creator_id`, `text`, `channel`, `submitted_by?`, `published_since?`, `parent_piece_id?` | `{piece_id, facts_version, overall, findings[], disclosure, can_generate_link, layers_used, notes}` | creator, marca |
| 4 | `register_content_and_link` | `piece_id`, `actor_type?` | `{link_id, url, registered_promises[], disclosure_text}` | creator |
| 5 | `classify_refund` | `sale_id`, `reason_text`, `type?` | `{refund_id, cause, subcause, buyer_belief, relation, linked_promise, confidence, needs_review, explanation}` | pipeline de reembolso, Operações |
| 6 | `get_promise_outcome_report` | `creator_id` **ou** `product_id`, `start`, `end` | taxas por causa, promessas mais contestadas, sinais para a marca, cobertura | marca, Operações |
| 7 | `explain_refunds_to_creator` | `creator_id`, `start`, `end` | `{text, data_used}` | creator |
| 8 | `list_review_queue` | `kind?` (`bloqueio`, `classificacao`) | itens pendentes com contexto | marca, Operações |
| 9 | `submit_review` | `target_type`, `target_id`, `action`, `actor`, `actor_role`, `note?` | estado atualizado | creator (só `contestar`), marca, Operações |

As ferramentas 1, 3, 4, 5, 6 e 7 são as do guia. A 2, 8 e 9 foram acrescentadas porque o guia exige que a marca declare a ficha e que o humano decida, e isso precisa de uma porta.

**Códigos de erro:** `PRODUTO_INEXISTENTE`, `FICHA_INVALIDA`, `FICHA_INEXISTENTE` (versão pedida não existe; D22), `CREATOR_INEXISTENTE`, `ENTRADA_INVALIDA` (valor fora do esperado, ex.: canal; D24), `PECA_INEXISTENTE`, `BLOQUEIO_PENDENTE` (lista os trechos), `FICHA_DESATUALIZADA` (a ficha mudou depois da checagem; reenvie a peça), `VENDA_INEXISTENTE`, `PAPEL_NAO_AUTORIZADO`, `PERIODO_INVALIDO`.

**Formato de `findings[]` (check_content):**

```json
{
  "excerpt": "acesso vitalício",
  "span": [0, 16],
  "output": "bloquear",
  "rule_key": "COND-ACESSO",
  "source": "regra",
  "reason_type": "condicao_contraria_a_ficha",
  "explanation": "A ficha deste produto diz acesso por 12 meses. Prometer acesso vitalício cria uma obrigação que o produto não cumpre.",
  "suggestion": "Troque por \"12 meses de acesso\".",
  "extracted": {"attribute": "acesso", "value": "vitalicio", "unit": null}
}
```

---

## 10. Regras como dados

Todo YAML em `data/rules/` tem cabeçalho obrigatório e é validado por `promessa.rules.loader`:

```yaml
id: suplemento_proibidas
versao: "2026-11-23"
categoria: suplemento            # ou "todas"
origem: ANVISA                   # vira claim_rule.source (IN28, ANVISA, RDC752, CONAR, CDC, MARCA)
fonte: "Anvisa: RDC 243/2018 e IN 28/2018; perguntas e respostas sobre suplementos"
referencia: "https://www.gov.br/anvisa/pt-br/centraisdeconteudo/publicacoes/alimentos/perguntas-e-respostas-arquivos/suplementos-alimentares.pdf"
nota: "Lista curada a partir da auditoria H2. Não é exaustiva."
regras:
  - rule_key: SUP-EMAG
    tema: emagrecimento
    saida: bloquear
    termos: ["emagrec*", "seca barriga", "secar a barriga", "queima gordura", "perda de gordura",
             "reduz gordura", "acumulo de gordura", "bloqueador de acucar", "controle do apetite",
             "controla o apetite", "inibe o apetite"]
    explicacao: "Emagrecimento não tem alegação aprovada para suplementos."
```

Termos ficam já normalizados (minúsculas, sem acento) e casam como palavra ou frase inteira; termo terminado em `*` casa como prefixo (`emagrec*`). Padrões são regex sobre o texto normalizado (D20).

**Arquivos e conteúdo esperado:**

| Arquivo | Conteúdo | Saída |
|---|---|---|
| `suplemento_proibidas.yaml` | Temas sem alegação aprovada (H2 seção 3): emagrecimento, imunidade, foco/concentração, desempenho sexual, tratamento ou prevenção de doença (glicose, insulina, colesterol, fígado, inflamação, diabetes, pressão). | `bloquear` |
| `suplemento_in28_permitidas.yaml` | Alegações permitidas do Anexo V da IN 28, **só para os constituintes do suplemento fictício**, com texto literal. **Transcrever do PDF oficial; nunca inventar.** Enquanto não transcrito, o arquivo leva `status: pendente_transcricao`. | Camada 1: trecho que reproduz literalmente uma alegação permitida → `registrar` e não é bloqueado por termo proibido (D18). Camada 2: alegação de saúde fora da lista → `revisar`. |
| `cosmetico_proibidas.yaml` | Alegação terapêutica em cosmético (RDC 752/2022 e votos da Anvisa): alopecia, queda hereditária, calvície como tratamento, cura, nome que lembra minoxidil. "Crescimento" e "antiqueda" ficam como zona cinzenta. | `bloquear` / `revisar` |
| `padroes_h2.yaml` | Regex e termos: prazo/número junto de resultado (`PRAZO-RESULTADO`), renda com número (`RENDA-NUMERO`), resultado garantido (`RESULTADO-GARANTIDO`), urgência (`URGENCIA`), comparação com medicamento (`MED-COMPARACAO`: mounjaro, ozempic, wegovy, semaglutida, tirzepatida, sibutramina, injeção, caneta). | `revisar` |
| `condicoes_oferta.yaml` | Padrões que extraem garantia (dias), acesso (vitalício ou N meses/anos), recorrência (pagamento único × assinatura), bônus, custo extra ("sem gastar nada", "100% grátis"). | `bloquear` se contradiz a ficha; `registrar` se bate. |
| `normalizacao.yaml` | Mapa de grafia disfarçada (`0→o`, `1→i`, `3→e`, `4→a`, `5→s`, `7→t`, `@→a`, `$→s`). | — |
| `taxonomia_devolucao.yaml` | Causas, subcausas, definições, exemplos curtos e precedência da H1 (seção 12.1). | — |

---

## 11. Agente 1: checador de conteúdo

### 11.1 Saídas e precedência

| Saída | Quando | Efeito |
|---|---|---|
| `bloquear` | Termo de lista **proibida** da categoria, ou condição anunciada **contrária à ficha**. Sempre amarrado a um `rule_key` de `claim_rule` daquela versão. | Link só é gerado após nova peça sem o trecho ou revisão humana que reverta. |
| `revisar` | Indício sem certeza: prazo/número + resultado, renda com número, urgência, comparação com medicamento, grafia disfarçada, alegação de saúde fora da lista permitida, promessa de resultado sem número. | Não impede o link. O creator vê sugestão; a marca pode aprovar. Promessa extraída vira `registered_promise` com `approval = em_revisao`. |
| `registrar` | Condição ou promessa lícita e verificável que **bate** com a ficha (ex.: "7 dias de garantia"). | Vira `registered_promise` com `approval = registrada`. |

`overall` da peça = a saída mais grave entre os trechos (`bloquear` > `revisar` > `registrar` > `limpo`). Se o mesmo trecho for marcado por regras diferentes, ficam todas as marcações; a interface mostra a mais grave primeiro.

### 11.2 Camada 1: regras determinísticas (sem modelo)

1. **Segmentar** o texto em trechos (frases e quebras de linha), guardando posição inicial e final no texto original.
2. **Normalizar preservando posições:** minúsculas; remover acento caractere a caractere (mesmo comprimento); substituição de grafia disfarçada **só em tokens que misturam letras com dígitos ou símbolos** (`m0unj@r0` → `mounjaro`, mas `10K` continua `10k`).
3. **Listas da categoria** (`claim_rule` proibidas da versão) → `bloquear`. **Exceção (D18):** antes, procurar no texto normalizado as alegações permitidas da versão (`claim_rule` com `kind = permitida`). Cada ocorrência literal vira `registrar` (`reason_type = alegacao_permitida`, `rule_key` da alegação, ex.: `IN28-B6-02`) e os termos proibidos que caem **inteiramente dentro** desse trecho são descartados (com log). Paráfrase não é exceção: continua `bloquear`, e a sugestão oferece o texto literal permitido. A explicação lembra que a alegação só vale com a dose mínima do Anexo III.
4. **Padrões da H2** → `revisar`. Urgência vira `URGENCIA-VENCIDA` quando `published_since` tem mais de 7 dias; sem data, `URGENCIA` com explicação "confirme se a oferta é mesmo por tempo limitado".
5. **Condições da oferta × ficha:**
   - garantia de N dias ≠ `guarantee_days` → `bloquear COND-GARANTIA`; igual → `registrar`;
   - "vitalício", "para sempre", "acesso ilimitado" com `access_type ≠ vitalicio` → `bloquear COND-ACESSO`; "N meses/anos de acesso" diferente → `bloquear`; igual → `registrar`;
   - "pagamento único", "sem mensalidade" com `recurrence ≠ unica` → `bloquear COND-RECORRENCIA`;
   - bônus citado e `bonuses` vazio → `bloquear COND-BONUS`; bônus citado e presente → `registrar`;
   - "sem gastar nada", "100% grátis", "sem investir" com `extra_costs` não vazio → `bloquear COND-CUSTO-OCULTO`.
   - Atenção: "5 kg em 7 dias" **não** é garantia. Só conta como garantia quando o número de dias vem junto de garantia, "para testar", "dinheiro de volta" ou equivalente.
6. **Nome do produto que já é alegação:** verificado em `upsert_product_facts` (aviso para a marca) e no texto da peça.
7. **Identificação publicitária:** fora dos trechos. `disclosure = {present: bool, suggestion}` procura `#publi`, `publi`, `publicidade`, `parceria paga`, `#ad`. Não muda `overall` (todo anúncio da H2 já carregava "Patrocinado"; contar isso como achado distorceria o Teste 1).

### 11.3 Camada 2: modelo de linguagem

- **Entrada:** trechos numerados, categoria, condições da ficha, regras permitidas e proibidas da versão (com `rule_key`), achados da camada 1 (para não repetir).
- **O que pedir:** grafia disfarçada que a normalização não pegou, comparação implícita com medicamento, alegação de saúde fora da lista permitida, promessa de resultado sem número, renda implícita; extração de promessas verificáveis (atributo, valor, unidade); explicação e sugestão de reescrita para **todos** os achados.
- **Saída (esquema validado):** `findings[{excerpt, output, rule_key|null, reason_type, explanation, suggestion}]`, `promises[{excerpt, attribute, value, unit}]`.
- **Regras de fusão (código, não prompt):**
  - o modelo **não rebaixa** um achado da camada 1;
  - o modelo **só cria `bloquear`** se citar um `rule_key` proibido existente na versão; caso contrário, vira `revisar`;
  - `excerpt` que não for substring literal do texto é descartado e registrado em log;
  - com `CHECKER_USE_LLM=false` ou sem chave, o checador funciona só com a camada 1 e diz isso na resposta (`layers_used`).

---

## 12. Agente 2: classificador de devolução

### 12.1 Taxonomia (a mesma aplicada à mão nas 172 reclamações da H1)

| `cause` | `subcause` | Pesa no creator? |
|---|---|---|
| `promessa_explicita` | `diferente_do_anunciado`, `condicao_da_oferta`, `informacao_omitida`, `resultado_prometido` | Sim, só com `relation = confirma` e confiança alta |
| `promessa_expectativa` | `qualidade_abaixo` | Não. Entra no relatório como sinal fraco |
| `acesso_entrega` | `acesso_nao_liberado`, `fisico_nao_entregue`, `servico_fora_do_ar`, `login_conta`, `conteudo_removido` | Não. Vai para marca e Operações |
| `processo` | `arrependimento_sem_motivo`, `renovacao_indesejada`, `cancelamento_travado`, `reembolso_nao_processado`, `motivo_pessoal` | Não |
| `fraude` | `cobranca_nao_reconhecida`, `pagamento_fora_do_checkout`, `golpe` | Não. Vai para antifraude |
| `outros` | `outros` | Não |

**Precedência (livro de códigos da H1):** fraude > promessa > acesso > processo.
**Casos de fronteira que o prompt precisa explicitar:**
- renovação automática **não informada na venda** → `promessa_explicita/informacao_omitida`; renovação apenas indesejada → `processo/renovacao_indesejada`;
- "perdi o acesso, achei que era para sempre" → `promessa_explicita/condicao_da_oferta` (a queixa é sobre a duração prometida, não falha técnica);
- pagamento por Pix fora do checkout a pedido do vendedor → `fraude/pagamento_fora_do_checkout`;
- "o curso é fraco", "não era o que eu esperava" sem citar anúncio → `promessa_expectativa`.

### 12.2 Etapas

1. `privacy.scrub(reason_text)`: remove e-mail, CPF, telefone, número de cartão.
2. **Classificar** (modelo): `cause`, `subcause`, `buyer_belief` (`{attribute, value, unit, text}` ou nulo: o que o comprador diz que foi prometido), `channel_mentioned`, `confidence` (0–1), `explanation` (uma frase). Até 8 exemplos curtos, **só do split de desenvolvimento**.
3. **Validar:** subcausa precisa pertencer à causa; se não, vira a primeira subcausa válida e a confiança cai para no máximo 0,5.
4. **Ligar** (`refunds/linker.py`), só para `promessa_explicita`:
   - busca as `registered_promise` da peça da venda;
   - atributos de condição (`garantia`, `acesso`, `recorrencia`, `bonus`, `custo`): comparação **determinística** de valores normalizados;
   - `resultado` e `alegacao`: comparação pelo modelo (prompt curto `linker_v1`);
   - para os demais `cause`: `relation = nao_aplicavel`.
5. `needs_review = confidence < CONFIDENCE_THRESHOLD` (padrão 0,8).

### 12.3 Semântica da relação

| `relation` | Significa | Efeito |
|---|---|---|
| `confirma` | O que o comprador diz que foi prometido **corresponde** ao que está registrado na peça do creator. A promessa daquele creator está na origem da devolução. | Conta no indicador do creator se confiança ≥ limiar e não foi revertida. |
| `contradiz` | O comprador acredita em algo **diferente** do registrado (ex.: registrado "12 meses", comprador "achei que era para sempre"). A expectativa veio de outro lugar. | Não pesa no creator. Sobe como **sinal para a marca** (ex.: "vitalício" circula fora do controle dela, talvez no kit de divulgação). |
| `sem_relacao` | Queixa de promessa sem ponto de contato com nada registrado. | Não pesa no creator. Aparece no relatório. |
| `nao_aplicavel` | Causa não é `promessa_explicita`. | — |

### 12.4 Indicador e relatórios

- `taxa_devolucao` = devoluções / vendas do período (coorte pela data da venda).
- `taxa_promessa_confirmada_creator` = devoluções `promessa_explicita` + `confirma` + confiança ≥ limiar + não revertidas / vendas do creator. **Só aparece se vendas do creator no período ≥ `MIN_SALES_FOR_INDICATOR`** (padrão 30); abaixo disso, "dados insuficientes".
- Promessas mais contestadas (por `normalized_text`, só `confirma`).
- Sinais para a marca: crenças mais frequentes em `contradiz` (ex.: `acesso = vitalicio`).
- Cobertura: % de vendas com promessa registrada; % de devoluções classificadas e ligadas.
- Operação: tempo entre `refund_event.created_at` e a classificação.
- Integridade: condições anunciadas contrárias à ficha barradas antes da venda (contagem de `COND-*` bloqueados).

### 12.5 Explicação para o creator

Gerada a partir **só de dados agregados** (nunca do texto do comprador), até ~120 palavras, tom de ajuda, sem palavras de punição. Estrutura: o que voltou (número), por quê (causas), o que não tem a ver com você (acesso, processo, fraude), qual trecho mudar (excerpt da peça com `confirma`), lembrete de identificação publicitária se faltou. Sem chave ou com erro do modelo, usa um **modelo de texto fixo** com os mesmos campos.

---

## 13. Revisão humana e guardas

- Todo `bloquear` pode ser **contestado** pelo creator (`submit_review action=contestar`). Só `marca` ou `operacoes` podem `manter` ou `reverter`. O creator não resolve a própria contestação (`PAPEL_NAO_AUTORIZADO`).
- Classificações com `needs_review` entram na fila; `reclassificar` grava a nova causa e o revisor. A decisão humana fica disponível para virar exemplo do agente (exportável em `eval/reports/revisoes.csv`).
- **Nenhum** creator perde acesso, comissão ou alcance por decisão automática. Não existe código que altere comissão.
- O indicador por creator obedece ao mínimo de vendas (seção 12.4).
- O creator **nunca** vê o comprador: nenhuma saída com papel `creator` contém `reason_text`, nome, e-mail ou id de venda.

---

## 14. Gabaritos e avaliação (Teste 1 do guia)

### 14.1 Conjuntos

| Arquivo | Origem | Linhas | Campos | Contagens de conferência (o import falha se não bater) |
|---|---|---|---|---|
| `data/gold/h2_anuncios.jsonl` | Aba H2 Auditoria | 60 | `id`, `familia`, `tipo_anunciante`, `tipo_produto`, `categoria` (mapeada), `texto` (trecho anonimizado), `veredito`, `nao_conforme` (bool), `irregular_evidente` (bool), `promessa_verificavel` (bool), `data_inicio` | Saúde/estética 37, renda 12, condições 11; não conformes 33; irregular evidente 4 (S06, S22, S25, S26); verificáveis 22 |
| `data/gold/h1_reclamacoes.jsonl` | Abas Amostra 1 e 2 | 172 | `id`, `amostra`, `texto` (resumo em paráfrase), `titulo` (do slug do link no apêndice da validação H1, opcional), `causa` (taxonomia), `causa_principal` (4 classes + outros), `subcausa`, `canal`, `categoria_produto`, `tipo_produto`, `cita_anuncio` (D21) | Só `Público = Comprador`; sem P74, P81, P90 (duplicadas) e sem P50, P54 (repetem E04, E14). Acesso 59, processo 55, promessa 44 (27 explícita: 11 diferente, 9 condição, 5 omissão, 2 resultado; 17 expectativa), fraude 12, outros 2 |
| `data/gold/splits.json` | Gerado | — | `dev` / `test` por conjunto, estratificado, semente 42 (H2: 20/40; H1: 40/132) | — |

**Anonimização:** sem nome de anunciante, empresa reclamada nem link. Nomes que aparecem no texto viram `[MARCA]` ou `[PESSOA]` a partir de uma lista de substituição que fica em `data/raw/` (fora do git). Nomes de medicamentos (Mounjaro etc.) ficam: são o sinal.

### 14.2 Métricas e metas (propostas do guia)

| Agente | Conjunto | Métrica | Meta |
|---|---|---|---|
| Checador | 60 anúncios | Sensibilidade nas 4 peças com alegação proibida pela Anvisa (predição `bloquear`) | 4 de 4 |
| Checador | 60 anúncios | Kappa de Cohen no binário "indício" (pred = `bloquear` ou `revisar`; gold = não conforme) | ≥ 0,6 |
| Checador | 22 verificáveis | Promessas extraídas (recall no nível da peça + conferência manual de 10 valores) | ≥ 80% |
| Classificador | 172 compradores | Acurácia e kappa na causa principal (promessa, acesso, processo, fraude, outros) | ≥ 80% e ≥ 0,6 |
| Classificador | 44 de promessa | Acurácia do subtipo (4 explícitos + expectativa) | ≥ 70% |

Também reportar: matriz de confusão; precisão e recall de `promessa_explicita` (é o que pesa no creator, logo **precisão** importa mais); resultado por split (dev, test, total); configuração (só regras vs regras + modelo; modelo usado).

### 14.3 Recodificação cega

`scripts/blind_sample.py` sorteia 20 anúncios e 20 reclamações (semente fixa) e gera CSV **sem rótulos** em `data/gold/recodificacao/`. Lucas recodifica; `eval/agreement.py` calcula o kappa humano × humano. Se ele for baixo (< 0,6), a meta do agente cai junto, como diz o guia.

### 14.4 Vazamentos conhecidos (declarar no relatório, não esconder)

- As regras da camada 1 foram escritas a partir da própria auditoria H2. O resultado do checador na H2 é **otimista**.
- O texto da H1 é uma **paráfrase escrita por quem codificou**, que pode carregar a categoria nas palavras. Se houver tempo, rodar também só com o título da reclamação (palavras do comprador) e comparar.
- Exemplos do prompt vêm só do split `dev`; a métrica principal é a do split `test`. Depois da primeira rodada no `test`, mudanças de prompt ou regra são registradas como nova versão no relatório.

---

## 15. Privacidade (LGPD)

- `privacy.scrub` antes de gravar ou enviar ao modelo: e-mail, CPF/CNPJ, telefone, cartão → `[EMAIL]`, `[CPF]`, `[TELEFONE]`, `[CARTAO]`.
- Guardar só a categoria e o trecho necessário; relatórios agregados.
- `data/raw/` fora do git; `data/gold/` só anonimizado.
- Logs não imprimem `reason_text` completo (no máximo 80 caracteres já limpos).

---

## 16. Convenções de código

- **Nomes:** código, tabelas e colunas em inglês; enums de domínio em português sem acento; textos ao usuário em português com acento.
- **Camadas:** `mcp_server.py` e `app/` não importam `db.models` diretamente; usam `services`.
- **Erros:** exceções de `promessa.errors` com `code` e `message` em português.
- **Logs:** `logging` padrão; uma linha por decisão automática (`piece_id`, `rule_key`, `output`, `source`, `model`).
- **Testes:** `pytest -q` sem rede por padrão. Testes que chamam o modelo têm `@pytest.mark.llm` e rodam com `make test-llm`; com `LLM_OFFLINE=1` usam só o cache.
- **Prompts:** arquivos em `src/promessa/llm/prompts/`, com versão no nome (`checker_v1.md`). Mudou o prompt, sobe a versão.
- **Commits:** um por task, mensagem `T07: checador camada 2 (modelo)`.
- **Formatação:** `ruff format` e `ruff check` limpos antes de cada commit.

---

## 17. Configuração e comandos

### 17.1 `.env`

| Variável | Padrão | Uso |
|---|---|---|
| `GEMINI_API_KEY` | — | Chave da Gemini API (AI Studio). Obrigatória para a camada 2 e o classificador |
| `PROMESSA_DB_URL` | `sqlite:///var/promessa.db` | Banco |
| `CHECKER_MODEL` | `gemini-3.5-flash-lite` | Camada 2 do checador (D25) |
| `CLASSIFIER_MODEL` | `gemini-3.5-flash-lite` | Classificador e linker |
| `EXPLAINER_MODEL` | `gemini-3.5-flash-lite` | Explicação ao creator |
| `CHECKER_USE_LLM` | `true` | Desliga a camada 2 |
| `LLM_OFFLINE` | `false` | `true` = só cache; erro se não houver |
| `LLM_CACHE_DIR` | `.cache/llm` | Cache em disco |
| `CONFIDENCE_THRESHOLD` | `0.8` | Fila de revisão e indicador |
| `MIN_SALES_FOR_INDICATOR` | `30` | Mínimo de vendas para mostrar indicador por creator |
| `URGENCY_STALE_DAYS` | `7` | Urgência vencida |
| `LINK_BASE_URL` | `https://youshop.example/l/` | Link fictício |

### 17.2 `tasks.py`

Uso: `uv run python tasks.py <tarefa> [<tarefa> ...]` (em sequência; para na primeira falha). Sem argumentos, `help`.

Nos documentos, `make <x>` significa `uv run python tasks.py <x>`; `make a b c` significa `uv run python tasks.py a b c`.

| Tarefa | Faz |
|---|---|
| `setup` | `uv sync` |
| `lint` / `format` / `test` / `test-llm` | ruff (check e format); pytest sem modelo; pytest com marcador `llm` |
| `db-reset` | apaga e recria `var/promessa.db` |
| `gold` | `scripts/import_gold.py` |
| `seed` | `scripts/seed.py` (marcas, produtos, fichas v1, creators) |
| `simulate` | `scripts/simulate.py` (peças, links, vendas, devoluções) |
| `eval-checador` / `eval-classificador` / `eval` | Teste 1 |
| `mcp` | sobe o servidor MCP em stdio (`python -m promessa.mcp_server`) |
| `demo` | `scripts/demo_e2e.py` |
| `painel` | `python -m streamlit run app/painel.py` |

### 17.3 Modelo de `CLAUDE.md` (raiz do repositório)

```markdown
# Promessa Rastreável (MVP)
Antes de qualquer mudança, leia docs/CONTEXTO.md. O trabalho segue docs/PLANO.md, uma task por vez.

Regras de trabalho
- Implemente só a task pedida. Não adiante tasks futuras.
- Ao terminar, rode os critérios de aceite da task e mostre a saída. Depois, faça commit "TXX: título".
- Regras, listas e taxonomia ficam em data/rules/*.yaml. Nunca escreva termos proibidos no código.
- Nunca invente texto de norma (IN 28, RDC, Conar). Se faltar, deixe `status: pendente_transcricao` e avise.
- Lógica de negócio só em src/promessa/*/service.py. MCP e painel chamam serviços.
- Ficha, peça e review_event são imutáveis. Mudança = nova versão.
- Textos para usuário: português do Brasil, simples. Código: inglês.
- Ambiguidade: escolha a opção mais simples e registre em docs/decisoes.md.
- Sempre abra arquivos com encoding='utf-8' (leitura e escrita, inclusive CSV e YAML).
- Nunca chame executáveis do .venv; use `python -m <módulo>`.

Comandos: uv run python tasks.py <tarefa> (test | test-llm | lint | seed | simulate | eval | demo | painel | mcp). Nos documentos, `make <x>` = `uv run python tasks.py <x>`.
```

---

## 18. Decisões

### 18.1 Tomadas (podem ser revistas, com registro)

| # | Decisão | Motivo |
|---|---|---|
| D1 | A ficha é a fonte das condições do checkout. | Sem integração com o checkout real no MVP. Em produção, a ficha seria comparada com a configuração do checkout. |
| D2 | `revisar` não impede o link; a promessa vai como `em_revisao`. | O guia: "creator vê a sugestão; a marca pode aprovar". E é justamente essa promessa que pode virar devolução depois. |
| D3 | O painel chama os serviços diretamente; demo e Claude Code usam o MCP. | Velocidade. As ferramentas MCP e o painel usam os mesmos serviços, então o comportamento é idêntico. Na fase 2, o painel pode virar cliente MCP. |
| D4 | Regras oficiais são copiadas para `claim_rule` em cada versão da ficha. | Prova o que valia no dia da venda, mesmo se o YAML mudar depois. |
| D5 | Identificação publicitária não entra no `overall`. | Evita falso positivo em massa e distorção do Teste 1. Fica no briefing e no campo `disclosure`. |
| D6 | `bloquear` só com `rule_key` de lista ou ficha. | O guia define bloquear como "proibida em lista oficial ou condição contrária à ficha". O modelo sozinho no máximo sugere `revisar`. |
| D7 | Vendas e devoluções do MVP são simuladas; a avaliação dos agentes usa os dados reais das validações. | Não há dado da YouShop até a H5. |

### 18.2 Em aberto (padrão escolhido para não travar)

| Questão | Padrão no MVP |
|---|---|
| Mínimo de vendas para mostrar o indicador do creator | 30 no período (`MIN_SALES_FOR_INDICATOR`); confirmado (D16) |
| Limiar de confiança alta | 0,8; confirmado (D16) |
| Modelo final de cada agente | `gemini-3.5-flash-lite` nos três (checador, classificador e explicação), conforme `.env` (D14, D16, D25); reavaliar pelo split `dev` e registrar no relatório |
| Prazo para a marca revisar uma contestação | Não implementado; aparece a idade do item na fila |

---

## 19. Glossário

| Termo | Significado |
|---|---|
| Ficha (de promessas) | O que o produto pode prometer: condições da oferta + alegações permitidas e proibidas, com fonte e versão. |
| Condição da oferta | Garantia, tipo e duração do acesso, recorrência, bônus, custos extras. |
| Alegação | Afirmação sobre efeito ou resultado do produto ("ajuda no funcionamento muscular"). |
| Peça | Texto de um conteúdo do creator ou da marca (legenda, roteiro, transcrição). |
| Promessa registrada | Promessa verificável extraída da peça e presa à venda pelo link. |
| Briefing | Texto curto que o creator recebe ao gerar o link: pode dizer, não pode dizer, condições exatas, identificação publicitária. |
| Crença do comprador (`buyer_belief`) | O que o comprador diz que foi prometido, normalizado. |
| IN 28 | Instrução Normativa 28/2018 da Anvisa: lista fechada de alegações permitidas para suplementos (Anexo V). |
| H1–H5 | Hipóteses validadas: H1 reclamações, H2 anúncios, H3 regras, H4 ciclo, H5 dados da YouShop (pendente). |
| Teste 1 / Teste 2 | Avaliação dos agentes com gabaritos (no MVP) / piloto com creators reais (depois). |
