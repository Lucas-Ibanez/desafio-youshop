# Promessa Rastreável · Plano de construção do MVP

> Plano em tasks ordenadas para guiar o Claude Code. Leia junto com `docs/CONTEXTO.md` (stack, pastas, modelo de dados, regras dos agentes).
> Versão 1 · 23/11/2026 · Janela: **seg 23/11, 14h → ter 24/11, 18h**.

---

## 1. O que precisa estar pronto às 18h de terça

**Definição de pronto do MVP** (cada item é verificável por um comando):

| # | Entrega | Como verificar |
|---|---|---|
| 1 | O exemplo do guia roda de ponta a ponta **pelo protocolo MCP**: ficha → peça bloqueada → peça corrigida → link → devolução classificada como `contradiz`. | `make demo` |
| 2 | Teste 1 dos dois agentes, com métricas contra as metas do guia e vazamentos declarados. | `make eval` gera `eval/reports/*.md`; resumo em `docs/resultados.md` |
| 3 | Painel com as visões de marca, creator e Operações sobre dados simulados. | `make painel` |
| 4 | Servidor MCP conectado ao Claude Code, com as 9 ferramentas chamáveis numa conversa. | `claude mcp list` mostra o servidor; conversa de exemplo no README |
| 5 | Testes passando e README que permite a outra pessoa rodar tudo. | `make lint test` |

**O que não entra:** tudo o que está em "Fora do MVP" (CONTEXTO, seção 3.2). Se surgir vontade de fazer algo dessa lista, anote em `docs/decisoes.md` como "fase seguinte" e siga.

---

## 2. Como usar este plano com o Claude Code

> Nos documentos, `make <x>` significa `uv run python tasks.py <x>`; `make a b c` significa `uv run python tasks.py a b c`.

1. Crie o repositório na T01 e copie `CONTEXTO.md` e `PLANO.md` para `docs/`. O `CLAUDE.md` da raiz segue o modelo da seção 17.3 do CONTEXTO.
2. **Uma task por sessão de trabalho.** Use este prompt, trocando o número:

   ```
   Leia docs/CONTEXTO.md e a task T06 de docs/PLANO.md.
   Implemente só a T06. Siga as decisões do CONTEXTO; se algo estiver ambíguo,
   escolha a opção mais simples e registre em docs/decisoes.md.
   Ao final, rode cada critério de aceite da T06, mostre a saída e faça commit "T06: <título>".
   ```

3. Para as tasks marcadas com **[plan]**, peça primeiro um plano ("entre em modo de planejamento e me mostre o plano antes de codar") e aprove. São as de lógica mais densa: T06, T07, T10, T13.
4. Ao fim de cada task, confira você mesmo os critérios de aceite. Se um falhar, peça a correção **antes** de seguir. Dívida aqui vira bola de neve na terça.
5. **Paralelismo opcional na terça:** depois da T09, a T14 (painel) pode correr numa segunda sessão do Claude Code em outra *worktree* do git, enquanto a primeira faz T10 a T13. O painel começa com dados do `make seed` e pega os relatórios quando a T13 chegar.

---

## 3. Cronograma

**Andamento** (atualizado em 24/11, 07:45):

| Task | Status | Evidência |
|---|---|---|
| T00 Preparação | ✅ Concluída | CSV, fontes, `.env` (chave do Gemini) e ferramentas prontos; IN 28 de magnésio e B6 conferida em `data/rules/suplemento_in28_permitidas.yaml` (D17); padrões confirmados (D16); sobreposição IN 28 × `SUP-IMUN` resolvida (D18). Página da IN 28 não verificável (site fora do ar). |
| T01 Esqueleto do repositório | ✅ Concluída | Commits `88a1956` (T01), `1471916` (T01b: `tasks.py`, MCP via `python -m`, UTF-8) e `22d6d26` (T01c: Gemini). |
| T02 Modelo de dados e banco | ✅ Concluída | 13 tabelas e 6 triggers de imutabilidade; `tests/test_models.py` com 15 testes (D19). |
| T03 Regras como dados | ✅ Concluída | 7 YAML validados pelo `promessa.rules.loader --check`; `tests/test_rules.py` com 44 testes (D20). |
| T04 Gabaritos | ✅ Concluída | 17 conferências OK; 60 anúncios e 172 compradores anonimizados; splits 20/40 e 40/132; amostra cega de 20+20 (D21). |
| T05 Ficha de promessas | ✅ Concluída | Seeds, `facts/service.py`, ferramentas `get_product_facts` e `upsert_product_facts`; 27 testes (D22). |
| T06 Checador camada 1 **[plan]** | ✅ Concluída | Os 15 casos da tabela passam; 31 testes; < 50 ms por peça (D23). Plano apresentado no início da sessão, sem aprovação prévia (pedido direto do Lucas). |
| T07 Cliente do modelo + camada 2 **[plan]** | ✅ Concluída | `check_content` via MCP; 32 testes sem rede + 17 `llm` (passam ao vivo e com `LLM_OFFLINE`). Atenção: `gemini-3.6-flash` lento (~40 s/chamada) e com cota estourada (D24); checador trocado para `gemini-3.5-flash-lite` (D25). |
| T08 Teste 1 do checador | ✅ Concluída | Rodada v1 em `eval/reports/checador_h2.md`: 4/4 evidentes; kappa test 0,37 (regras) e 0,32 (regras + modelo), meta 0,6 ❌; promessa verificável 47% e 71%, meta 80% ❌ (D26). |
| **Checkpoint 1** | ✅ Feito | Conferência manual: 6 de 10 extrações certas. Rodada v2 com ajustes de regra só do `dev`: kappa (só regras) dev 0,52 → 0,71; test igual, 0,37 (D27). |
| T09 Promessa registrada e link | ✅ Concluída | `register_content_and_link`, `list_review_queue`, `submit_review` via MCP; 22 testes (D28). |
| T10 Classificador de devolução **[plan]** | ✅ Concluída | `classify_refund` via MCP; 31 testes sem rede + 7 `llm` (passam ao vivo e com cache) (D29). |
| T11 Ligação com a promessa | ✅ Concluída | `classify_refund` preenche `relation` e `linked_promise_id`; 12 de 12 cenários com modelo; 29 testes sem rede (D30). |
| T12 Teste 1 do classificador | ✅ Concluída (1 critério ❌) | Rodada v1 em `eval/reports/classificador_h1.md`: test acurácia 81%, kappa 0,74, subtipo 74% (metas ✅); corte: sim. Rodada fria de 14,5 min (meta 10 ❌, cota do Gemini) (D31). |
| **Checkpoint 2** | ✅ Feito | v2 do classificador (causa restrita à taxonomia): test acurácia 81% → 83%, kappa 0,74 → 0,77, nenhuma causa inválida; modelo mantido `gemini-3.5-flash-lite` (D34). |
| T13 Simulador, relatórios e explicação **[plan]** | ✅ Concluída | Conferida no modo gabarito e com o classificador real: as personas batem nos dois (D33, D34). |
| T14 Painel | ✅ Concluída | 5 páginas + início, só serviços; exemplo do guia pela interface; 30 testes com o AppTest do Streamlit (D35). |
| T15 Demo via MCP + Claude Code | **Próxima** | — |
| T16 Fechamento | Não iniciada | — |

Adiantado cerca de 1h15 em relação ao cronograma abaixo (o Checkpoint 1 estava previsto para 23:30; a T09, para terça 08:00).

| Quando | Task | Quem | Duração |
|---|---|---|---|
| **Seg 14:00** | T00 Preparação | Lucas | 30 min |
| 14:00 | T01 Esqueleto do repositório | Claude Code | 30 min |
| 14:30 | T02 Modelo de dados e banco | Claude Code | 1h |
| 15:30 | T03 Regras como dados | Claude Code + Lucas | 1h15 |
| 16:45 | T04 Gabaritos: importar, anonimizar, conferir | Claude Code | 1h |
| 17:45 | T05 Ficha de promessas + produtos fictícios + 1ª ferramenta MCP | Claude Code | 1h |
| 18:45 | Pausa | — | 45 min |
| 19:30 | T06 Checador camada 1 (regras e condições da oferta) **[plan]** | Claude Code | 1h45 |
| 21:15 | T07 Cliente do modelo + checador camada 2 + `check_content` **[plan]** | Claude Code | 1h30 |
| 22:45 | T08 Teste 1 do checador (H2) | Claude Code | 45 min |
| **23:30** | **Checkpoint 1** | Lucas | — |
| Noite ou ter 7:00 | TP Recodificação cega (paralela, opcional) | Lucas | 1h |
| **Ter 08:00** | T09 Promessa registrada, link e revisão de bloqueio | Claude Code | 1h |
| 09:00 | T10 Classificador de devolução **[plan]** | Claude Code | 1h30 |
| 10:30 | T11 Ligação com a promessa (relação) | Claude Code | 1h |
| 11:30 | T12 Teste 1 do classificador (H1) | Claude Code | 45 min |
| 12:15 | Almoço | — | 45 min |
| **13:00** | **Checkpoint 2** | Lucas | — |
| 13:00 | T13 Simulador, relatórios e explicação ao creator **[plan]** | Claude Code | 1h30 |
| 14:30 | T14 Painel | Claude Code | 1h45 |
| 16:15 | T15 Demo de ponta a ponta via MCP + Claude Code | Claude Code | 45 min |
| **17:00** | **Checkpoint 3: congelar funcionalidades** | Lucas | — |
| 17:00 | T16 Fechamento: README, resultados, ensaio | Lucas + Claude Code | 45 min |
| 17:45 | Folga | — | 15 min |

**Correspondência com as etapas do guia:** Etapa 0 (gabaritos e repositório) → T00–T04 · Etapa 1 (ficha) → T05 · Etapa 2 (checador) → T06–T08 · Etapa 3 (registro na venda) → T09 · Etapa 4 (classificador e retorno) → T10–T13 · Etapa 5 (painel) → T14 · Piloto → fora do MVP.

A ordem segue o risco, como o guia pede: gabaritos primeiro (sem eles não há como medir), depois a ficha (tudo depende dela), depois os agentes; o painel por último porque é o que menos prova.

---

## 4. Prioridades e plano de corte

| Prioridade | Itens |
|---|---|
| **Obrigatório** (não se corta) | Ficha versionada e imutável · checador camada 1 com condições da oferta · registro da promessa e link com bloqueio · classificador + relação · relatório por creator e produto · ferramentas MCP · Teste 1 de H1 e H2 · `make demo` |
| **Importante** | Checador camada 2 (modelo) · explicação ao creator via modelo · painel com 4 páginas · fila de revisão |
| **Desejável** | Recodificação cega · página de Avaliação no painel · rodada da H1 só com títulos · conexão no Claude Code com conversa gravada |

**Se atrasar, corte nesta ordem:**
1. Página de Avaliação e página de Ficha no painel (ficam Checador, Fila e Relatórios).
2. Explicação ao creator via modelo (fica o modelo de texto fixo, que já é obrigatório como alternativa).
3. Rodada da H1 só com títulos.
4. Recodificação cega (vira próximo passo declarado no relatório).
5. Checador camada 2 (o checador funciona só com regras; o Teste 1 reporta "só regras").

**Checkpoints (go/no-go):**

| Checkpoint | Precisa estar verde | Se não estiver |
|---|---|---|
| **CP1 · seg 23:30** | T00–T06 aceitas; T07 e T08 pelo menos com camada 1. | Terça começa terminando T07/T08 com teto de 1h; se passar, corte o item 5. |
| **CP2 · ter 13:00** | T09–T12 aceitas; fluxo completo funciona pelos serviços (sem painel). | T14 reduzida ao corte 1; explicação vira modelo fixo (corte 2). |
| **CP3 · ter 17:00** | `make demo` e `make eval` verdes. | A partir daqui, só correção. Nada de funcionalidade nova. |

---

## 5. Tasks

Formato de cada task: **objetivo · depende de · o que fazer · arquivos · critérios de aceite · não fazer**.

---

### T00 · Preparação (Lucas)

**Objetivo:** deixar à mão tudo o que só você pode providenciar, para o Claude Code não parar.
**Depende de:** nada. Fazer em paralelo com a T01.

**O que fazer:**
1. Exportar da planilha do case, em CSV UTF-8, as abas **H2 Auditoria**, **Amostra 1** e **Amostra 2**. Salvar em `data/raw/` com os nomes `h2_auditoria.csv`, `h1_amostra1.csv`, `h1_amostra2.csv`. Confirme que existe a coluna de resumo em paráfrase da H1 e a coluna "promessa verificável" da H2.
2. Copiar o guia do MVP e as validações H1–H4 para `docs/fontes/`.
3. Criar o `.env` com `GEMINI_API_KEY`.
4. Instalar `uv`, Python 3.12 e o Claude Code; conferir `git` configurado.
5. **Até o fim da T03:** abrir o PDF da IN 28/2018 compilada (link na H2, seção 9) e transcrever **literalmente**, do Anexo V, as alegações permitidas de **magnésio** e **vitamina B6** (constituintes do suplemento fictício), com a página. Vai para `data/rules/suplemento_in28_permitidas.yaml`. ✅ *Feito: arquivo com 7 alegações permitidas para magnésio e 8 para B6, conferido contra o PDF pelo Lucas (D17). Página não verificável (site da Anvisa fora do ar). A alegação de B6 sobre o sistema nervoso foi confirmada em vigor. Sobreposição com `SUP-IMUN` resolvida na D18.*
6. Ler a seção 18 do CONTEXTO e confirmar (ou mudar) os padrões: mínimo de 30 vendas, limiar 0,8, modelos. ✅ *Feito: confirmados na D16 (30 vendas, limiar 0,8, modelos do `.env` definidos na D14).*

**Critérios de aceite:**
- [x] Os 3 CSV estão em `data/raw/` e abrem com acentos corretos. *(UTF-8 sem BOM, vírgula; 60, 98 e 95 linhas; colunas de paráfrase, promessa verificável, veredito, causa, subcausa e público presentes.)*
- [x] `.env` existe e **não** está no git. *(ignorado pelo `.gitignore`; `GEMINI_API_KEY` preenchida.)*
- [x] As alegações do Anexo V para magnésio e B6 estão transcritas com página, ou o arquivo está marcado `status: pendente_transcricao`. *(`data/rules/suplemento_in28_permitidas.yaml` transcrito e conferido, `status: conferido`; validado: campos obrigatórios presentes, 7 alegações para magnésio e 8 para B6. `pagina: null`: site da Anvisa fora do ar.)*

**Status:** ✅ concluída em 23/11. Itens 1–6 feitos (D16, D17). Sem pendências. Única ressalva: a página da IN 28 não pôde ser verificada (site fora do ar).

---

### T01 · Esqueleto do repositório

**Objetivo:** projeto que instala, testa e sobe um servidor MCP vazio.
**Depende de:** nada.

**O que fazer:**
1. Criar a estrutura de pastas da seção 7 do CONTEXTO (pastas vazias com `.gitkeep` onde preciso).
2. `pyproject.toml` com pacote `promessa` em `src/`, Python 3.12, dependências da seção 6 (`mcp`, `google-genai`, `sqlalchemy`, `pydantic`, `pyyaml`, `python-dotenv`, `streamlit`, `pandas`, `scikit-learn`) e de desenvolvimento (`pytest`, `ruff`). Script `promessa-mcp = "promessa.mcp_server:main"`.
3. `tasks.py` com as tarefas da seção 17.2 (as que ainda não têm script imprimem "ainda não implementado"). *(Era `Makefile`; trocado na D11.)*
4. `.env.example`, `.gitignore`, `CLAUDE.md` (modelo da seção 17.3), `docs/decisoes.md` com cabeçalho, `README.md` mínimo.
5. `config.py` lendo as variáveis da seção 17.1 com os padrões.
6. `mcp_server.py` com `MCPServer("promessa-rastreavel")` (o `FastMCP` do SDK `mcp` 1.x; D8), uma ferramenta `ping` que devolve `{"ok": true, "versao": "0.1.0"}` e `main()` em stdio.
7. `tests/test_mcp_tools.py` chamando `ping` por um cliente MCP (cliente em memória do SDK, se disponível; senão, cliente stdio em subprocesso).

**Critérios de aceite:**
- [x] `make setup` instala sem erro; `uv.lock` criado. *(`tasks.py setup`: 73 pacotes, `uv.lock` versionado.)*
- [x] `make lint` e `make test` passam. *(`All checks passed!`, `25 files already formatted`, `11 passed`.)*
- [x] O teste do `ping` passa **pelo protocolo MCP**, não chamando a função Python direto. *(`test_ping_em_memoria` e `test_ping_por_stdio` PASSED.)*
- [x] `git log` mostra o commit `T01: esqueleto do repositório`. *(`88a1956`, seguido de `1471916` T01b e `22d6d26` T01c.)*

**Status:** ✅ concluída em 23/11 (17:53).

**Não fazer:** nenhuma tabela, regra ou lógica de domínio.

---

### T02 · Modelo de dados e banco

**Objetivo:** as 13 tabelas do CONTEXTO (seção 8) com imutabilidade garantida pelo banco.
**Depende de:** T01.

**O que fazer:**
1. `db/enums.py` com todos os enums da seção 8.1.
2. `db/models.py` (SQLAlchemy 2.x, estilo `Mapped`) com as 13 tabelas, FKs, `UniqueConstraint(product_id, version)` em `product_facts`.
3. `db/session.py`: `get_engine()`, `get_session()`, `init_db()` (create_all) e **triggers SQLite** que fazem `RAISE(ABORT, ...)` em UPDATE e DELETE de `product_facts`, `content_piece` e `review_event`. Comente ao lado o equivalente em Postgres.
4. Função `get_current_facts(session, product_id, at=None)` que devolve a versão com maior `valid_from ≤ at`.
5. `make db-reset` funcional.

**Critérios de aceite:**
- [x] `make db-reset` cria `var/promessa.db` com 13 tabelas (`sqlite3 var/promessa.db .tables`). *(`tasks.py db-reset` → `python -m promessa.db.session --reset`; `sqlite3 .tables` lista as 13; idempotente.)*
- [x] `tests/test_models.py` cobre e passa: *(15 testes; também cobre DELETE em `product_facts` e `review_event`, UPDATE em `content_piece`, enum inválido recusado pelo banco, chave estrangeira e datas em UTC.)*
  - inserir ficha v1 e v2 do mesmo produto; v1 continua legível;
  - UPDATE em `product_facts` falha; DELETE em `content_piece` falha; UPDATE em `review_event` falha;
  - `get_current_facts` devolve v1 para uma data antes do `valid_from` da v2 e v2 depois;
  - versão duplicada para o mesmo produto falha.
- [x] Banco de teste é em memória (`sqlite://`), sem tocar `var/`. *(fixture `engine` em `tests/conftest.py`; data de modificação de `var/promessa.db` igual antes e depois da suíte.)*

**Status:** ✅ concluída em 23/11 (19:15).

**Não fazer:** serviços, seeds, validação de negócio (fica na T05).

---

### T03 · Regras como dados

**Objetivo:** todas as listas, padrões e a taxonomia em YAML versionado, com carregador validado e normalização de texto.
**Depende de:** T01. Recebe a transcrição da IN 28 da T00 (pode entrar no fim).

**O que fazer:**
1. Criar os 7 YAML da seção 10 do CONTEXTO com o cabeçalho obrigatório (`id`, `versao`, `categoria`, `fonte`, `referencia`, `nota`). Conteúdo de partida:
   - `suplemento_proibidas.yaml`: `SUP-EMAG`, `SUP-IMUN`, `SUP-FOCO`, `SUP-SEXUAL`, `SUP-DOENCA` (glicose, insulina, colesterol, fígado, inflamação, diabetes, pressão, "previne", "cura", "trata"). Termos sem acento e em minúsculas (a comparação é sobre texto normalizado).
   - `cosmetico_proibidas.yaml`: `COS-TERAPEUTICA` (`bloquear`: alopecia, queda hereditária, calvície, "trata a queda", minoxidil) e `COS-ZONA-CINZENTA` (`revisar`: "crescimento", "antiqueda" com "comprovado").
   - `padroes_h2.yaml`: `PRAZO-RESULTADO` (número + kg/quilos/medidas/dias/semanas junto de verbo de resultado: secar, perder, emagrecer, eliminar, queimar, reduzir), `RENDA-NUMERO` (renda/faturar/ganhar/lucrar + valor: `10k`, `R$ 5.000`, "6 dígitos"), `RESULTADO-GARANTIDO` ("garantido", "100% garantido", "sem erro" junto de resultado ou renda), `URGENCIA` ("só hoje", "últimas vagas", "vagas limitadas", "poucas horas", "restam N vagas"), `MED-COMPARACAO` (mounjaro, ozempic, wegovy, semaglutida, tirzepatida, sibutramina, "injeção", "caneta").
   - `condicoes_oferta.yaml`: padrões de garantia, acesso, recorrência, bônus e custo (seção 11.2, item 5, do CONTEXTO).
   - `normalizacao.yaml`: mapa de grafia disfarçada.
   - `taxonomia_devolucao.yaml`: seção 12.1 do CONTEXTO, com definição de uma linha por subcausa, a precedência e os 4 casos de fronteira.
   - `suplemento_in28_permitidas.yaml`: estrutura pronta; conteúdo da T00 (ou `status: pendente_transcricao`). O loader dá a cada alegação permitida um `rule_key` estável (`IN28-MAG-01`…, `IN28-B6-01`…), que pode ser gravado no YAML sem tocar no texto (D18).
2. `rules/schema.py` (Pydantic) e `rules/loader.py` com cache em memória e CLI `python -m promessa.rules.loader --check`.
3. `rules/normalize.py`: `normalize(text) -> str` de **mesmo comprimento** do original (minúsculas, acento removido caractere a caractere) e `deleet(token)` aplicado só a tokens que misturam letra com dígito ou símbolo.

**Critérios de aceite:**
- [x] `uv run python -m promessa.rules.loader --check` lista cada arquivo com versão e número de regras, e **falha** se um arquivo não tiver `fonte` ou `referencia`. *(7 arquivos ok; testes removem `fonte` e `referencia` de uma cópia e o `--check` sai com 1.)*
- [x] `tests/test_rules.py` passa: *(44 testes; também cobrem `deleet` em `b6`, `omega3`, `r$`, a taxonomia igual à seção 12.1, as chaves `IN28-*` e os exemplos da H2 nos padrões.)*
  - `normalize("Só HOJE!!")` → `"so hoje!!"` e `len` igual ao original;
  - `deleet("m0unj@r0")` → `"mounjaro"`; `deleet("10K")` → `"10k"`;
  - todo `rule_key` é único entre arquivos;
  - toda subcausa da taxonomia pertence a uma causa.
- [x] Nenhum termo proibido aparece em arquivo `.py` (teste com `grep` sobre `src/`). *(`test_nenhum_termo_proibido_em_src` busca os 82 termos das listas, como palavra ou prefixo, no texto normalizado de `src/**/*.py`.)*
- [x] Nenhum texto da IN 28 foi inventado: ou há transcrição com página, ou `status: pendente_transcricao`. *(Transcrição conferida pelo Lucas, `status: conferido`; página não verificável com o site fora do ar (D17). Um teste guarda o hash do texto das alegações: qualquer edição quebra o teste.)*

**Status:** ✅ concluída em 23/11.

**Não fazer:** lógica de checagem (T06).

---

### T04 · Gabaritos: importar, anonimizar, conferir

**Objetivo:** os dois conjuntos rotulados prontos para avaliar os agentes, com as contagens das validações conferidas automaticamente.
**Depende de:** T00 (CSV), T01.

**O que fazer:**
1. `scripts/import_gold.py`:
   - lê os CSV de `data/raw/`; **primeiro imprime os cabeçalhos** e mapeia colunas por nome (não por posição);
   - H2 → `data/gold/h2_anuncios.jsonl` com os campos da seção 14.1 do CONTEXTO. `categoria` mapeada do tipo de produto: suplemento/fitoterápico/manipulado → `suplemento`; cosmético → `cosmetico`; família renda → `infoproduto_renda`; demais → `infoproduto_outro`;
   - H1 → `data/gold/h1_reclamacoes.jsonl`, só compradores, sem P74, P81, P90, P50, P54. `causa_principal` ∈ `promessa`, `acesso`, `processo`, `fraude`, `outros`; `subcausa` normalizada para a taxonomia (ex.: `explicita (condicao da oferta)` → `condicao_da_oferta`; `expectativa (...)` → `qualidade_abaixo`); `titulo` extraído do slug do link (hífens viram espaços, sem o sufixo de id);
   - anonimização: remove anunciante, empresa e link; aplica a lista de substituição `data/raw/anon_map.yaml` (criar com os nomes que aparecem nos textos; Lucas revisa);
   - **confere as contagens** da seção 14.1 do CONTEXTO e falha mostrando a diferença se alguma não bater.
2. `data/gold/splits.json`: split estratificado, semente 42 (H2 por `nao_conforme` e família: 20 dev / 40 test; H1 por `causa_principal`: 40 dev / 132 test).
3. `scripts/blind_sample.py`: 20 anúncios + 20 reclamações do split `test`, semente 7, em CSV sem rótulos em `data/gold/recodificacao/`, com colunas vazias para a codificação.

**Critérios de aceite:**
- [x] `make gold` termina com uma tabela de conferência em que **todas** as linhas estão OK: *(17 linhas OK.)* 60 anúncios (37/12/11; 33 não conformes; 4 irregular evidente = S06, S22, S25, S26; 22 verificáveis) e 172 compradores (59/55/44/12/2; 27 explícitas = 11/9/5/2; 17 expectativa).
- [x] Se uma contagem não bater, o script **não corrige o número**: aponta as linhas divergentes para investigar a exportação. *(Não grava nada e lista os ids do grupo; testado em `tests/test_gold.py`.)*
- [x] `grep` por 10 nomes de anunciantes e empresas do apêndice da H2 e da H1 em `data/gold/*.jsonl` não encontra nada. *(0 ocorrências; o import também confere os 157 nomes dos apêndices e falha se algum vazar.)*
- [x] `data/raw/` e `anon_map.yaml` estão no `.gitignore`. *(`git check-ignore`: regra `data/raw/*`.)*
- [x] Os CSV de recodificação existem e não têm coluna de rótulo preenchida. *(`data/gold/recodificacao/h2_recodificar.csv` e `h1_recodificar.csv`, 20 linhas cada, colunas de codificação vazias.)*

**Status:** ✅ concluída em 23/11.

**Não fazer:** avaliar agentes (T08, T12).

---

### T05 · Ficha de promessas, produtos fictícios e primeiras ferramentas MCP

**Objetivo:** a marca consegue declarar e versionar a ficha, e o creator recebe o briefing, pelas ferramentas MCP.
**Depende de:** T02, T03.

**O que fazer:**
1. `data/seeds/marcas_produtos.yaml` com 5 produtos fictícios, cada um espelhando um padrão real das validações:

   | `product_id` | Nome | Categoria | Ficha v1 | Padrão real que espelha |
   |---|---|---|---|---|
   | `prod_treino` | Treino em Casa 12M | `infoproduto_outro` | garantia 7; `prazo` 12 meses; `unica`; bônus ["E-book de receitas"]; sem custos | Vitalício que acabou e garantia 30×7 (H1); "5 kg em 7 dias" (H2). É o exemplo do guia. |
   | `prod_magnesio` | Magnésio + B6 Vitalis | `suplemento` | garantia 30; `nao_aplica`; `unica` | Suplemento com alegação de emagrecimento, imunidade, foco (H2: 12 de 13 irregulares). |
   | `prod_capilar` | Fortis Shampoo Fortalecedor | `cosmetico` | garantia 7; `nao_aplica`; `unica` | "Previne a queda hereditária" (H2). |
   | `prod_canal` | Canal Sem Rosto | `infoproduto_renda` | garantia 7; `vitalicio`; `unica`; custos extras [ferramenta de voz e edição, R$ 97/mês] | Canal dark com custo não informado (H1) e "renda extra de 10K" (H2). |
   | `prod_ingles` | Inglês Fluente Club | `infoproduto_outro` | garantia 7; `assinatura`; `mensal`; renovação automática | Renovação não informada e "pagamento único" falso (H1). |

   E `data/seeds/creators.yaml` com `cr_ana`, `cr_bia`, `cr_caio`, `cr_duda`, `cr_eli`.
2. `facts/service.py`:
   - `create_facts_version(...)`: valida (`guarantee_days ≥ 7`; `prazo` exige meses; enums), cria nova versão, **materializa** em `claim_rule` as regras oficiais da categoria (com `reference = arquivo@versao`) e as `brand_rules`; verifica se o **nome do produto** contém termo proibido da categoria e devolve `warnings`;
   - `get_facts(product_id, version=None)`;
   - `build_briefing(facts)`: até ~150 palavras, com "Condições exatas" (garantia, acesso, cobrança, bônus, custos extras), "Pode dizer" (permitidas), "Não pode dizer" (temas proibidos em linguagem simples), "Identifique como publicidade: use #publi".
3. `scripts/seed.py` e `make seed`.
4. Ferramentas MCP `get_product_facts` e `upsert_product_facts` (finas, chamando o serviço).

**Critérios de aceite:**
- [x] `make db-reset seed` carrega 5 marcas, 5 produtos, 5 fichas v1 e 5 creators. *(e 22 regras materializadas: 5 `SUP-*` + 15 `IN28-*` no magnésio, 2 `COS-*` no capilar.)*
- [x] `get_product_facts("prod_magnesio")` pelo cliente MCP devolve as regras `SUP-*` com `source` e `reference` preenchidos. *(`ANVISA`, `suplemento_proibidas.yaml@2026-11-23`; testado em memória e por stdio.)*
- [x] `upsert_product_facts` em `prod_treino` cria v2; `get_product_facts("prod_treino", version=1)` ainda devolve a v1 intacta. *(resposta da v1 idêntica antes e depois.)*
- [x] Ficha com `guarantee_days = 5` é recusada com `FICHA_INVALIDA` citando o CDC art. 49. *("FICHA_INVALIDA: A garantia precisa ser de pelo menos 7 dias (CDC art. 49, direito de arrependimento). Recebido: 5 dias.")*
- [x] Produto hipotético chamado "Seca Barriga Caps" (categoria suplemento) gera `warning` com `SUP-EMAG`. *(pelo serviço e pelo MCP.)*
- [x] O briefing de `prod_treino` contém "7 dias", "12 meses" e "#publi", e não passa de 150 palavras. *(62 palavras; os 5 briefings ficam entre 62 e 107.)*

**Status:** ✅ concluída em 23/11 (20:05).

**Não fazer:** checagem de peças (T06).

---

### T06 · Checador camada 1: regras determinísticas e condições da oferta **[plan]**

**Objetivo:** checagem sem modelo, rápida e explicável, que já resolve os casos de lista e de condição da oferta.
**Depende de:** T03, T05.

**O que fazer:**
1. `checker/segment.py`: trechos por frase e quebra de linha, com `(start, end)` no texto original.
2. `checker/deterministic.py`: aplica, sobre o texto normalizado (CONTEXTO 11.2), as `claim_rule` proibidas da versão da ficha e os padrões da H2. Produz `Finding` (modelo Pydantic com os campos do formato da seção 9 do CONTEXTO), com explicação e sugestão em **modelo de texto** por `rule_key` (o modelo de linguagem melhora isso na T07).
3. `checker/offer_conditions.py`: extrai garantia, acesso, recorrência, bônus e custo e compara com a ficha (regras do item 5 da seção 11.2), com `extracted` normalizado. "N dias" só é garantia com contexto de garantia.
4. `checker/service.py` (parte 1): `run_layer1(text, facts, published_since)` → findings + `overall` + `disclosure`. Sem persistência ainda (vem na T07).

**Critérios de aceite** (`tests/test_checker_deterministic.py`, tabela abaixo como teste parametrizado):

| Texto | Produto | Esperado |
|---|---|---|
| "acesso vitalício e 30 dias para testar" | `prod_treino` | 2 × `bloquear` (`COND-ACESSO`, `COND-GARANTIA`) |
| "12 meses de acesso, 7 dias de garantia" | `prod_treino` | 2 × `registrar`; `extracted` = acesso 12 meses, garantia 7 dias |
| "Secar até 5KG EM 7 DIAS" | `prod_treino` | `revisar` `PRAZO-RESULTADO`; `extracted` resultado "5 kg em 7 dias"; **nenhum** `COND-GARANTIA` |
| "veja os resultados melhores que m0unj@r0" | `prod_treino` | `revisar` `MED-COMPARACAO` |
| "bloqueador de açúcar que seca barriga e firma pele em tempo recorde" | `prod_magnesio` | ao menos `bloquear` `SUP-EMAG` |
| "Imunidade Forte: nutrientes que blindam sua saúde" | `prod_magnesio` | `bloquear` `SUP-IMUN` |
| "A vitamina B6 auxilia no funcionamento do sistema imune." | `prod_magnesio` | `registrar` (alegação permitida da IN 28); **nenhum** `SUP-IMUN` (D18) |
| "Vitamina B6 que turbina a sua imunidade" | `prod_magnesio` | `bloquear` `SUP-IMUN`; sugestão com o texto literal permitido (D18) |
| "previne a queda hereditária" | `prod_capilar` | `bloquear` `COS-TERAPEUTICA` |
| "tenha uma RENDA EXTRA de 10K" | `prod_canal` | `revisar` `RENDA-NUMERO` |
| "comece do zero, sem gastar nada" | `prod_canal` | `bloquear` `COND-CUSTO-OCULTO` |
| "sem mensalidade, você paga uma vez só" | `prod_ingles` | `bloquear` `COND-RECORRENCIA` |
| "DESCONTO INÉDITO, Só hoje!!" com `published_since` = 2026-01-08 | `prod_ingles` | `revisar` `URGENCIA-VENCIDA` |
| "Ganhe o e-book de receitas de bônus" | `prod_treino` | `registrar` `COND-BONUS` |
| "Treino de 20 minutos para fazer em casa" | `prod_treino` | nenhum achado; `overall = limpo` |

- [x] Todos os casos acima passam. *(`tests/test_checker_deterministic.py`, 15 casos parametrizados.)*
- [x] Todo `bloquear` tem `rule_key` que existe em `claim_rule` da versão ou é `COND-*`.
- [x] `span` de cada achado recorta exatamente o `excerpt` no texto original.
- [x] `disclosure.present = false` para os textos acima e `true` para "... #publi". *(e o `overall` não muda com o #publi, D5.)*
- [x] A camada 1 roda em menos de 50 ms por peça (teste com `time.perf_counter`). *(inclusive numa peça com os 15 casos juntos.)*

**Status:** ✅ concluída em 23/11 (20:10).

**Não fazer:** chamar modelo; gravar no banco.

---

### T07 · Cliente do modelo, checador camada 2 e `check_content` **[plan]**

**Objetivo:** o checador completo, persistido e exposto via MCP, com o modelo cobrindo o que a regra não pega.
**Depende de:** T06.

**O que fazer:**
1. `llm/client.py`: `complete_json(prompt_name, variables, output_model, model)`:
   - monta a mensagem a partir de `prompts/<prompt_name>.md`;
   - obriga saída estruturada pelo Gemini (`response_mime_type="application/json"` e `response_schema=output_model`, Pydantic) e valida a resposta com o próprio `output_model`;
   - temperatura 0; até 3 tentativas com espera crescente em erro de rede, limite (429) ou indisponibilidade (503, comum no Gemini em pico de demanda);
   - **cache em disco** pela chave `sha256(modelo + versão do prompt + entrada)`; com `LLM_OFFLINE=1`, só cache (erro claro se faltar);
   - registra em log modelo, versão do prompt, tokens e tempo.
2. `prompts/checker_v1.md` com as instruções da seção 11.3 do CONTEXTO: trechos numerados, ficha resumida, listas com `rule_key`, achados da camada 1, o que procurar, e a regra "use `bloquear` só citando um `rule_key` proibido da lista".
3. `checker/llm_layer.py` e as **regras de fusão** em código (seção 11.3): não rebaixar camada 1; `bloquear` sem `rule_key` válido vira `revisar`; `excerpt` que não é substring literal é descartado e logado.
4. `checker/service.py` (parte 2): `check_content(...)` cria o `content_piece` (com `facts_id` vigente e `parent_piece_id`), roda camada 1 e, se `CHECKER_USE_LLM`, camada 2; grava os `check_result` com `source`, `model`, `prompt_version`; devolve a resposta da seção 9 com `layers_used` e `can_generate_link`.
5. Ferramenta MCP `check_content`.

**Critérios de aceite:**
- [x] Sem chave ou com `CHECKER_USE_LLM=false`, `check_content` funciona só com regras e responde `layers_used = ["regras"]`. *(e com o modelo fora do ar cai para só regras, com aviso em `notes`.)*
- [x] Testes com modelo simulado (*mock*), sem rede: *(`tests/test_check_content.py` e `tests/test_llm_client.py`.)*
  - o modelo tenta `bloquear` sem `rule_key` → gravado como `revisar`;
  - o modelo devolve `excerpt` inexistente no texto → descartado e logado;
  - o modelo tenta rebaixar um `bloquear` da camada 1 → ignorado.
- [x] Testes `@pytest.mark.llm` (rodam com `make test-llm`): *(17 passaram com `gemini-3.6-flash` em 10 min 40 s.)*
  - "esse chá dispensa a caneta da farmácia" em `prod_treino` → `revisar` com `reason_type` de comparação com medicamento;
  - "acorda o seu metabolismo" em `prod_magnesio` → `revisar` (alegação fora da lista permitida);
  - os casos da T06 continuam com a mesma saída ou mais grave.
- [x] Segunda execução dos testes `llm` com `LLM_OFFLINE=1` passa (cache funciona). *(17 passaram em 1,6 s.)*
- [x] O exemplo do guia pelo cliente MCP: peça 1 ("acesso vitalício e 30 dias para testar") → `can_generate_link = false`; peça 2 com `parent_piece_id` ("12 meses de acesso, 7 dias de garantia") → `can_generate_link = true`.
- [x] `content_piece` e `check_result` gravados; `model` e `prompt_version` preenchidos nos achados do modelo.

**Status:** ✅ concluída em 23/11 (20:30). Plano apresentado no início da sessão (pedido direto do Lucas).

**Não fazer:** gerar link (T09).

---

### T08 · Teste 1 do checador (H2)

**Objetivo:** medir o checador contra os 60 anúncios codificados, com honestidade sobre os vazamentos.
**Depende de:** T04, T07.

**O que fazer:**
1. `eval/metrics.py`: acurácia, kappa de Cohen, precisão e recall, matriz de confusão, IC de Wilson.
2. `eval/eval_checker.py`:
   - para cada anúncio, uma **ficha genérica** da categoria do gabarito (condições nulas: o checador só extrai e registra condições, não compara);
   - roda duas configurações: **só regras** e **regras + modelo**;
   - métricas da seção 14.2 do CONTEXTO, por split (`dev`, `test`, total);
   - grava `eval/reports/checador_h2.md`, `.json` e `erros_checador.csv` (id, gold, predito, trechos e regras).
3. O `.md` começa com: data, versões dos prompts e das regras, modelo, e a seção "Vazamentos conhecidos" (CONTEXTO 14.4).

**Critérios de aceite:**
- [x] `make eval-checador` termina em menos de 5 minutos (e em segundos com cache). *(284 s sem cache, limitado pela cota de 15 chamadas/min; 2 s com cache.)*
- [x] O relatório mostra cada meta do guia com o valor obtido e ✅ ou ❌. **Não esconder ❌.** *(por configuração e por split: dev, test e total.)*
- [x] A sensibilidade nas 4 peças irregulares evidentes lista as 4 pelo id com o resultado de cada uma. *(S06, S22, S25, S26: `bloquear` nas duas configurações.)*
- [x] O recall de promessa verificável vem acompanhado de 10 extrações sorteadas para conferência manual (Lucas marca certo ou errado no próprio `.md`). *(as marcas são preservadas nas próximas rodadas.)*
- [x] A primeira rodada no split `test` fica registrada como "v1" no relatório; ajustes posteriores geram "v2" com o que mudou. *(versão pela impressão digital de regras, prompt e modelo; histórico no `.md` e no `.json`.)*

**Status:** ✅ concluída em 23/11 (21:40).

**→ Checkpoint 1 (Lucas):** olhar o relatório e os erros. Se o kappa estiver muito abaixo de 0,6, ver nos erros se o problema é regra faltando (corrigir no YAML, só olhando o split `dev`) ou discordância de critério (anotar para a recodificação cega).

---

### TP · Recodificação cega (Lucas, paralela, desejável)

**Objetivo:** saber quanto dois humanos concordam, para calibrar as metas dos agentes, como o guia recomenda.
**Depende de:** T04.

**O que fazer:** codificar os 20 anúncios e as 20 reclamações de `data/gold/recodificacao/` **sem olhar** a codificação original, usando o livro de códigos das validações. Depois, `eval/agreement.py` (Claude Code escreve em 15 minutos) calcula o kappa humano × humano.

**Critérios de aceite:**
- [ ] `uv run python eval/agreement.py` mostra kappa para H2 (indício sim/não) e H1 (causa principal).
- [ ] O resultado entra em `docs/resultados.md`. Se ficar abaixo de 0,6, as metas do agente são relidas à luz disso.

---

### T09 · Promessa registrada, link rastreado e revisão de bloqueio

**Objetivo:** o elo central: o link só nasce depois da checagem e carrega a promessa. Contestação com decisão humana.
**Depende de:** T07.

**O que fazer:**
1. `links/service.py` → `register_content_and_link(piece_id, actor_type="humano")`:
   - erro `PECA_INEXISTENTE`;
   - erro `BLOQUEIO_PENDENTE` se houver `bloquear` com `review_status ≠ revertido` (lista os trechos);
   - erro `FICHA_DESATUALIZADA` se a ficha vigente do produto mudou depois da checagem;
   - cria `registered_promise` para cada achado com `extracted`: `registrar` → `registrada`; `revisar` → `em_revisao`; tipo e atributo a partir do `rule_key` e do `extracted`;
   - cria `tracked_link` (id base32 de 8 caracteres, `url = LINK_BASE_URL + id`, `facts_id` da peça, `disclosure_text` com a sugestão de "#publi").
2. `review/service.py`: `list_review_queue(kind)`, `submit_review(...)` com as permissões da seção 13 do CONTEXTO; grava `review_event` e atualiza `review_status`.
3. Ferramentas MCP `register_content_and_link`, `list_review_queue`, `submit_review`.

**Critérios de aceite** (`tests/test_links.py`):
- [x] Passos 2 e 3 do exemplo do guia: peça bloqueada → `BLOQUEIO_PENDENTE`; peça corrigida → link criado com 2 promessas `registrada` (acesso 12 meses, garantia 7 dias). *(o erro lista os dois trechos; também pelo MCP.)*
- [x] Peça com "5 kg em 7 dias" + "7 dias de garantia" → link criado; promessa de resultado `em_revisao` e garantia `registrada`.
- [x] Contestação: creator `contestar` → item aparece na fila; creator tentando `reverter` → `PAPEL_NAO_AUTORIZADO`; marca `reverter` → link liberado; `review_event` tem 2 linhas com ator e papel.
- [x] Nova versão da ficha depois da checagem → `FICHA_DESATUALIZADA`.
- [x] Invariantes 2 e 3 da seção 8.3 do CONTEXTO testados.

**Status:** ✅ concluída em 23/11 (22:25).

**Não fazer:** vendas e devoluções (T10, T13).

---

### T10 · Classificador de devolução **[plan]**

**Objetivo:** classificar o motivo do comprador na taxonomia da H1, protegendo dados pessoais.
**Depende de:** T03, T07 (cliente do modelo), T04 (exemplos do split `dev`).

**O que fazer:**
1. `privacy.py`: `scrub(text)` para e-mail, CPF/CNPJ, telefone e cartão.
2. `prompts/classifier_v1.md`: taxonomia injetada do YAML, precedência, os 4 casos de fronteira (CONTEXTO 12.1), até 8 exemplos do split `dev` (balanceados por causa), pedido de `buyer_belief` normalizado (atributos iguais aos de `registered_promise`).
3. `refunds/classifier.py`: `classify_text(text, product_category) -> Classification` (sem banco, para reuso na avaliação), com a validação de subcausa (CONTEXTO 12.2, item 3).
4. `refunds/service.py`: `classify_refund(sale_id, reason_text, type)` grava `refund_event` (texto limpo) e `refund_classification` (relação provisória `nao_aplicavel`; a ligação vem na T11), `needs_review` pelo limiar.
5. Ferramenta MCP `classify_refund`. Para testar agora, uma função auxiliar de teste cria `sale` ligada a um link.

**Critérios de aceite:**
- [x] `tests/test_privacy.py`: "meu cpf 123.456.789-00 e email ana@x.com" → sem CPF nem e-mail. *(→ "meu cpf [CPF] e email [EMAIL]"; valores, datas e números de pedido ficam.)*
- [x] Testes `@pytest.mark.llm`: *(os 7 passaram com `gemini-3.5-flash-lite`, incluindo as crenças garantia 30 e acesso vitalício.)*

  | Motivo | Causa / subcausa esperada |
  |---|---|
  | "Não reconheço essa cobrança no meu cartão" | `fraude` / `cobranca_nao_reconhecida` |
  | "Paguei há 5 dias e até hoje não liberaram o acesso" | `acesso_entrega` / `acesso_nao_liberado` |
  | "Me arrependi, quero cancelar" | `processo` / `arrependimento_sem_motivo` |
  | "Anunciaram garantia de 30 dias, mas só aceitam pedido em 7" | `promessa_explicita` / `condicao_da_oferta`, crença garantia 30 dias |
  | "O curso é fraco, esperava mais" | `promessa_expectativa` / `qualidade_abaixo` |
  | "Perdi o acesso, achei que era para sempre" | `promessa_explicita` / `condicao_da_oferta`, crença acesso vitalício |
  | "Cobraram renovação que ninguém me avisou na compra" | `promessa_explicita` / `informacao_omitida` |

- [x] Subcausa inválida devolvida pelo modelo (teste com *mock*) é corrigida e a confiança fica ≤ 0,5.
- [x] `refund_event.reason_text` gravado já limpo. *(e o texto vai limpo também para o modelo.)*
- [x] Nenhum exemplo do prompt pertence ao split `test` (teste que confere os ids).

**Status:** ✅ concluída em 23/11 (22:30). Plano apresentado no início da sessão (pedido direto do Lucas).

**Não fazer:** ligação com a promessa (T11); relatórios (T13).

---

### T11 · Ligação com a promessa registrada

**Objetivo:** decidir se a devolução `confirma`, `contradiz` ou não tem relação com o que o creator prometeu.
**Depende de:** T09, T10.

**O que fazer:**
1. `refunds/linker.py` com as regras da seção 12.2 (item 4) e a semântica da 12.3 do CONTEXTO: comparação determinística para condições; `prompts/linker_v1.md` só para `resultado` e `alegacao`.
2. Integrar ao `classify_refund`: preenche `linked_promise_id` e `relation`.
3. `data/seeds/cenarios_relacao.yaml` com 12 cenários (promessa registrada + motivo + relação esperada), cobrindo: condição igual (`confirma`), condição diferente (`contradiz`), resultado prometido e cobrado (`confirma`), crença sem nada registrado (`sem_relacao`), causa não promessa (`nao_aplicavel`).

**Critérios de aceite:**
- [x] Passo 4 do exemplo do guia: promessa registrada "acesso 12 meses"; motivo "perdi o acesso, achei que era para sempre" → `promessa_explicita` / `condicao_da_oferta`, `relation = contradiz`, **não** conta no indicador do creator. *(com o modelo de verdade e pelo serviço; `weighs_on_creator = false`.)*
- [x] Promessa registrada "5 kg em 7 dias" (`em_revisao`); motivo "prometeram 5 kg em uma semana e não perdi nada" → `confirma`.
- [x] Pelo menos 11 dos 12 cenários acertam (`make test-llm`); os determinísticos acertam 100% sem modelo. *(12 de 12 com modelo; 9 de 9 determinísticos sem modelo.)*
- [x] Invariante 4 da seção 8.3 testada.

**Status:** ✅ concluída em 23/11 (22:35).

---

### T12 · Teste 1 do classificador (H1)

**Objetivo:** medir o classificador contra os 172 compradores codificados.
**Depende de:** T04, T10.

**O que fazer:**
1. `eval/eval_classifier.py` usando `classify_text` (sem banco), com texto = resumo em paráfrase.
2. Métricas da seção 14.2: causa principal (acurácia, kappa, matriz), subtipo nos 44 de promessa, **precisão e recall de `promessa_explicita`**, por split.
3. Rodada opcional (desejável): texto = só o título da reclamação.
4. Grava `eval/reports/classificador_h1.md`, `.json`, `erros_classificador.csv`.

**Critérios de aceite:**
- [ ] `make eval-classificador` roda em menos de 10 minutos e em segundos com cache. *(❌ sem cache: 872 s, limitado pela cota gratuita de 15 chamadas/min e por 503 em pico de demanda; ✅ com cache: 13 s. D31.)*
- [x] Relatório com metas ✅/❌, matriz de confusão legível e a seção de vazamentos.
- [x] O relatório aplica o **critério de corte** do guia em texto: "o classificador separa promessa de acesso e processo com acerto aceitável? sim/não", com os números. *(SIM: 83% e kappa 0,76 nas 121 reclamações do `test` de promessa, acesso ou processo.)*
- [x] `make eval` roda T08 e T12 juntos.

**Status:** ✅ concluída em 23/11 (23:00), com o critério de tempo sem cache não atingido (D31).

**→ Checkpoint 2 (Lucas):** fluxo completo pelos serviços + dois relatórios de avaliação. Decidir o modelo final de cada agente pelo split `dev` e registrar em `docs/decisoes.md`.

---

### T13 · Simulador, relatórios e explicação ao creator **[plan]**

**Objetivo:** dados que tornem os dois retornos visíveis (creator e marca) e as ferramentas de relatório.
**Depende de:** T09, T11.

**O que fazer:**
1. `scripts/simulate.py` (semente 42, período 26/10 a 22/11/2026):
   - cada creator envia peças reais pelo `check_content` (camada 1 basta; modelo opcional por flag) e gera links;
   - cerca de 600 vendas e 12% de devoluções, com mistura de causas próxima da H1 (acesso ~34%, processo ~32%, promessa ~26%, fraude ~7%);
   - motivos a partir de pelo menos 5 modelos de texto por subcausa, com variação;
   - devoluções classificadas pelo `classify_refund` real (com cache);
   - **personas**:

     | Creator | Comportamento | O que a demo precisa mostrar |
     |---|---|---|
     | `cr_ana` | Tenta "acesso vitalício e 30 dias para testar" (bloqueada), corrige; mantém "5 kg em 7 dias" (`revisar`). | Maior taxa de promessa `confirma`; promessa mais contestada "5 kg em 7 dias". |
     | `cr_bia` | Peças limpas, só condições registradas. | Taxa baixa; explicação curta e positiva. |
     | `cr_caio` | Vende muito `prod_ingles`, que tem problema de acesso na simulação. | Taxa de devolução alta, mas indicador de promessa baixo: "não é com você". |
     | `cr_duda` | Menos de 30 vendas. | "Dados insuficientes". |
     | `cr_eli` | Suplemento e cosmético, com trechos `revisar`. | Alertas de alegação; poucas devoluções de promessa. |
     | vários | Devoluções de `prod_treino` dizendo "achei que era vitalício", com registro de 12 meses. | Sinal para a marca: "vitalício" circula fora do controle dela. |

2. `reports/service.py`: métricas da seção 12.4 do CONTEXTO, por creator e por produto, com `MIN_SALES_FOR_INDICATOR`.
3. `reports/explain.py`: explicação da seção 12.5 (modelo `explainer_v1` + modelo de texto fixo como alternativa).
4. Ferramentas MCP `get_promise_outcome_report` e `explain_refunds_to_creator`.

**Critérios de aceite:**
- [x] `make db-reset seed simulate` roda em menos de 3 minutos com cache e imprime um resumo (vendas, devoluções, por causa). *(modo gabarito: 5 s; modo modelo: ~76 classificações, ~5 min na primeira vez e segundos com cache; rodar depois da cota voltar.)*
- [x] Relatório de `cr_ana` tem a maior taxa de promessa confirmada e "5 kg em 7 dias" no topo das promessas contestadas. *(4,7%; trecho "Secar até 5KG EM 7 DIAS".)*
- [x] Relatório de `prod_treino` mostra "acesso vitalício" no topo das crenças em `contradiz`. *(7 devoluções, de cr_ana e cr_bia.)*
- [x] `cr_caio`: taxa de devolução entre as maiores e indicador de promessa entre os menores. *(17,5%, a maior; indicador 0.)*
- [x] `cr_duda`: "dados insuficientes" no lugar do indicador. *(20 vendas.)*
- [x] Explicação de `cr_ana` cita o trecho a mudar e diz o que não é com ela; tem no máximo ~120 palavras. *(texto fixo: 101 palavras; o do modelo só é aceito se citar o trecho e couber no limite.)*
- [x] Teste: nenhuma frase de `reason_text` (5 palavras seguidas ou mais) aparece na explicação ou em relatório com papel `creator` (invariante 5). *(descontando o que está na própria peça do creator, que o comprador pode citar.)*
- [x] Sem chave, a explicação sai pelo modelo de texto fixo.

**Status:** ✅ concluída em 23/11 (23:40), conferida no modo gabarito e, em 24/11, com o classificador real (modo modelo): mesmas personas (D34). Plano apresentado no início da sessão (pedido direto do Lucas).

---

### T14 · Painel

**Objetivo:** uma interface simples onde marca, creator e Operações veem o ciclo.
**Depende de:** T09 (pode começar com dados do `seed`); relatórios da T13.

**O que fazer:** Streamlit, chamando **só serviços** (decisão D3). Seletor de papel na barra lateral (`marca`, `creator`, `operacoes`) e de período.

| Página | Papel | Conteúdo |
|---|---|---|
| 1 · Ficha | marca | Versões do produto, condições, regras com fonte; formulário de nova versão; avisos. |
| 2 · Checador | creator | Briefing do produto; caixa de texto; trechos destacados por cor (vermelho `bloquear`, amarelo `revisar`, verde `registrar`), explicação e sugestão; aviso de `#publi`; botão "Gerar link" só se permitido; botão "Contestar" em cada bloqueio. |
| 3 · Fila de revisão | marca, operacoes | Bloqueios contestados e classificações de baixa confiança, com contexto; manter, reverter ou reclassificar com nome do revisor. |
| 4 · Relatórios | todos | Marca/Ops: por produto (causas, promessas contestadas, sinais `contradiz`, cobertura, integridade). Creator: só os próprios números e a explicação simples. |
| 5 · Avaliação | todos | Lê `eval/reports/*.json`: metas e resultados do Teste 1. |

**Critérios de aceite:**
- [x] `make painel` abre sem erro sobre o banco do `simulate`. *(servidor headless: health ok, HTTP 200; as 6 páginas abrem nos 3 papéis sobre o `var/promessa.db` da simulação real.)*
- [x] O exemplo do guia inteiro pode ser feito pela interface (ficha → peça bloqueada → correção → link). *(teste com o AppTest: ficha do treino, peça bloqueada sem botão de link, correção ligada à anterior, link com acesso 12 meses e garantia 7 dias; contestação e reversão também.)*
- [x] Na visão `creator`, nenhum texto de comprador aparece. *(teste: nenhuma sequência de 5 palavras dos motivos na página de relatórios, para os 5 creators.)*
- [x] `grep` confirma que `app/` não importa `promessa.db.models`.

**Status:** ✅ concluída em 24/11 (07:45).

**Não fazer:** autenticação, estilo elaborado.

---

### T15 · Demo de ponta a ponta via MCP e conexão no Claude Code

**Objetivo:** mostrar que o servidor MCP é a porta de entrada e que um agente consegue usá-lo.
**Depende de:** T13.

**O que fazer:**
1. `scripts/demo_e2e.py`: sobe o servidor como subprocesso stdio, abre um `ClientSession`, lista as ferramentas e executa os 5 passos do exemplo do guia, imprimindo cada chamada e resposta de forma legível (entrada resumida, saída em destaque):
   1. `get_product_facts("prod_treino")` → garantia 7 dias, acesso 12 meses;
   2. `check_content` com "acesso vitalício e 30 dias para testar" → 2 × `bloquear`;
   3. `check_content` corrigido → 2 × `registrar`; `register_content_and_link` → link;
   4. venda simulada + `classify_refund("perdi o acesso, achei que era para sempre")` → `contradiz`, não pesa no creator;
   5. `get_promise_outcome_report(product_id="prod_treino")` → sinal "vitalício" para a marca.
2. Registrar o servidor no Claude Code (algo como `claude mcp add promessa -- uv run --directory <caminho absoluto do repo> python -m promessa.mcp_server`; confira a sintaxe com `claude mcp --help`) e documentar no README, com 3 pedidos de exemplo para uma conversa:
   - "Confira esta legenda para o produto prod_magnesio: ...";
   - "Por que as vendas da cr_ana estão voltando neste mês?";
   - "Quais promessas sobre o prod_treino mais geram devolução?".

**Critérios de aceite:**
- [ ] `make demo` roda em menos de 60 segundos (com cache) e termina com "Demo concluída".
- [ ] A lista de ferramentas mostrada tem as 9 da seção 9 do CONTEXTO (e o `ping`).
- [ ] `claude mcp list` mostra o servidor; os 3 pedidos de exemplo funcionam numa conversa (anotar a saída no README ou gravar a tela).

---

### T16 · Fechamento: README, resultados e ensaio

**Objetivo:** outra pessoa consegue rodar e entender; você consegue apresentar em 5 minutos.
**Depende de:** T15.

**O que fazer:**
1. `README.md`: o que é (3 linhas), requisitos, instalação, `make` passo a passo, como conectar no Claude Code, limites do MVP.
2. `docs/resultados.md`: tabela do Teste 1 (meta, obtido, ✅/❌), vazamentos, kappa humano (se a TP foi feita), o que o critério de corte diz, próximos passos (H5, piloto, vídeo, fase 2 com agentes externos).
3. `docs/decisoes.md` revisado.
4. `make lint test` e `make eval` limpos; `git tag v0.1-mvp`.
5. Ensaiar a demo (seção 6) duas vezes, uma delas do zero (`make db-reset seed simulate`).

**Critérios de aceite:**
- [ ] Um clone limpo + `.env` + `make setup db-reset seed simulate demo` funciona.
- [ ] `docs/resultados.md` mostra todos os números sem esconder metas não atingidas.
- [ ] Ensaio cronometrado ≤ 5 minutos.

---

## 6. Roteiro da demo (5 minutos)

| Tempo | O que mostrar | De onde |
|---|---|---|
| 0:00–0:30 | O problema em uma frase: as plataformas sabem quem vendeu e por que o dinheiro voltou, mas não o que foi prometido. 1 em 4 reclamações é de promessa; quase 2 em 3 quando o comprador lembra onde foi convencido. | Fala |
| 0:30–1:00 | A marca declara a ficha do Treino em Casa: 7 dias de garantia, 12 meses de acesso. O creator recebe o briefing. | Painel, páginas 1 e 2 |
| 1:00–2:00 | Creator cola "acesso vitalício e 30 dias para testar" → bloqueado, com explicação. Corrige → registrado → link gerado com a promessa presa. | Painel, página 2 |
| 2:00–3:00 | Três semanas depois: "perdi o acesso, achei que era para sempre" → promessa, condição da oferta, **contradiz**: não pesa no creator. | `make demo`, passo 4 |
| 3:00–4:00 | Os dois retornos: `cr_ana` vê o trecho a mudar ("5 kg em 7 dias"); `cr_caio` vê que as devoluções dele são de acesso; a marca vê que "vitalício" circula fora do controle dela. | Painel, página 4 |
| 4:00–4:45 | Teste 1: números dos dois agentes contra as metas, com os limites declarados. | Painel, página 5 |
| 4:45–5:00 | Próximo passo: respostas da YouShop (H5) e piloto; o mesmo servidor MCP abre para agentes externos na fase 2. | Fala |

---

## 7. Riscos do cronograma

| Risco | Sinal | Resposta |
|---|---|---|
| Exportação da planilha com colunas diferentes do esperado | T04 falha na conferência de contagens | Ajustar o mapeamento de colunas, nunca os números. Se faltar o resumo da H1, usar o título do slug e declarar. |
| Limite de taxa ou indisponibilidade da API | Erros 429/5xx | Cache já evita repetição; reduzir paralelismo; avaliação pode rodar em lotes. Sem API, o MVP inteiro funciona em modo só regras + modelo de texto fixo (cortes 2 e 5). |
| Classificador confunde promessa com acesso | T12 abaixo da meta | Melhorar casos de fronteira no prompt olhando só o split `dev`; reportar `test` honestamente. O guia já prevê: piloto não começa, MVP continua entregue. |
| Regras da camada 1 com muito falso positivo | Kappa baixo com precisão baixa | Rebaixar padrões ruidosos para `revisar` ou remover, registrando no YAML (nova versão). |
| T06 ou T07 estouram o tempo | CP1 vermelho | Teto de 1h na terça de manhã; depois, corte 5. |
| Escopo crescendo durante a construção | Vontade de "só mais isso" | Anotar em `docs/decisoes.md` como fase seguinte. O CONTEXTO (seção 3.2) é a lista do que não entra. |
| Cansaço na madrugada | Erros bobos, testes pulados | Parar no CP1 às 23:30. A terça tem folga para terminar T07/T08. |
