# Decisões

Registro curto das decisões do MVP. Cada decisão segue o formato abaixo. Uma decisão revista
ganha um novo registro que cita a anterior; registros antigos não são apagados.

```
## D<n> · <título> · <data>
**Contexto:** o que levou à decisão.
**Decisão:** o que foi escolhido.
**Consequência:** o que muda no código ou no produto.
```

As decisões D1–D7 vêm da seção 18.1 do docs/CONTEXTO.md.

## Índice

- **D1** · A ficha é a fonte das condições do checkout · 23/11/2026
- **D2** · `revisar` não impede o link · 23/11/2026
- **D3** · Painel chama serviços direto; demo e Claude Code usam MCP · 23/11/2026
- **D4** · Regras oficiais copiadas para `claim_rule` em cada versão da ficha · 23/11/2026
- **D5** · Identificação publicitária fora do `overall` · 23/11/2026
- **D6** · `bloquear` só com `rule_key` de lista ou ficha · 23/11/2026
- **D7** · Vendas e devoluções simuladas; avaliação com dados reais · 23/11/2026
- **D8** · SDK `mcp` 2.x: `FastMCP` virou `MCPServer` · 23/11/2026
- **D9** · `make` ausente na máquina de desenvolvimento (Windows) · 23/11/2026 · substituída pela D11
- **D10** · Launcher `promessa-mcp.exe` bloqueado pelo Windows · 23/11/2026
- **D11** · `tasks.py` no lugar do `Makefile` · 23/11/2026
- **D12** · `.gitattributes` e UTF-8 em todo lugar · 23/11/2026
- **D13** · `docs/fontes/` fora do git · 23/11/2026
- **D14** · Modelo de linguagem: Gemini no lugar da API do Claude · 23/11/2026
- **D15** · Árvore da seção 7 do CONTEXTO alinhada ao repositório · 23/11/2026
- **D16** · Padrões do MVP confirmados pelo Lucas · 23/11/2026
- **D17** · Alegações da IN 28 para magnésio e vitamina B6 · 23/11/2026
- **D18** · Alegação permitida literal prevalece sobre termo proibido · 23/11/2026
- **D19** · Modelo de dados: escolhas da T02 · 23/11/2026
- **D20** · Regras como dados: escolhas da T03 · 23/11/2026
- **D21** · Gabaritos: escolhas da T04 · 23/11/2026
- **D22** · Ficha de promessas: escolhas da T05 · 23/11/2026
- **D23** · Checador camada 1: escolhas da T06 · 23/11/2026
- **D24** · Cliente do modelo, camada 2 e `check_content`: escolhas da T07 · 23/11/2026
- **D25** · Checador passa a usar `gemini-3.5-flash-lite` · 23/11/2026
- **D26** · Teste 1 do checador: escolhas e resultado da v1 · 23/11/2026
- **D27** · Checkpoint 1: conferência manual e rodada v2 do checador · 23/11/2026
- **D28** · Link rastreado e revisão humana: escolhas da T09 · 23/11/2026
- **D29** · Classificador de devolução: escolhas da T10 · 23/11/2026
- **D30** · Ligação com a promessa registrada: escolhas da T11 · 23/11/2026
- **D31** · Teste 1 do classificador: escolhas e resultado da v1 · 23/11/2026
- **D32** · Classificador v2: causa restrita à taxonomia; rodada pendente por cota · 23/11/2026
- **D33** · Simulador, relatórios e explicação: escolhas da T13 · 23/11/2026
- **D34** · Rodadas depois da cota: classificador v2 e simulação real · 24/11/2026
- **D35** · Painel: escolhas da T14 · 24/11/2026
- **D36** · Demo via MCP e conexão no Claude Code: escolhas da T15 · 24/11/2026
- **D37** · Fechamento do MVP: escolhas da T16 · 24/11/2026
- **D38** · Ensaio da demo: o que pesa no creator e a expectativa no texto fixo · 24/11/2026
- **D39** · Ensaio da demo: textos e números na tela (problemas de gravidade baixa) · 24/11/2026

---

## D1 · A ficha é a fonte das condições do checkout · 23/11/2026
**Contexto:** não há integração com o checkout real da YouShop no MVP.
**Decisão:** a ficha de promessas é tratada como a fonte das condições da oferta.
**Consequência:** o checador compara a peça com a ficha. Em produção, a ficha seria comparada com a configuração do checkout.

## D2 · `revisar` não impede o link · 23/11/2026
**Contexto:** o guia diz que o creator vê a sugestão e a marca pode aprovar.
**Decisão:** trechos `revisar` não bloqueiam a geração do link; a promessa extraída vai como `em_revisao`.
**Consequência:** essas promessas ficam presas à venda e podem ser ligadas a uma devolução depois.

## D3 · Painel chama serviços direto; demo e Claude Code usam MCP · 23/11/2026
**Contexto:** velocidade de construção.
**Decisão:** o painel Streamlit importa os serviços; `demo_e2e.py` e o Claude Code passam pelo MCP.
**Consequência:** comportamento idêntico, pois ambos usam os mesmos serviços. Na fase 2, o painel pode virar cliente MCP.

## D4 · Regras oficiais copiadas para `claim_rule` em cada versão da ficha · 23/11/2026
**Contexto:** é preciso provar o que valia no dia da venda (CDC art. 30).
**Decisão:** ao criar uma versão da ficha, as regras oficiais da categoria são materializadas em `claim_rule`.
**Consequência:** mudar um YAML depois não altera o que valia para versões antigas.

## D5 · Identificação publicitária fora do `overall` · 23/11/2026
**Contexto:** todo anúncio da H2 já carregava "Patrocinado"; contar isso distorceria o Teste 1.
**Decisão:** a falta de `#publi` não entra no `overall`; aparece no briefing e no campo `disclosure`.
**Consequência:** evita falso positivo em massa.

## D6 · `bloquear` só com `rule_key` de lista ou ficha · 23/11/2026
**Contexto:** o guia define bloquear como "proibida em lista oficial ou condição contrária à ficha".
**Decisão:** o modelo sozinho no máximo sugere `revisar`; `bloquear` exige `rule_key` existente.
**Consequência:** regra de fusão em código na camada 2 do checador.

## D7 · Vendas e devoluções simuladas; avaliação com dados reais · 23/11/2026
**Contexto:** não há dado da YouShop até a H5.
**Decisão:** o simulador gera vendas e devoluções; o Teste 1 usa os gabaritos reais da H1 e da H2.
**Consequência:** as métricas dos agentes vêm de dados reais; os relatórios da demo, de dados sintéticos.

## D8 · SDK `mcp` 2.x: `FastMCP` virou `MCPServer` · 23/11/2026
**Contexto:** o CONTEXTO (seção 6) cita `FastMCP` em `mcp.server.fastmcp`. A versão estável instalada é `mcp` 2.3.0, em que esse módulo foi removido (importá-lo levanta `ModuleNotFoundError` com aviso de migração).
**Decisão:** seguir o pacote instalado, como manda o CONTEXTO: `from mcp.server.mcpserver import MCPServer`, `MCPServer("promessa-rastreavel", version=...)`, `@mcp.tool()` e `mcp.run(transport="stdio")`. Nos testes, o cliente é `mcp.Client`: recebe a instância do servidor (em memória; com `mode="legacy"` faz o handshake `initialize` e troca mensagens JSON-RPC) ou `StdioServerParameters` (subprocesso stdio).
**Consequência:** onde o CONTEXTO e o PLANO dizem `FastMCP`, leia `MCPServer`. A demo da T15 pode usar `mcp.Client(StdioServerParameters(...))` no lugar de montar `ClientSession` à mão.
**Atualização (23/11/2026):** CONTEXTO seção 6 corrigida para `MCPServer` e `mcp.Client`. O comentário da árvore da seção 7 (`mcp_server.py # FastMCP + ferramentas`) e a linha `Makefile` da mesma árvore ficaram como estavam (edição não autorizada nesta rodada); leia `MCPServer` e `tasks.py`.
**Atualização (23/11/2026):** árvore da seção 7 corrigida (D15).

## D9 · `make` ausente na máquina de desenvolvimento (Windows) · 23/11/2026 · substituída pela D11
**Contexto:** o `Makefile` é a interface de comandos do projeto, mas `make` não está instalado e instalá-lo exige mudança global na máquina.
**Decisão:** manter o `Makefile` como fonte dos comandos, com receitas portáveis (operações de arquivo via `uv run python -c`). Até o `make` ser instalado, os alvos são verificados rodando os mesmos comandos `uv run ...`.
**Consequência:** nenhum alvo depende de ferramenta Unix além do shell que o `make` já usa.

## D10 · Launcher `promessa-mcp.exe` bloqueado pelo Windows · 23/11/2026
**Contexto:** `uv run promessa-mcp` falha com "Uma política de Controle de Aplicativo bloqueou este arquivo" (os error 4551). O Windows bloqueia o `.exe` não assinado que o uv gera em `.venv/Scripts/`. `uv run python -m promessa.mcp_server` executa o mesmo `main()` e funciona (responde ao `initialize` e fica aguardando em stdio).
**Decisão:** manter o script `promessa-mcp` no `pyproject.toml` e o alvo `make mcp` como especificados, sem mudar a política da máquina. Nesta máquina, a forma que funciona é `uv run python -m promessa.mcp_server`. Os testes por stdio já usam `python -m`. Pendente com o Lucas: trocar o alvo `make mcp` e o registro no Claude Code (T15) para `python -m`, ou liberar o executável na política do Windows.
**Consequência:** até decidir, `make mcp` falha nesta máquina; o servidor e os testes funcionam.
**Status (23/11/2026): resolvida.** O comando oficial do servidor passa a ser `uv run python -m promessa.mcp_server` (tarefa `mcp` do `tasks.py`, D11). O script `promessa-mcp` fica no `pyproject.toml` por não atrapalhar em outras máquinas, mas nenhum documento ou tarefa depende dele. PLANO T15 atualizado: registro no Claude Code com `uv run --directory <repo> python -m promessa.mcp_server`.

## D11 · `tasks.py` no lugar do `Makefile` · 23/11/2026
**Contexto:** `make` não existe na máquina de desenvolvimento (Windows) e não vamos instalar nada global (D9). Os `.exe` do `.venv` podem ser bloqueados (D10).
**Decisão:** `tasks.py` na raiz, em Python puro (só biblioteca padrão), com as mesmas tarefas da seção 17.2 do CONTEXTO mais `help`. Uso: `uv run python tasks.py <tarefa> [<tarefa> ...]`, em sequência, parando na primeira falha. Ferramentas Python sempre via `sys.executable -m <módulo>`; só `setup` chama o `uv`. Subprocessos recebem `PYTHONUTF8=1` e `PYTHONIOENCODING=utf-8`. `db-reset` usa `pathlib`. O `Makefile` foi apagado.
**Consequência:** nos documentos, `make <x>` significa `uv run python tasks.py <x>` (aviso na seção 17.2 do CONTEXTO e na seção 2 do PLANO). `test-llm` trata "nenhum teste coletado" (código 5 do pytest) como sucesso enquanto não houver testes com o modelo. O pytest ganhou `pythonpath = ["."]` para os testes importarem `tasks` e `tests.mcp_helpers`.

## D12 · `.gitattributes` e UTF-8 em todo lugar · 23/11/2026
**Contexto:** no Windows, o git convertia LF em CRLF (avisos em todo `git add`) e o console quebra acentos e símbolos.
**Decisão:** `.gitattributes` com `* text=auto eol=lf` e `git add --renormalize .`. Regras novas no CLAUDE.md: sempre abrir arquivos com `encoding='utf-8'` (inclusive CSV e YAML) e nunca chamar executáveis do `.venv` (usar `python -m`).
**Consequência:** o repositório fica em LF; `ruff format --check` continua limpo.

## D13 · `docs/fontes/` fora do git · 23/11/2026
**Contexto:** o guia do MVP e as validações H1–H4 têm nomes reais de anunciantes e pessoas, com vereditos de irregularidade.
**Decisão:** `.gitignore` ignora `docs/fontes/*`, exceto `docs/fontes/README.md`, que explica o motivo.
**Consequência:** quem clona o repositório precisa copiar as fontes à mão. Nada nos gabaritos versionados (`data/gold/`) pode depender de texto que só exista nas fontes.

## D14 · Modelo de linguagem: Gemini no lugar da API do Claude · 23/11/2026
**Contexto:** o Lucas decidiu usar a API do Gemini. A chave (`GEMINI_API_KEY`) é da Gemini API (AI Studio) e funciona com o SDK `google-genai` sem Vertex AI. A listagem de modelos da chave foi consultada em 23/11/2026.
**Decisão:** trocar o SDK `anthropic` pelo `google-genai` (3.6.1) e a variável `ANTHROPIC_API_KEY` por `GEMINI_API_KEY`. Saída estruturada passa a ser a nativa do Gemini (`response_mime_type="application/json"` + `response_schema` com o modelo Pydantic), no lugar de *tool use* forçado; temperatura 0 continua. Padrões, mantendo a divisão "checador mais capaz, classificador de volume": `CHECKER_MODEL=gemini-3.6-flash`, `CLASSIFIER_MODEL` e `EXPLAINER_MODEL=gemini-3.5-flash-lite`. Fumaça em 23/11: os dois responderam a chamada simples e a estruturada (`{"ok": true}`). Alternativas observadas: `gemini-3.7-flash` respondeu 503 (alta demanda) nas duas tentativas; `gemini-3.5-flash` funcionou; `gemini-2.5-flash` aparece na listagem mas devolve 404; os `gemini-4-*` (nomes-código) não foram usados por não indicarem versão estável.
**Consequência:** CONTEXTO (seções 5, 6, 7 e 17.1), PLANO (T00, T01 e T07), README, `.env.example`, `config.py`, testes e marcador `llm` atualizados. Claude Code e Claude Desktop continuam como ferramenta de desenvolvimento e cliente MCP; só o modelo dos agentes mudou. O retry da T07 precisa cobrir 503. A escolha final de cada modelo continua pelo split `dev` (CONTEXTO 18.2).

## D15 · Árvore da seção 7 do CONTEXTO alinhada ao repositório · 23/11/2026
**Contexto:** a árvore ainda mostrava `Makefile`, `FastMCP`, *tool use* e não tinha os arquivos criados na T01/T01b.
**Decisão:** raiz nomeada como o repositório (`desafio-youshop/`, projeto `promessa-rastreavel`); `Makefile` → `tasks.py`; `.python-version` e `.gitattributes` incluídos; `.gitignore` com `docs/fontes/`; `docs/fontes/` e `data/raw/` marcados fora do git, com os nomes dos CSV e do `anon_map.yaml`; `llm/client.py` com saída estruturada do Gemini; `mcp_server.py` com `MCPServer` e `python -m`; `tests/` com `mcp_helpers.py`, `test_config.py` e `test_tasks.py`.
**Consequência:** a árvore descreve o que existe hoje e o que as tasks vão criar, sem resíduos do Makefile e do FastMCP.

## D16 · Padrões do MVP confirmados pelo Lucas · 23/11/2026
**Contexto:** item 6 da T00 pedia confirmar os padrões da seção 18.2 do CONTEXTO. (Pedido feito como "D12"; esse número já era da decisão sobre `.gitattributes`, por isso o registro é D16.)
**Decisão:** `MIN_SALES_FOR_INDICATOR=30`; limiar de confiança alta `CONFIDENCE_THRESHOLD=0.8`; modelos conforme o `.env` atual (D14): `CHECKER_MODEL=gemini-3.6-flash`, `CLASSIFIER_MODEL=gemini-3.5-flash-lite`, `EXPLAINER_MODEL=gemini-3.5-flash-lite`.
**Consequência:** `.env.example` e `config.py` já tinham esses valores. Na seção 18.2 do CONTEXTO, as linhas de 30 vendas e 0,8 ganharam "confirmado (D16)" e a linha de modelos passou a nomear os modelos do `.env`. O split `dev` ainda pode trocar um modelo, com novo registro.
**Atualização (23/11/2026):** o modelo do checador mudou para `gemini-3.5-flash-lite` (D25); 30 vendas e limiar 0,8 continuam.

## D17 · Alegações da IN 28 para magnésio e vitamina B6 · 23/11/2026
**Contexto:** item 5 da T00. O Lucas colocou `data/rules/suplemento_in28_permitidas.yaml` com o texto do Anexo V da IN 28/2018 na versão compilada, que cita alterações até a IN 284/2024. (Pedido feito como "D13"; esse número já era da decisão sobre `docs/fontes`, por isso o registro é D17.)
**Decisão:**
- As alegações permitidas são as do arquivo: 7 para magnésio e 7 para vitamina B6, mais as alegações de conteúdo ("Fonte de...", "Alto conteúdo..."). O texto é transcrição literal e não é editado por código nem por agente.
- "A vitamina B6 auxilia na função normal do sistema nervoso." fica em `pendente_confirmacao` (proposta aprovada em 2026) e **não** é tratada como permitida até o Lucas confirmar que está em vigor no texto consolidado.
- As alegações só valem se o produto atingir os valores mínimos do Anexo III (e, para "alto conteúdo", o dobro dos mínimos sem passar do máximo do Anexo IV). O suplemento fictício (`prod_magnesio`) deve declarar as doses na ficha na T05; se não declarar, essa limitação fica registrada no briefing e no relatório.
- Valores aceitos para `status`: `pendente_transcricao`, `transcrito_a_conferir`, `conferido`. O arquivo está hoje com `status: conferido` e `pagina: null`.
**Consequência:**
- TODO T03: o loader (`promessa.rules.loader`) deve validar o cabeçalho deste arquivo, aceitar os três valores de `status`, ler `constituintes[].alegacoes_permitidas` e ignorar `pendente_confirmacao` como permitida. Não havia loader na T01, então nada foi criado agora.
- Atenção para T03/T06: a IN 28 permite "A vitamina B6 auxilia no funcionamento do sistema imune.", enquanto a regra prevista `SUP-IMUN` bloqueia o tema imunidade em suplementos. A T03 precisa resolver essa sobreposição (por exemplo, não bloquear quando o trecho coincide com uma alegação permitida da ficha), para o checador não barrar uma alegação legal.
**Atualização (23/11/2026, Lucas):** texto conferido contra o PDF (comentário de `status` retirado). A página não pôde ser verificada (site da Anvisa fora do ar); `pagina: null` com essa nota. A alegação "A vitamina B6 auxilia na função normal do sistema nervoso." foi confirmada em vigor e passou, com o texto idêntico, para `alegacoes_permitidas`: B6 agora tem 8 alegações permitidas e o arquivo não tem mais `pendente_confirmacao`. O conflito com `SUP-IMUN` foi resolvido na D18.

## D18 · Alegação permitida literal prevalece sobre termo proibido · 23/11/2026
**Contexto:** a IN 28 permite "A vitamina B6 auxilia no funcionamento do sistema imune.", mas `SUP-IMUN` bloqueia o tema imunidade em suplementos (H2: "Imunidade Forte", "blindam sua saúde"). Sem regra, o checador bloquearia uma alegação legal. O mesmo pode acontecer com qualquer termo proibido que apareça dentro de uma alegação permitida.
**Decisão:** exceção determinística na camada 1, antes das listas proibidas:
- procurar, no texto normalizado (minúsculas, sem acento), cada alegação permitida da versão da ficha (`claim_rule` com `kind = permitida`, vindas do YAML da IN 28);
- cada ocorrência literal vira `registrar` (`source = regra`, `reason_type = alegacao_permitida`, `rule_key` estável da alegação, ex.: `IN28-B6-02`) e entra como promessa do tipo `alegacao`;
- termos proibidos cujo casamento cai **inteiramente dentro** do trecho permitido são descartados, com log; fora dele, a lista proibida vale normalmente;
- paráfrase não é exceção ("Vitamina B6 que turbina a sua imunidade" continua `bloquear SUP-IMUN`); a sugestão de reescrita oferece o texto literal permitido da ficha, e o creator pode contestar;
- a explicação do `registrar` lembra que a alegação só vale se o produto tiver a dose mínima do Anexo III (D17).
**Por que assim:** é a opção mais simples que não depende de afinar termos da lista proibida caso a caso, vale para qualquer sobreposição futura, mantém "determinístico antes do modelo" e não deixa o modelo rebaixar uma regra (D6). A Anvisa exige a redação aprovada, então só o texto literal ganha a exceção.
**Consequência:** CONTEXTO seções 10 e 11.2 e PLANO T03 (chaves `IN28-*`) e T06 (dois casos novos na tabela de aceite) atualizados. A implementação fica com a T03 (chaves e loader) e a T06 (exceção na camada 1).

## D19 · Modelo de dados: escolhas da T02 · 23/11/2026
**Contexto:** a T02 cria as 13 tabelas da seção 8 do CONTEXTO; alguns detalhes não estavam definidos.
**Decisão:**
- Enums em `db/enums.py` como `StrEnum` com os valores da seção 8.1 (nomes dos membros = valor em maiúsculas). No banco, texto com `CHECK` (o banco recusa valor fora do enum). `limpo` não é enum de trecho; só existe no `overall` da peça (T06).
- Enum extra `Role` (`marca`, `creator`, `operacoes`, `sistema`, seção 4) para `review_event.actor_role`. `review_event.target_type` fica como texto (ex.: `check_result`, `refund_classification`).
- `refund_classification.cause` e `subcause` são texto, não enum: a taxonomia é dado (`taxonomia_devolucao.yaml`, T03) e a validação fica no classificador (T10).
- Datas pelo tipo `UTCDateTime`: grava em UTC sem fuso (o SQLite não guarda fuso) e devolve com fuso UTC; data sem fuso na entrada é tratada como UTC.
- Ids: texto para `brand`, `creator`, `product` (ex.: `prod_treino`); uuid para `content_piece`; 8 caracteres para `tracked_link` (gerado na T09); inteiro autoincremento nas demais.
- Imutabilidade: triggers SQLite `<tabela>_no_update` e `<tabela>_no_delete` com `RAISE(ABORT, ...)` em `product_facts`, `content_piece` e `review_event`, criados junto com as tabelas; equivalente em Postgres comentado em `db/session.py`. Chaves estrangeiras ligadas (`PRAGMA foreign_keys=ON`).
- Regras de negócio da ficha (garantia ≥ 7 dias, `prazo` exige meses) **não** viram `CHECK` no banco: ficam na validação da T05, que devolve `FICHA_INVALIDA` com a explicação.
- `get_current_facts(session, product_id, at=None)` fica em `db/models.py` (consulta, não regra de negócio): maior `valid_from ≤ at`; empate fica com a maior versão; sem versão vigente, `None`.
- `db-reset`: `python -m promessa.db.session --reset` apaga o arquivo de `PROMESSA_DB_URL` e recria tabelas e triggers; recusa banco que não seja SQLite em arquivo.
**Consequência:** `refund_classification` permite mais de uma linha por devolução (sem `UNIQUE` em `refund_id`); a T10 decide se reclassificação atualiza ou cria linha. Invariantes 2 a 5 da seção 8.3 dependem dos serviços e são testadas nas tasks deles (T09, T11, T13).

## D20 · Regras como dados: escolhas da T03 · 23/11/2026
**Contexto:** a T03 cria os 7 YAML, o carregador e a normalização; alguns detalhes não estavam definidos.
**Decisão:**
- **Sintaxe de termo:** termos ficam normalizados (minúsculas, sem acento) e casam como palavra ou frase inteira; terminado em `*`, casa como prefixo (`emagrec*`). Evita que "cura" pegue "curativo". O exemplo da seção 10 do CONTEXTO passou a usar `emagrec*`.
- **Padrões:** regex sobre o texto normalizado e com a grafia disfarçada desfeita. `junto_de` exige um termo no mesmo trecho (ex.: `PRAZO-RESULTADO` só com verbo de resultado; `COS-ZONA-CINZENTA` só com "comprovado").
- **Cabeçalho:** além de `id`, `versao`, `categoria`, `fonte`, `referencia` e `nota`, os arquivos que viram `claim_rule` têm `origem` (`ANVISA`, `RDC752`, `IN28`, `CDC`), usado como `claim_rule.source` na T05. `id` precisa ser igual ao nome do arquivo.
- **`deleet`:** troca caracteres do mapa só quando algum deles está **entre duas letras** do token (sinal de disfarce). `m0unj@r0` vira `mounjaro`; `10k`, `5kg`, `b6`, `omega3`, `r$` e `@perfil` ficam iguais. A regra literal ("tokens que misturam letra e dígito") transformaria `10K` em `iok`, o que contradiz o critério da task. O mapa troca 1 caractere por 1 letra, para preservar posições.
- **Urgência vencida:** `URGENCIA` traz `rule_key_vencida: URGENCIA-VENCIDA` e a explicação própria; o limite de dias continua em `URGENCY_STALE_DAYS`.
- **IN 28:** cada constituinte ganhou `codigo` (`MAG`, `B6`) e o loader gera `IN28-<codigo>-NN` pela ordem da lista (ex.: `IN28-B6-02` = sistema imune). Alegação nova entra no fim. O texto das alegações não foi tocado; um teste guarda o hash dele.
- **Escolhas de conteúdo:** `SUP-DOENCA` usa "pressão alta", "pressão arterial" e "hipertensão" no lugar de "pressão" sozinho (evita "sem pressão"); metabolismo não entra em `SUP-EMAG`, porque a IN 28 permite "metabolismo energético" e a T07 espera `revisar` para "acorda o seu metabolismo"; "cura", "trata" e "previne" entram como pede o PLANO, com risco de ruído a medir no split `dev` (T08).
- **Taxonomia:** 5 casos de fronteira (a renovação virou dois: omitida na venda e só indesejada). Precedência: fraude, promessa explícita, expectativa, acesso, processo, outros. Exemplos escritos para ilustrar, sem texto do gabarito.
**Consequência:** o loader recusa termo não normalizado, regex inválida, `rule_key` repetido entre arquivos, arquivo ausente ou desconhecido e taxonomia inconsistente. A lógica de casamento (T06) deve usar `match_text` e a mesma sintaxe de termo.

## D21 · Gabaritos: escolhas da T04 · 23/11/2026
**Contexto:** a T04 importa os CSV da H1 e da H2. Os CSV não têm link (H1) nem uma coluna "irregular evidente" (H2), e os textos e títulos citam pessoas, cursos e plataformas.
**Decisão:**
- **Irregular evidente** = `Veredito == "Irregular evidente"` (dá exatamente S06, S22, S25, S26). `nao_conforme` = veredito diferente de "Conforme".
- **Título da H1:** vem do slug do link no apêndice de `docs/fontes/validacao-H1-reclamacoes.md` (texto antes do primeiro `_`, hífens viram espaços). Sem esse arquivo, `titulo` fica nulo. Os 172 compradores têm título.
- **Subcausa:** os rótulos da codificação manual viram a taxonomia por uma tabela no script (ex.: "sem motivo declarado" e "compra por engano" → `arrependimento_sem_motivo`; "acesso bloqueado" → `login_conta`; "servico nao entregue" → `acesso_nao_liberado`). Rótulo sem mapeamento faz o import falhar. `causa` = causa da taxonomia; `causa_principal` = as 5 classes da avaliação.
- **Campos extras na H1:** `tipo_produto` e `cita_anuncio` (as duas amostras têm), úteis para analisar erros na T12. `canal` e `categoria_produto` só existem na amostra 2; na 1 ficam nulos.
- **Anonimização:** `data/raw/anon_map.yaml` (fora do git) com pessoas → `[PESSOA]` e marcas, cursos e plataformas → `[MARCA]`. Casa sem diferença de maiúscula/acento, palavra ou frase inteira, nos campos `texto`, `tipo_produto` (H2) e `titulo` (H1). Ficam: nomes de medicamento e nomes de produto que já são alegação ("Mounjaro Natural", "Detox Seca Barriga", "Fat Red Burner", "Mega Crescimento", "Protocolo Seca/Zero Barriga"), porque são o sinal medido; marketplaces genéricos (Mercado Livre, Shopee, Correios). O import confere os 157 nomes dos apêndices (anunciantes, plataformas e empresas) e não grava se algum vazar. A revisão dos títulos achou 7 pessoas e 30 marcas/cursos fora dos apêndices; todos entraram na lista.
- **Falha sem gravar:** se uma contagem divergir ou um nome vazar, o import não grava nada e lista os ids do grupo.
- **Splits:** estratificação própria e determinística (semente 42, cota por estrato pelo maior resto), sem depender da versão do scikit-learn. H2 por (`nao_conforme`, família); H1 por `causa_principal`.
- **Amostra cega:** semente 7, só ids do split `test`; mostra só `id`, `tipo_produto`/`titulo` e `texto`, com colunas vazias para codificar. O script não sobrescreve um arquivo que já tenha codificação (só com `--force`). Roda à parte: `uv run python scripts/blind_sample.py`.
**Consequência:** `tasks.py gold` roda o import. Os gabaritos anonimizados entram no git; `data/raw/` e `docs/fontes/` continuam fora. Quem clonar sem as fontes ainda consegue avaliar os agentes, mas não consegue reimportar.

## D22 · Ficha de promessas: escolhas da T05 · 23/11/2026
**Contexto:** a T05 cria a ficha versionada, os produtos fictícios e as duas primeiras ferramentas MCP.
**Decisão:**
- **`claim_rule.payload` (JSON, coluna nova):** guarda o que a camada 1 precisa para aplicar a regra (tema, termos, padrões, `junto_de`, sugestão; nas permitidas, constituinte e condição). Sem isso a cópia da regra na versão (D4) não provaria o que valia nem serviria ao checador. `text` = explicação (proibidas) ou texto literal (permitidas).
- **O que é materializado por versão:** listas proibidas da categoria (`suplemento_proibidas`, `cosmetico_proibidas`), alegações permitidas da IN 28 (suplemento) e regras da marca. `padroes_h2` e `condicoes_oferta` valem para todos e não são copiados (a T06 lê do YAML; `COND-*` já é amarrado à ficha).
- **Regras da marca:** `rule_key` `MARCA-NN` (ou o que a marca mandar, com prefixo `MARCA-`); `source = MARCA`; proibida sai como `bloquear` por padrão (a ficha é da marca, D6); sem `termos`, o próprio texto normalizado vira o termo.
- **Validação (`FICHA_INVALIDA`):** garantia ≥ 7 dias citando o CDC art. 49; `prazo` exige meses e meses só com `prazo`; renovação automática não combina com pagamento único; nova versão não pode valer antes da anterior; enum inválido.
- **Código novo `FICHA_INEXISTENTE`:** produto existe, mas a versão pedida (ou qualquer ficha) não. `PRODUTO_INEXISTENTE` fica para produto que não existe.
- **Aviso de nome:** o nome do produto passa pelas listas proibidas da categoria, pelas regras da marca e pelos padrões da H2 ("Seca Barriga Caps" → `SUP-EMAG`). É aviso, não bloqueio.
- **Briefing:** até 150 palavras, gerado das condições e das regras materializadas. Mostra 2 alegações permitidas e o número das demais, para caber no limite; diz "sem bônus" e "sem custos extras" quando for o caso, para o creator não inventar.
- **Dose do Anexo III (D17):** a ficha não tem campo de dose. O briefing do suplemento avisa que as alegações só valem com a dose mínima da IN 28; a limitação fica registrada aqui.
- **Ferramentas MCP:** `access_type`, `recurrence`, `extra_costs` e `brand_rules` entram como texto e dicionário para que valor inválido volte como `FICHA_INVALIDA` (validação do serviço), e não como erro genérico de esquema. `DomainError` vira `ToolError`; o SDK acrescenta o prefixo "Error executing tool <nome>:" antes de `CODIGO: explicação`.
- **Sessão:** `db.session.session_scope()` (commit/rollback) sobre um engine padrão de `PROMESSA_DB_URL`, trocável por `set_default_engine` nos testes. O servidor cria as tabelas na primeira chamada.
- **Seeds:** 5 marcas, produtos e creators com nomes inventados; ficha v1 vale desde 01/10/2026 (antes do período simulado). `promessa.facts.seed.load_seed` é idempotente.
**Consequência:** a T06 aplica as `claim_rule` da versão a partir do `payload`, com `promessa.rules.match.find_hits` (mesma sintaxe de termo da D20).

## D23 · Checador camada 1: escolhas da T06 · 23/11/2026
**Contexto:** a T06 é marcada [plan]. O Lucas pediu a implementação direta; o plano foi apresentado no início da sessão e seguido.
**Decisão:**
- **Contexto da checagem:** `checker.service.build_context` lê a versão da ficha e as `claim_rule` (com `payload`) e monta um `CheckContext` (`checker/models.py`). `run_layer1(text, ctx, published_since, now)` não toca banco nem modelo.
- **Ordem por trecho:** (1) alegações permitidas da versão que aparecem literalmente viram `registrar` (`alegacao_permitida`) e protegem o trecho (D18); (2) `claim_rule` proibidas, descartando casamentos inteiros dentro de um trecho protegido (com log); (3) condições da oferta × ficha; (4) padrões da H2 (lidos do YAML, não materializados; D22).
- **Escopo do achado:** um achado por regra e trecho, com `excerpt` do primeiro ao último casamento. Nas condições, casamentos da mesma regra com o mesmo valor viram um achado ("sem mensalidade, você paga uma vez só" → um `COND-RECORRENCIA`); valores diferentes geram achados separados.
- **`reason_type`:** `alegacao_proibida` (lista, bloquear), `zona_cinzenta` (lista, revisar), `regra_da_marca`, `alegacao_permitida`, `condicao_contraria_a_ficha`, `condicao_igual_a_ficha`, e o `rule_key` em minúsculas para os padrões da H2 (`med_comparacao`, `prazo_resultado`, `urgencia_vencida`...).
- **`extracted`:** `{type, attribute, value, unit}`. `type` (`condicao_oferta`, `resultado`, `alegacao`) foi acrescentado para a T09 criar a `registered_promise` sem adivinhar. Acesso em anos vira meses; garantia em dias; bônus leva o nome do bônus da ficha quando citado.
- **Extração de resultado:** o campo novo `extrai: resultado` no `padroes_h2.yaml` marca `PRAZO-RESULTADO` e `RENDA-NUMERO`. O trecho inclui o verbo ou a palavra de renda (`junto_de`); "Secar até 5KG EM 7 DIAS" → `"5 kg em 7 dias"`; "RENDA EXTRA de 10K" → `"renda extra de 10k"`.
- **Comparações:** acesso "N meses" diferente da ficha bloqueia mesmo quando promete menos (regra literal do CONTEXTO 11.2); "sem gastar nada" só gera achado quando a ficha tem custo extra (sem custo, não há o que registrar).
- **Explicações e sugestões:** modelo de texto a partir do YAML e da ficha ("A ficha deste produto diz acesso por 12 meses. …"; `Troque por "12 meses de acesso".`). A T07 pode melhorar o texto com o modelo, sem mudar a saída.
- **Identificação publicitária:** a lista curta (`#publi`, `publi`, `publicidade`, `parceria paga`, `#ad`) ficou no código de `checker/service.py`: não é termo proibido nem regra com fonte. Não muda o `overall` (D5).
- **Nome do produto no texto da peça (11.2, item 6):** coberto pelas próprias listas; não há verificação separada.
**Consequência:** `check_content` (T07) chama `build_context` + `run_layer1`, persiste e funde com a camada 2.

## D24 · Cliente do modelo, camada 2 e `check_content`: escolhas da T07 · 23/11/2026
**Contexto:** a T07 (marcada [plan]) liga o Gemini ao checador. O Lucas pediu a implementação direta; o plano foi apresentado no início da sessão.
**Decisão:**
- **`complete_json`:** prompt em `prompts/<nome>.md` com `{{variavel}}`; saída estruturada do Gemini (`response_schema` = modelo Pydantic) validada de novo com o mesmo modelo; temperatura 0; até 3 tentativas (espera 1 s e 2 s) em rede, 429 e 5xx, e também em JSON fora do esquema; erro não transitório (ex.: 400) não repete. Versão do prompt = nome do arquivo (`checker_v1`).
- **Cache:** um JSON por chave `sha256(modelo + versão do prompt + entrada renderizada)` em `LLM_CACHE_DIR` (fora do git). `LLM_OFFLINE=true` só lê o cache e falha com `LLMOfflineMiss` se faltar.
- **Fusão (código):** `excerpt` precisa ser pedaço literal do texto (senão descarta e loga); `bloquear` só com `rule_key` proibido da versão (senão `revisar`); achado do modelo sobre trecho já marcado pela camada 1 com saída igual ou mais grave é ignorado (não rebaixa e não duplica); `registrar` do modelo é descartado (só a camada 1 confere com a ficha); promessa de resultado do modelo sem achado vira `revisar` (`resultado_sem_numero`).
- **Texto das explicações da camada 1:** continua o modelo de texto da T06. O modelo escreve explicação e sugestão só para os achados dele (reprodutível e com origem clara; princípio 5).
- **`reason_type` do modelo:** lista fechada com os mesmos nomes da camada 1 (`med_comparacao`, `prazo_resultado`...) mais `grafia_disfarcada`, `alegacao_fora_da_lista`, `resultado_sem_numero`, `renda_implicita`, `alegacao_proibida`, `outro`.
- **`check_content`:** valida creator, canal, `submitted_by`, data e peça anterior (do mesmo produto); grava a peça com a ficha vigente; roda a camada 1 e, se `CHECKER_USE_LLM` e houver chave (ou `LLM_OFFLINE`), a camada 2. Se o modelo falhar, responde só com regras e avisa em `notes`. Grava um `check_result` por achado; cada achado da resposta traz o `id` (alvo de contestação na T09). `can_generate_link = overall != bloquear`.
- **Códigos novos:** `CREATOR_INEXISTENTE` e `ENTRADA_INVALIDA`.
- **Testes:** os testes padrão nunca chamam o Gemini (fixture automática zera a chave e desliga a camada 2); os `@pytest.mark.llm` usam o `.env` real.
**Achado que precisa de decisão do Lucas (modelo do checador):** com `CHECKER_MODEL=gemini-3.6-flash`, cada chamada levou cerca de 40 s (10 min 40 s para 17 chamadas) e, logo depois, a chave recebeu 429 RESOURCE_EXHAUSTED (cota) nesse modelo; uma chamada com pensamento mínimo levou 166 s. O `gemini-3.5-flash-lite` (já usado no classificador) respondeu o mesmo prompt em cerca de 1,2 s e marcou "acorda o seu metabolismo" como `revisar alegacao_fora_da_lista`. Para a T08 (60 anúncios, duas configurações) e o simulador, o 3.6-flash fica inviável nesta chave. O padrão **não** foi trocado (D16 é decisão do Lucas).
**Consequência:** `check_content` está pronto para a T09. Antes da T08, decidir o `CHECKER_MODEL`.

## D25 · Checador passa a usar `gemini-3.5-flash-lite` · 23/11/2026
**Contexto:** na T07, o `gemini-3.6-flash` (padrão do checador desde a D14, confirmado na D16) levou cerca de 40 s por chamada e a chave recebeu 429 RESOURCE_EXHAUSTED nesse modelo (D24). O `gemini-3.5-flash-lite` respondeu o mesmo prompt do checador em cerca de 1,2 s, com o achado esperado.
**Decisão (Lucas):** `CHECKER_MODEL=gemini-3.5-flash-lite` no `.env`, no `.env.example` e no padrão de `config.py`. Classificador e explicação continuam no mesmo modelo. Revoga a escolha do checador da D14/D16; o restante da D16 (30 vendas, limiar 0,8) continua.
**Consequência:** a divisão "checador mais capaz, classificador de volume" deixa de existir no MVP; os três agentes usam o mesmo modelo. O cache antigo (chaves com `gemini-3.6-flash`) não é reaproveitado, porque o modelo entra na chave; os testes `llm` foram rodados de novo: 17 passaram ao vivo em 1 min 30 s (antes, 10 min 40 s com o 3.6-flash) e em 1,7 s com `LLM_OFFLINE=true`. Se sobrar cota, a T08 pode comparar os dois modelos no split `dev` e registrar o resultado.

## D26 · Teste 1 do checador: escolhas e resultado da v1 · 23/11/2026
**Contexto:** a T08 mede o checador contra os 60 anúncios codificados da H2.
**Decisão:**
- **Ficha genérica:** `checker.service.generic_context(categoria)` monta um `CheckContext` com as regras oficiais da categoria (mesma materialização da ficha) e sem condições (`generic=True`). Condição anunciada vira `registrar` com `reason_type = condicao_extraida`, sem comparação.
- **Predição:** indício = `overall` em `bloquear` ou `revisar`; gabarito = não conforme. Sensibilidade nas evidentes = `overall == bloquear`. Recall verificável no nível da peça = ao menos uma promessa em `extracted` (de regra ou do modelo).
- **Splits e metas:** todas as metas aparecem em dev, test e total, com ✅/❌ em cada coluna; o `test` é o principal (CONTEXTO 14.4).
- **Rodadas:** versão pela impressão digital (hash de cada YAML de `data/rules/`, do prompt e nome do modelo). Igual à anterior → mesma versão (reexecução); diferente → próxima versão, com a lista do que mudou e o texto de `--mudancas`. Uma rodada de teste só com regras feita durante o desenvolvimento e outra em que o modelo falhou em 19 peças por cota foram descartadas antes da v1 oficial.
- **Conferência manual:** 10 extrações sorteadas (semente 11) das peças verificáveis; as marcas do Lucas na última coluna são lidas do `.md` antigo e mantidas.
- **Cota do Gemini:** o plano gratuito limita 15 chamadas/min por modelo. Novo `LLM_MAX_RPM=15` (limitador entre threads no cliente) e espera do tempo pedido pela API em 429 ("retry in Ns", até 60 s). Rodada fria: 284 s; com cache: 2 s.
- **Lint:** os scripts de `eval/` podem ter linhas longas (texto do relatório em Markdown).
**Resultado da v1 (test):** 4/4 evidentes nas duas configurações; kappa 0,37 (só regras) e 0,32 (regras + modelo), meta 0,6 ❌; promessa verificável 8/17 (47%) e 12/17 (71%), meta 80% ❌. No total: só regras tem precisão alta e recall baixo do indício (86% / 55%, 15 falsos negativos); com modelo, o recall sobe e a precisão cai (91% / 67%, 15 falsos positivos).
**Achado:** mesmo com temperatura 0, o Gemini não é determinístico: uma rodada fria idêntica deu kappa 0,38 e verificável 65% (contra 0,32 e 71% da v1). A reprodutibilidade vem do cache; o número com modelo tem variação de alguns pontos e o relatório deve ser lido assim.
**Consequência:** Checkpoint 1 com o Lucas. Ajustes de regra só olhando o split `dev` e registrados como v2.

## D27 · Checkpoint 1: conferência manual e rodada v2 do checador · 23/11/2026
**Contexto:** no Checkpoint 1, o Lucas pediu que o Claude marcasse as 10 extrações e fizesse a rodada v2 com os ajustes de regra propostos, usando só evidência do split `dev`.
**Decisão:**
- **Conferência manual (marcada pelo Claude, a pedido do Lucas):** 6 certas (O05, O09, O11, R01, S04, S17) e 4 erradas (O08: atributo errado, certificado de 200 h não é resultado; R02: "3000" sem unidade, é prova social; S14: valor não normalizado; S15: perdeu o resultado). Critério: atributo e valor descrevem a promessa verificável do trecho. Commit da v1 com as marcas: `4b54fe7`.
- **Ajustes da v2 (`suplemento_proibidas.yaml@2026-11-23.2`):** `SUP-EMAG` + "controlam o apetite", "controlar o apetite" (S24, dev); `SUP-DOENCA` + "prevencao", "doenca", "doencas" (S29, dev).
- **Ficou de fora:** emagrecimento sem número em infoproduto (S03, S08, S13, S15, S18, S19). Todos os exemplos estão no `test`; não há evidência no `dev`, e ajustar com o `test` vazaria o gabarito.
- **Conferência estável:** a rodada seguinte reaproveita as mesmas 10 peças (se ainda tiverem extração); a marca só é mantida se a extração for idêntica, senão a célula pede "rever" e mostra a marca anterior.
**Resultado da v2:** kappa só regras no `dev` 0,52 → 0,71; `test` igual (0,37 só regras; 0,32 com modelo), porque os ajustes só tocam peças do `dev`. Evidentes 4/4 e promessa verificável sem mudança.
**Leitura:** a meta de kappa não foi atingida no `test`. O que falta é regra para emagrecimento em infoproduto (sem evidência no `dev`) e critério para contraexemplos educativos e zona cinzenta de cosmético (discordância de critério, para a recodificação cega). O extrator de resultado acerta 6 de 10; os erros são de normalização e de atributo.
**Consequência:** seguir para a T09. Outros candidatos com evidência no `dev` que não estavam na lista aprovada: metabolismo acelerado/"acordam o metabolismo" (S21), "compulsão" (S23), "produto mais lucrativo" (R08). Ficam para uma v3, se o Lucas quiser.

## D28 · Link rastreado e revisão humana: escolhas da T09 · 23/11/2026
**Contexto:** a T09 liga a checagem ao link e põe a decisão humana nos bloqueios.
**Decisão:**
- **Promessas:** uma `registered_promise` por achado com `extracted`; `registrar` → `registrada`; `revisar` → `em_revisao` (ou `registrada`, se a marca já aprovou); `bloquear` revertido pela marca → `registrada` (a marca disse que a condição vale). `type` vem do `extracted.type` (D23), com reserva pelo `rule_key`. Promessas iguais (tipo, atributo, valor, unidade) na mesma peça viram uma.
- **`normalized_text`:** sem acento e em minúsculas; condição = "atributo valor unidade" ("acesso 12 meses", "garantia 7 dias", "acesso vitalicio"); resultado e alegação = o valor ("5 kg em 7 dias"). É a chave das "promessas mais contestadas" (T13).
- **Link:** id base32 de 8 caracteres (40 bits aleatórios, minúsculo), único; `url = LINK_BASE_URL + id`; `facts_id` da peça; `disclosure_text` lembra o #publi (ou confirma, se a peça já tem). Chamar de novo para a mesma peça devolve o mesmo link (sem duplicar promessas).
- **Ordem das recusas:** `PECA_INEXISTENTE` → link já existente (devolve) → `BLOQUEIO_PENDENTE` (lista trecho, regra e id do achado) → `FICHA_DESATUALIZADA` (diz as versões).
- **Permissões (CONTEXTO 13):** `contestar` só em `bloquear` ainda sem decisão, pelo creator dono da peça ou pela marca; `manter`/`reverter` só marca ou Operações (o creator não resolve a própria contestação; papel `sistema` não revisa); bloqueio já decidido não é decidido de novo. `aprovar` (D2) vale para `revisar`, só marca ou Operações: o achado fica `mantido` (aceito como está) e a promessa `em_revisao` vira `registrada`. Classificação de devolução: `manter` ou `reclassificar` (payload `cause`/`subcause` validado na taxonomia; o status vira `revertido`), só marca ou Operações.
- **Fila:** bloqueios `contestado` (com texto da peça, regra, explicação, nota e autor da contestação) e classificações com confiança abaixo de `CONFIDENCE_THRESHOLD` ainda não revisadas (com só 80 caracteres do motivo, CONTEXTO 15). Mais antigos primeiro, com idade em horas.
**Consequência:** a T10 grava `refund_classification` e já encontra a fila e a reclassificação prontas.

## D29 · Classificador de devolução: escolhas da T10 · 23/11/2026
**Contexto:** a T10 (marcada [plan]) classifica o motivo do comprador na taxonomia da H1. O Lucas pediu a implementação direta; o plano foi apresentado no início da sessão.
**Decisão:**
- **`privacy.scrub`:** e-mail → `[EMAIL]`; CPF formatado e CNPJ → `[CPF]`; cartão (13 a 19 dígitos que passam no dígito verificador de Luhn) → `[CARTAO]`; telefone (com DDD, com ou sem +55) → `[TELEFONE]`; 11 dígitos seguidos viram `[CPF]` se vierem logo depois de "cpf", senão `[TELEFONE]`. Valores em reais, datas, quantidades e números de pedido ficam. `preview` mostra no máximo 80 caracteres já limpos (logs).
- **Exemplos do prompt:** 8 fixos do split `dev` da H1 (semente 42): 2 promessa explícita, 1 expectativa, 2 acesso, 2 processo, 1 fraude (sem "outros"). Seleção determinística, então o cache vale entre rodadas. Um teste confere que nenhum id é do `test`.
- **Prompt `classifier_v1`:** taxonomia, precedência e casos de fronteira lidos do YAML (nada de taxonomia no código); pede `buyer_belief` com os mesmos atributos e formatos de valor da `registered_promise` ("30"/"dias", "vitalicio", "12"/"meses", "unica"), para a T11 comparar sem conversão.
- **Validação (12.2, item 3):** subcausa fora da causa → primeira subcausa válida da causa e confiança ≤ 0,5; causa inexistente → `outros/outros` e confiança ≤ 0,5. `main_cause` traz a classe de 5 da avaliação (promessa, acesso, processo, fraude, outros).
- **Sem modelo ou com erro do modelo:** `outros/outros`, confiança 0, explicação dizendo que precisa de revisão; a classificação entra na fila (não há perda do evento).
- **`classify_refund`:** limpa o motivo antes de gravar e antes de enviar ao modelo; grava `refund_event` e `refund_classification` (relação provisória `nao_aplicavel`, ligação na T11); `needs_review = confiança < CONFIDENCE_THRESHOLD`. A resposta ganhou `classification_id` (alvo da revisão), `main_cause`, `channel_mentioned` e `notes`.
- **Testes:** fixture `make_sale` (peça checada → link → venda) para T10, T11 e T13.
**Consequência:** a T11 só precisa preencher `relation` e `linked_promise_id` a partir do `buyer_belief` e das promessas da peça da venda.

## D30 · Ligação com a promessa registrada: escolhas da T11 · 23/11/2026
**Contexto:** a T11 decide se a devolução `confirma`, `contradiz` ou não tem relação com o que a peça registrou.
**Decisão:**
- **Condições (determinístico):** a crença do comprador é comparada com as promessas registradas do mesmo atributo. Garantia compara o número; acesso normaliza para "vitalicio" ou meses (1 ano = 12); bônus aceita um texto contido no outro (ou "citado"); recorrência e custo comparam o valor normalizado. Igual → `confirma` (liga a promessa igual); diferente → `contradiz` (liga a primeira promessa do atributo); nada registrado do atributo → `sem_relacao`.
- **Resultado e alegação (modelo, `linker_v1`):** só se a peça registrou promessa desse tipo; senão `sem_relacao` sem chamar o modelo. O modelo escolhe a relação e o id; id fora da lista é descartado. Sem modelo ou com erro, `sem_relacao` com explicação pedindo revisão. Usa o `CLASSIFIER_MODEL` (CONTEXTO 17.1).
- **Promessas `em_revisao` também ligam** (o caso "5 kg em 7 dias" do guia).
- **Invariante 4:** `confirma`/`contradiz` sem promessa ligada e sem crença vira `sem_relacao`.
- **`weighs_on_creator`:** regra única do que pesa no creator (`promessa_explicita` + `confirma` + confiança ≥ limiar + não revertida). A T13 usa a mesma função. A resposta de `classify_refund` traz `weighs_on_creator` e `relation_explanation`.
- **Cenários:** `data/seeds/cenarios_relacao.yaml`, 12 casos (9 determinísticos, 3 de resultado), com a classificação esperada para testar a ligação sem modelo.
**Resultado:** 12 de 12 cenários com o classificador e o linker de verdade (`gemini-3.5-flash-lite`); 9 de 9 determinísticos sem modelo.
**Consequência:** o ciclo inteiro do guia funciona pelos serviços (ficha → peça bloqueada → correção → link → devolução `contradiz`). A T12 mede o classificador nas 172 reclamações; a T13 agrega relações e o indicador.

## D31 · Teste 1 do classificador: escolhas e resultado da v1 · 23/11/2026
**Contexto:** a T12 mede o classificador contra os 172 compradores da H1.
**Decisão:**
- **Predição:** `classify_text` (sem banco) com o resumo em paráfrase e a categoria do produto do gabarito como dica; 4 threads com o limitador de 15 chamadas/min. Reclamação em que o modelo não respondeu conta como erro (`outros`) e aparece em aviso.
- **Métricas por split:** causa principal (5 classes: acurácia, kappa, matriz), subtipo nas 44 de promessa (4 explícitos + expectativa; predição fora de promessa conta como erro), precisão e recall de `promessa_explicita`.
- **Critério de corte do guia (definição):** nas reclamações do `test` cujo gabarito é promessa, acesso ou processo, acurácia ≥ 80% e kappa ≥ 0,6 → "sim".
- **Rodada só com títulos:** opcional (`--com-titulos`), porque custa mais 172 chamadas; não rodou na v1.
- **Rodadas:** versão pela impressão digital (taxonomia, prompt, ids dos exemplos, modelo). As 3 reclamações que falharam por 503 na primeira execução foram refeitas na mesma v1 (a configuração não mudou; as outras 169 vieram do cache). Partes comuns dos dois relatórios em `eval/common.py`.
**Resultado da v1 (test):** acurácia 81% ✅, kappa 0,74 ✅, subtipo 74% ✅; corte: **sim** (83%, kappa 0,76). `promessa_explicita`: precisão 63%, recall 100% (30 previstas para 19 no gabarito): o modelo puxa para promessa, sobretudo reclamações de acesso (6 no `test`).
**Critério não atingido:** rodada sem cache em 872 s (meta 10 min). A cota gratuita (15 chamadas/min) já dá 11,5 min para 172 chamadas, e houve 503 em pico de demanda. Com cache: 13 s. Para cumprir, seria preciso cota maior (plano pago) ou chamadas em lote, o que mudaria o que está sendo medido.
**Achados para o Checkpoint 2:**
- 4 reclamações de processo viraram `outros` porque o modelo devolveu a causa "process" ou "processamento", fora da taxonomia. Restringir `cause` a uma lista fechada no esquema de saída do Gemini (enum) corrige isso; é mudança de esquema, então vira v2.
- A precisão de `promessa_explicita` (63%) é o ponto fraco: é ela que pesa no creator. O limiar de confiança e a revisão humana protegem o indicador, mas vale olhar os erros de acesso → promessa no `dev`.
- Paráfrase escrita por quem codificou: o resultado é otimista; a rodada com títulos é a contraprova.

## D32 · Classificador v2: causa restrita à taxonomia; rodada pendente por cota · 23/11/2026
**Contexto:** no Checkpoint 2, o Lucas aprovou corrigir o esquema de saída do classificador: na v1, 4 reclamações de processo viraram `outros` porque o modelo escreveu "process"/"processamento" (D31).
**Decisão:**
- O esquema enviado ao Gemini passa a ter `cause` como enum com as causas da taxonomia, gerado do YAML (`refunds.classifier.output_model`); a validação em código continua como defesa. A subcausa não foi restringida (fora do que foi aprovado).
- O prompt sobe para `classifier_v2` (mesmo texto, reforçando o nome exato da causa). Isso também é necessário porque a chave do cache não inclui o esquema: sem nova versão, a v2 reaproveitaria as respostas da v1.
**Cota diária:** durante a rodada v2, a chave atingiu a cota diária do plano gratuito para `gemini-3.5-flash-lite` (500 chamadas/dia por modelo; `GenerateRequestsPerDayPerProjectPerModel-FreeTier`; espera pedida de ~5h30). A rodada foi interrompida antes de gravar o relatório (a v1 ficou intacta); 76 das 172 reclamações já estão no cache com o `classifier_v2`. Outros modelos (`gemini-3.5-flash`, `gemini-3.6-flash`, `gemini-3.1-flash-lite`) ainda respondiam, cada um com cota própria.
**Decisão do Lucas:** esperar a cota voltar e manter o mesmo modelo (comparação v1 × v2 limpa). Enquanto isso, seguir com a T13 com testes sem rede; o simulador e a rodada v2 rodam depois de ~05h de 24/11.
**Consequência:** os testes `llm` do classificador e do linker também perdem o cache (prompt novo) e precisam de cota para a próxima rodada ao vivo. Orçamento de amanhã por modelo (500): v2 (~96) + testes `llm` (~20) + simulador (~70 devoluções) + demo.

## D33 · Simulador, relatórios e explicação: escolhas da T13 · 23/11/2026
**Contexto:** a T13 (marcada [plan]) torna visíveis os dois retornos (creator e marca). O Lucas pediu a implementação direta; o plano foi apresentado no início. A cota diária do Gemini estava esgotada (D32).
**Decisão:**
- **Dados da simulação em `data/seeds/simulacao.yaml`:** personas com peças, vendas e devoluções por motivo; 14 motivos com 5 textos cada (mais 5 variações neutras de fecho) e a classificação pretendida de cada um. 600 vendas e 76 devoluções (12,7%); mistura: acesso 37%, processo 28%, promessa 29% (explícita 24% + expectativa 5%), fraude 7%.
- **Peças reais:** cada creator passa pelo `check_content` (camada 1; `--checador-com-modelo` liga a camada 2) e pelo `register_content_and_link`; a cr_ana tem a peça bloqueada e a corrigida.
- **Dois modos:** `modelo` (padrão) classifica com o `classify_refund` real; `gabarito` usa a classificação pretendida de cada motivo, sem rede, por completers injetados (o mesmo caminho do serviço). Os testes e a conferência desta noite usam o `gabarito`. `tasks.py simulate` aceita `PROMESSA_SIMULATE_ARGS="--modo gabarito"`. O simulador recusa rodar se já houver vendas.
- **Datas:** vendas e devoluções no período (26/10 a 22/11); o `classify_refund` ganhou `at` para datar a devolução e a classificação (operação simulada = classificação na hora). Peças e links ficam com a data real de criação.
- **Relatórios (`reports/service.py`):** coorte pela data da venda; taxas por causa; indicador com `MIN_SALES_FOR_INDICATOR` usando o mesmo `weighs_on_creator` (D30); promessas mais contestadas (só `confirma`, com o trecho da peça); sinais para a marca (crenças em `contradiz`, normalizadas como as promessas); por creator (no escopo de produto); cobertura (vendas com promessa registrada, devoluções classificadas e ligadas); operação (horas até classificar); integridade (bloqueios `COND-*` nas peças do escopo). Só agregados.
- **Explicação (`reports/explain.py`):** dados agregados (`data_used`), prompt `explainer_v1`; o texto do modelo só é aceito se tiver até 130 palavras e citar o trecho a mudar; senão (ou sem chave, ou com erro) vale o modelo de texto fixo com os mesmos campos.
- **Invariante 5 (teste):** nenhuma sequência de 5 palavras do motivo aparece no que o creator vê, descontadas as que estão na própria peça do creator (o comprador pode repetir a promessa da peça).
- **Cliente do modelo:** quando a API pede espera maior que 60 s (cota diária), falha na hora (`LLMQuotaExhausted`) em vez de repetir.
**Resultado (modo gabarito):** cr_ana tem o maior indicador (4,7%) e "5 kg em 7 dias" no topo; prod_treino tem "acesso vitalicio" no topo dos sinais (7, de cr_ana e cr_bia); cr_caio tem a maior taxa de devolução (17,5%) e indicador 0; cr_duda tem "dados insuficientes"; a explicação da cr_ana cita "Secar até 5KG EM 7 DIAS" e o que não é com ela (101 palavras).
**Pendente:** rodar no modo `modelo` quando a cota voltar e conferir as personas com o classificador real.

## D34 · Rodadas depois da cota: classificador v2 e simulação real · 24/11/2026
**Contexto:** com a cota diária do Gemini de volta (07h de 24/11), rodaram as pendências da D32 e da D33.
**Resultado:**
- **Classificador v2 (`classifier_v2`, causa restrita à taxonomia):** `test` acurácia 81% → **83%**, kappa 0,74 → **0,77**, subtipo 74% (igual); precisão de `promessa_explicita` 63% → 61%. Nenhuma causa fora da taxonomia (eram 4 na v1). Critério de corte: sim. Uma reclamação levou 429 por limite por minuto e foi refeita na mesma v2 (as demais vieram do cache).
- **Modelo final (Checkpoint 2):** mantido `gemini-3.5-flash-lite` nos três agentes (D25). A comparação com outro modelo no split `dev` não foi feita, para preservar a cota do dia para a demo.
- **Simulação com o classificador real (modo `modelo`):** 600 vendas, 76 devoluções, a mesma distribuição de causas do modo gabarito; as personas batem: cr_ana com o maior indicador (4,7%) e "5 kg em 7 dias" no topo; cr_caio com a maior taxa de devolução (17,5%) e indicador 0; cr_duda com "dados insuficientes"; prod_treino com "acesso vitalicio" no topo dos sinais (7). Uma devolução levou 503 e foi refeita (resto do cache).
- **Testes `llm`:** 27 de 27 ao vivo com os prompts novos.
**Achado na explicação do modelo (cr_ana, 93 palavras):** cita o trecho certo e o que não é com ela, mas diz que "a maior parte" das devoluções veio da peça (foram 7 de 18). O filtro atual confere tamanho e trecho, não os números ditos em texto. Ajuste possível na T15/T16: instrução no prompt para não usar quantificadores ("maior parte") sem o número, ou preferir o texto fixo na demo.
**Consumo de cota no dia:** ~210 chamadas de 500 no `gemini-3.5-flash-lite`.

## D35 · Painel: escolhas da T14 · 24/11/2026
**Contexto:** a T14 monta a interface de marca, creator e Operações sobre os serviços (D3).
**Decisão:**
- **Estrutura:** `app/painel.py` (início) e `app/pages/1_Ficha.py` a `5_Avaliacao.py` (multipágina do Streamlit). Barra lateral comum em `app/painel_comum.py`: papel, creator (no papel creator), nome do revisor (marca e Operações) e período; as escolhas ficam guardadas entre páginas.
- **Só serviços:** o painel usa `promessa.*.service`, `db.session` e o carregador de regras; nada de `db.models`. Para isso, o serviço da ficha ganhou `list_products`, `list_creators` e `list_versions`.
- **Checador:** só regras por padrão, com a opção "Usar o modelo (camada 2)" (não gasta cota a cada clique). Destaque por cor do trecho mais grave (vermelho bloquear, amarelo revisar, verde registrar). Botão "Gerar link" só aparece se a checagem permite ou se o creator contestou (para tentar de novo depois da decisão da marca). A caixa "corrige a anterior" vem marcada depois de uma peça bloqueada e liga a nova peça à anterior (`parent_piece_id`).
- **Papéis:** Ficha (nova versão só para marca), Checador (creator), Fila (marca e Operações; o creator vê o aviso), Relatórios (creator: só os próprios números, o indicador, os trechos cobrados e a explicação; marca/Operações: por produto ou por creator, com sinais, cobertura e integridade), Avaliação (todos, lendo `eval/reports/*.json`).
- **Testes:** `streamlit.testing.v1.AppTest` sobre um banco em memória com seed e simulação (modo gabarito): todas as páginas nos 3 papéis, o exemplo do guia pela interface, a contestação com reversão pela fila e a ausência de texto de comprador na visão creator.
- **Lint:** arquivos de `app/` podem ter linhas longas (layout e textos da interface).
**Consequência:** a demo da página 2 e da página 4 pode ser feita ao vivo (roteiro da seção 6 do PLANO). A explicação ao creator no painel usa o modelo quando há chave (com cache); o achado da D34 sobre quantificadores continua valendo.

## D36 · Demo via MCP e conexão no Claude Code: escolhas da T15 · 24/11/2026
**Contexto:** a T15 mostra que o servidor MCP é a porta de entrada e que um agente consegue usá-lo.
**Decisão:**
- **`scripts/demo_e2e.py`:** sobe o servidor como subprocesso stdio com `mcp.Client(StdioServerParameters)` (D8) e roda os 5 passos do guia, com a chamada resumida, a resposta em destaque e uma verificação ✅/❌ por passo; termina com "Demo concluída" ou lista o que falhou (código de saída 1).
- **Banco só da demo:** `var/demo.db`, recriado e com seed a cada execução (repetível, não mistura com a simulação). A venda do passo 4 é gravada direto nesse banco: não há ferramenta MCP de venda (vendas vêm do pipeline, simulado no MVP).
- **Período do relatório no passo 5:** de 26/10 até a data de hoje, para incluir a venda da demo.
- **Logs do servidor:** `PROMESSA_LOG_LEVEL` (padrão INFO) controla o log do servidor MCP; a demo usa WARNING para a saída ficar legível.
- **Claude Code:** `claude mcp add promessa -- uv run --directory <repo> python -m promessa.mcp_server` no escopo local (privado nesta máquina; `~/.claude.json`). O servidor usa `var/promessa.db` (rodar `db-reset seed simulate` antes). Os 3 pedidos do PLANO rodaram com `claude -p` (modo não interativo), com permissão só para as ferramentas `mcp__promessa`; respostas resumidas no README. O pedido 1 grava a legenda como peça no banco (é o que o `check_content` faz).
**Resultado:** demo em ~5 s com cache (9 verificações ok); `claude mcp list` → `promessa: ... ✔ Connected`; os 3 pedidos responderam com o esperado (bloqueio das alegações e a frase literal da IN 28; trecho "Secar até 5KG EM 7 DIAS" e o que não é com a cr_ana; promessas do prod_treino separando creator e marca).
**Consequência:** todas as tarefas do `tasks.py` estão implementadas; falta o fechamento (T16).

## D37 · Fechamento do MVP: escolhas da T16 · 24/11/2026
**Contexto:** a T16 fecha o MVP para outra pessoa rodar e para a apresentação de 5 minutos.
**Decisão:**
- `docs/resultados.md` com todas as metas (✅/❌), os dois agentes por split, vazamentos, a recodificação cega não feita, a leitura e os próximos passos.
- README final: o que é, requisitos, instalação, passo a passo, demo, painel, Claude Code com os 3 pedidos, resultados, limites do MVP e notas para Windows.
- Este arquivo ganhou um índice no topo. Decisões revistas não foram apagadas: as que mudaram têm "substituída" ou "atualização" no próprio registro (ex.: D9 → D11, D16 → D25, D17 → D18).
- Verificação do clone limpo: `git clone` + `.env` + `tasks.py setup db-reset seed simulate demo` num diretório temporário, com o simulador no modo `modelo` (sem cache, chamando o Gemini).
- Tag `v0.1-mvp` local (sem push). O ensaio cronometrado da demo é do Lucas (roteiro na seção 6 do PLANO).

## D38 · Ensaio da demo: o que pesa no creator e a expectativa no texto fixo · 24/11/2026
**Contexto:** o ensaio cronometrado (Checkpoint 3) achou duas contradições na tela de Relatórios do creator (passo S5 do roteiro):
1. A tabela de causas dizia "Promessa explícita · pesa no creator: sim" com o total da causa. Para a cr_ana eram 10, mas só 7 pesam (as outras 3 contradizem a peça; D30). Para cr_caio e cr_duda, a linha dizia "sim" ao lado do texto "Nenhuma devolução veio de promessa da sua peça".
2. O texto fixo da explicação não citava as devoluções de expectativa ou qualidade: a cr_caio lia "35 voltaram" e só 33 eram explicadas.
**Decisão (a mais simples):**
- `CauseRow` ganhou `pesam_no_creator` (devoluções da causa que pesam de fato, pela mesma regra `weighs_on_creator` do indicador). `pesa_no_creator` continua dizendo se a causa *pode* pesar (taxonomia). O campo é novo e opcional na saída do `get_promise_outcome_report`.
- O painel mostra na coluna "pesa no creator": "não" (nenhuma pesa), "sim" (todas pesam) ou "7 de 10" (parte pesa). Vale para creator e marca.
- O texto fixo ganhou a frase "N esperavam do produto algo que a sua peça não prometeu (expectativa ou qualidade); isso não pesa no seu indicador." (singular com 1). As parcelas do texto agora somam o total de devoluções.
**Consequência:** a soma de `pesam_no_creator` é igual a `devolucoes_confirmadas` do indicador (teste). O prompt do modelo não mudou (o campo já ia nos dados). Os problemas de gravidade baixa do ensaio ficaram para depois.

## D39 · Ensaio da demo: textos e números na tela (problemas de gravidade baixa) · 24/11/2026
**Contexto:** o ensaio cronometrado listou oito problemas de gravidade baixa na tela e no `eval`: concordância e grupos zerados no texto fixo ("1 não têm…: 0 de acesso…"), "Fraude" na tabela do creator e "cobrança não reconhecida" no texto, "acesso vitalicio" sem acento, menu com nomes de arquivo ("painel", "Relatorios"), ponto decimal, seta de variação na métrica de devoluções, valores internos na tela ("prazo", "unica", "condicao_oferta") e rodar de novo a mesma rodada do `eval` trocando a data.
**Decisão (a mais simples em cada caso):**
- **`promessa/display.py`:** forma de exibição em pt-BR, usada pelos serviços e pelo painel: `pct`/`num`/`money` com vírgula, rótulos dos valores internos (acesso, cobrança, tipo de promessa, situação), `promise_label` (acento no vocabulário das condições da oferta: vitalício, bônus, única) e `join_pt`. Os valores gravados e as chaves de agrupamento não mudam. A regra do CONTEXTO (seção 1) continua valendo para as saídas de decisão (`bloquear`, `revisar`, `registrar`, `contradiz`); os valores descritivos ganham rótulo.
- **Relatório:** `BrandSignal` e `ContestedPromise` ganharam `rotulo` (forma com acento). `crenca` e `promessa` continuam normalizadas, porque o relatório agrupa por elas, a demo confere `crenca` e o MCP as devolve. O texto do sinal concorda com o número ("1 comprador acreditava").
- **Texto fixo da explicação:** verbo no singular com 1 (voltou, foi, tem, citou, esperava); só os grupos com devolução aparecem ("1 não tem a ver com você (cancelamento ou reembolso)"); "outros motivos" passa a aparecer quando houver.
- **"Fraude" na visão do creator:** só o painel do creator mostra "Cobrança não reconhecida", o mesmo termo da explicação; a marca e Operações continuam vendo "Fraude". O rótulo da taxonomia (`taxonomia_devolucao.yaml`) não mudou, porque ele entra no prompt do classificador: mudar o rótulo trocaria as chaves do cache (chamadas novas) e a impressão digital da avaliação.
- **Menu:** `app/painel.py` virou o ponto de entrada com `st.navigation` e títulos em português (Início, Ficha, Checador, Fila de revisão, Relatórios, Avaliação). A página inicial foi para `app/inicio.py`. Os endereços das páginas não mudaram.
- **Métrica de devoluções:** sem delta (a seta sugeria aumento); a taxa vai numa legenda.
- **`eval`:** `run_date` (em `eval/common.py`) mantém a data da primeira execução quando a rodada e todos os números são os mesmos; rodada nova ou número diferente gravam a data de agora.
**Consequência:** o prompt do modelo, as regras e a taxonomia não mudaram (o cache continua valendo). `scripts/demo_e2e.py` mostra o rótulo com acento e continua conferindo a chave normalizada.
