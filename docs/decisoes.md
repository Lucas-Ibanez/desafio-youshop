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
