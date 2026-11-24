# Resultados do Teste 1 (MVP Promessa Rastreável)

> 24/11/2026 · modelo `gemini-3.5-flash-lite` nos dois agentes (D25) · checador rodada **v2**
> (`eval/reports/checador_h2.md`) · classificador rodada **v2** (`eval/reports/classificador_h1.md`).
> O split `test` é o principal; `dev` serviu para ajustar regras e escolher os exemplos do prompt.
> Nenhum resultado foi escondido: metas não atingidas estão marcadas com ❌.

## Resumo contra as metas do guia

| Agente | Meta (guia) | Obtido no `test` | Total (dev + test) | |
|---|---|---|---|---|
| Checador | `bloquear` nas 4 peças com alegação proibida pela Anvisa: 4 de 4 | 2 de 2 (as outras 2 estão no `dev`) | **4 de 4** | ✅ |
| Checador | Kappa no binário "indício" ≥ 0,6 | 0,37 (só regras) · 0,32 (regras + modelo) | 0,48 · 0,37 | ❌ |
| Checador | Promessa verificável extraída (peça) ≥ 80% | 47% (só regras) · 71% (regras + modelo) | 41% · 59% | ❌ |
| Classificador | Acurácia na causa principal ≥ 80% | **83%** | 86% | ✅ |
| Classificador | Kappa na causa principal ≥ 0,6 | **0,77** | 0,80 | ✅ |
| Classificador | Acurácia do subtipo nas reclamações de promessa ≥ 70% | **74%** (34 reclamações) | 75% (44) | ✅ |

**Critério de corte do guia: o classificador separa promessa de acesso e processo com acerto
aceitável? SIM.** Nas 121 reclamações do `test` cujo gabarito é promessa, acesso ou processo, o
acerto foi de 86%, com kappa 0,79 (definição na D31: acurácia ≥ 80% e kappa ≥ 0,6 nessas três
classes).

## Checador (60 anúncios da auditoria H2)

Ficha genérica da categoria do gabarito: o checador aplica as listas oficiais e os padrões, e só
extrai as condições anunciadas (não há ficha real para comparar). Indício = `bloquear` ou `revisar`.

| Configuração | Kappa (dev / test / total) | Precisão do indício (total) | Recall do indício (total) | Evidentes | Verificável (test) |
|---|---|---|---|---|---|
| Só regras | 0,71 / 0,37 / 0,48 | 87% | 61% | 4 de 4 | 8 de 17 (47%) |
| Regras + modelo | 0,47 / 0,32 / 0,37 | 67% | 91% | 4 de 4 | 12 de 17 (71%) |

- **As irregulares evidentes (S06, S22, S25, S26) são bloqueadas nas duas configurações**, por
  `SUP-EMAG`, `SUP-IMUN` e `SUP-DOENCA`. É o caso em que bloquear tem base clara.
- **Só regras erra por omissão; com modelo, erra por excesso.** As regras quase não dão alarme falso
  (87% de precisão), mas deixam passar emagrecimento sem número em infoproduto (S03, S08, S13, S15,
  S18, S19), que não está em lista oficial nenhuma. O modelo pega esses casos (recall 91%), mas
  marca contraexemplos educativos ("não existe fórmula mágica para emagrecer") e a zona cinzenta de
  cosmético que o gabarito tratou como conforme.
- **Rodadas:** v1 (primeira) e v2 (ajuste de regra só com evidência do `dev`: "controlam o apetite"
  em S24; "prevenção"/"doença" em S29). O kappa só regras no `dev` subiu de 0,52 para 0,71; o
  `test` não mudou, o que mostra que o ajuste não foi feito olhando o `test`. A regra que mais
  ajudaria (emagrecimento sem número em infoproduto) ficou de fora porque todos os exemplos estão no
  `test` (D27).
- **Conferência manual das extrações:** 6 de 10 certas (erros: atributo errado num certificado de
  200 h, número sem unidade em prova social, valor não normalizado, resultado perdido em "nas
  próximas semanas").
- **Variação do modelo:** mesmo com temperatura 0, o Gemini não é determinístico; uma rodada idêntica
  deu kappa 0,38 e verificável 65% (D26). Os números com modelo variam alguns pontos; o cache torna
  cada rodada reprodutível.

## Classificador (172 compradores da H1)

Texto classificado: o resumo em paráfrase da H1. 8 exemplos no prompt, todos do `dev`.

| | dev (40) | test (132) | total (172) |
|---|---|---|---|
| Acurácia na causa principal | 95% | **83%** | 86% |
| Kappa | 0,93 | **0,77** | 0,80 |
| Subtipo de promessa | 80% (10) | **74%** (34) | 75% (44) |
| Promessa explícita: precisão / recall | 88% / 88% | **61% / 100%** | 67% / 96% |

Matriz de confusão (`test`; linhas = gabarito, colunas = predito):

| | promessa | acesso | processo | fraude | outros |
|---|---|---|---|---|---|
| promessa | **30** | 0 | 3 | 1 | 0 |
| acesso | 5 | **35** | 3 | 2 | 0 |
| processo | 3 | 0 | **39** | 0 | 0 |
| fraude | 1 | 0 | 2 | **6** | 0 |
| outros | 1 | 0 | 1 | 0 | **0** |

- **v1 → v2:** restringir a causa à taxonomia no esquema de saída (D32) acabou com as respostas
  "process"/"processamento" e levou a acurácia de 81% para 83% e o kappa de 0,74 para 0,77.
- **Ponto fraco: a precisão de `promessa_explicita` (61%).** O modelo puxa para promessa,
  sobretudo reclamações de acesso (5 no `test`). É a classe que pesa no creator, então a proteção do
  indicador vem de três lugares: só conta `confirma` com a promessa registrada na peça, só com
  confiança ≥ 0,8 e só se não foi revertida por revisão humana (D30).

## Ligação com a promessa e simulação

- **Relação devolução × promessa:** 12 de 12 cenários certos com classificador e linker de verdade
  (9 resolvidos por regra, 3 pelo modelo); o caso do guia ("acesso 12 meses" registrado × "achei
  que era para sempre") sai `contradiz` e não pesa no creator (D30).
- **Simulação com o classificador real:** as personas aparecem como planejado: cr_ana com o maior
  indicador (4,7%) e "Secar até 5KG EM 7 DIAS" no topo; cr_caio com a maior taxa de devolução
  (17,5%) e indicador 0 (problema de acesso, "não é com você"); cr_duda com dados insuficientes;
  "acesso vitalício" no topo dos sinais para a marca no prod_treino (D34). **São dados fictícios**:
  mostram que o ciclo funciona, não medem o mundo real.

## Vazamentos conhecidos (CONTEXTO 14.4)

- As regras da camada 1 foram escritas a partir da mesma auditoria H2 usada como gabarito: o
  resultado do checador na H2 é **otimista**.
- O texto da H1 é uma **paráfrase escrita por quem codificou** e pode carregar a categoria nas
  palavras: o resultado do classificador é **otimista**. A contraprova (classificar só pelo título,
  com as palavras do comprador) está pronta (`--com-titulos`), mas não rodou, para preservar a cota.
- Os exemplos do prompt do classificador vêm só do `dev`; os ajustes de regra do checador também.
- Uma pessoa codificou os dois gabaritos.

## Concordância humana (recodificação cega)

**Não feita.** Os CSV sem rótulos (20 anúncios e 20 reclamações do `test`) estão em
`data/gold/recodificacao/`. Sem o kappa humano × humano, não dá para saber se o kappa baixo do
checador é erro do agente ou discordância de critério (o caso dos contraexemplos educativos e da
zona cinzenta sugere a segunda).

## O que isto diz

- O **classificador** passa no critério de corte: separa promessa de acesso e processo com acerto
  aceitável, inclusive no `test`. O ciclo "devolução → causa → promessa registrada → creator ou
  marca" funciona de ponta a ponta.
- O **checador** acerta o que mais importa para bloquear (as 4 alegações proibidas) e as condições
  da oferta contra a ficha, mas não chega ao kappa 0,6 no binário "indício": faltam regras para
  emagrecimento em infoproduto e critério para negação e zona cinzenta.
- Os números do MVP são de protótipo (gabaritos de uma pessoa, paráfrase, auditoria que gerou as
  regras). Eles indicam caminho, não desempenho de produção.

## Próximos passos

1. **H5:** respostas e dados da YouShop (motivos reais de reembolso e checkout) para trocar a
   simulação por dados reais e conferir a premissa da D1 (ficha = condições do checkout).
2. **Piloto (Teste 2):** creators reais usando o checador antes de publicar; medir bloqueios
   evitados e devoluções por promessa confirmada.
3. **Checador:** regra de emagrecimento e resultado sem número para infoproduto (com novos exemplos,
   fora do `test`); tratamento de negação e de contraexemplos educativos; recodificação cega para
   calibrar a meta.
4. **Classificador:** rodada só com títulos; melhorar a precisão de promessa explícita com exemplos de
   acesso do `dev`.
5. **Vídeo e áudio:** transcrição das peças (fora do MVP).
6. **Fase 2:** abrir o mesmo servidor MCP para agentes externos (o servidor já está pronto e conectado
   ao Claude Code).
7. **Operação:** cota paga do Gemini (o plano gratuito limita 15 chamadas/min e 500/dia por modelo;
   a rodada fria do classificador levou 14,5 min, acima da meta de 10).
