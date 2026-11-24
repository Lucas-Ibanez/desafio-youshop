# Teste 1 do checador (H2, 60 anúncios)

- **Data:** 23/11/2026 22:56
- **Rodada:** v2 (mudou: data/rules/suplemento_proibidas.yaml. regras ajustadas só com evidência do dev: SUP-EMAG + controlam/controlar o apetite (S24); SUP-DOENCA + prevenção/doença (S29). Sem evidência no dev, emagrecimento sem número em infoproduto ficou de fora)
- **Regras:** normalizacao.yaml@2026-11-23, suplemento_proibidas.yaml@2026-11-23.2, suplemento_in28_permitidas.yaml@2026-11-23, cosmetico_proibidas.yaml@2026-11-23, padroes_h2.yaml@2026-11-23, condicoes_oferta.yaml@2026-11-23, taxonomia_devolucao.yaml@2026-11-23
- **Prompt:** `checker_v1` · **Modelo:** `gemini-3.5-flash-lite`
- **Ficha:** genérica da categoria do gabarito (regras oficiais da categoria; condições da oferta não informadas, então condição anunciada é só extraída e registrada).
- **Indício:** predição `bloquear` ou `revisar` × gabarito não conforme (indício + irregular evidente).

## Vazamentos conhecidos (CONTEXTO 14.4)

- As regras da camada 1 foram escritas a partir desta mesma auditoria H2: o resultado é **otimista**.
- O prompt do checador não usa exemplos do gabarito; mesmo assim, a métrica principal é a do split `test`.
- Depois da primeira rodada no `test`, toda mudança de regra ou prompt vira nova rodada (v2, v3...).

## Metas do guia

`test` é o split principal. ✅/❌ em cada coluna; nada é escondido.

| Meta | Configuração | dev | test | total |
|---|---|---|---|---|
| Sensibilidade nas irregulares evidentes (`bloquear`), meta 4 de 4 | só regras | 2/2 ✅ | 2/2 ✅ | 4/4 ✅ |
| Kappa no binário "indício", meta ≥ 0,6 | só regras | 0.71 ✅ | 0.37 ❌ | 0.48 ❌ |
| Recall de promessa verificável (peça), meta ≥ 80% | só regras | 1/5 (20%) ❌ | 8/17 (47%) ❌ | 9/22 (41%) ❌ |
| Sensibilidade nas irregulares evidentes (`bloquear`), meta 4 de 4 | regras + modelo | 2/2 ✅ | 2/2 ✅ | 4/4 ✅ |
| Kappa no binário "indício", meta ≥ 0,6 | regras + modelo | 0.47 ❌ | 0.32 ❌ | 0.37 ❌ |
| Recall de promessa verificável (peça), meta ≥ 80% | regras + modelo | 1/5 (20%) ❌ | 12/17 (71%) ❌ | 13/22 (59%) ❌ |

## Outras métricas (total)

| Configuração | acurácia | precisão do indício | recall do indício | IC95% do recall verificável |
|---|---|---|---|---|
| só regras | 73% | 87% | 61% | 23%–61% |
| regras + modelo | 70% | 67% | 91% | 39%–77% |

## Irregulares evidentes (as 4 peças)

| id | split | só regras | regras + modelo |
|---|---|---|---|
| S06 | test | bloquear ✅ (SUP-EMAG) | bloquear ✅ (SUP-EMAG) |
| S22 | dev | bloquear ✅ (SUP-IMUN) | bloquear ✅ (SUP-EMAG, SUP-IMUN) |
| S25 | dev | bloquear ✅ (SUP-DOENCA, SUP-EMAG) | bloquear ✅ (SUP-DOENCA, SUP-EMAG) |
| S26 | test | bloquear ✅ (SUP-EMAG) | bloquear ✅ (SUP-EMAG) |

## Matriz de confusão do indício (total)

**só regras**

| gabarito \ predito | indício | sem indício |
|---|---|---|
| não conforme | 20 | 13 |
| conforme | 3 | 24 |

**regras + modelo**

| gabarito \ predito | indício | sem indício |
|---|---|---|
| não conforme | 30 | 3 |
| conforme | 15 | 12 |

## Conferência manual (10 extrações sorteadas)

Semente 11, entre as peças verificáveis com alguma promessa extraída (regras + modelo). Lucas: marque a última coluna com `certo` ou `errado`; as marcas são mantidas nas próximas rodadas.

| id | trecho do anúncio | extraído | certo ou errado |
|---|---|---|---|
| O05 | comprar imóveis abaixo do valor... ACESSO VITALÍCIO. DE R$ 3.997 por apenas R$ 2.597 | acesso=vitalicio | certo |
| O08 | Certificado Gratuito Válido de 200h... Vagas Limitadas | resultado=200 horas | errado: o valor (200 h) está certo, mas é condição do certificado, não resultado |
| O09 | Certificado incluso + acesso vitalício... Certificado válido em todo Brasil | acesso=vitalicio | certo |
| O11 | Você desbloqueou acesso vitalício! | acesso=vitalicio | certo |
| R01 | tenha uma RENDA EXTRA de 10K | resultado=renda extra de 10k | certo |
| R02 | +3k alunas ja passaram pelo curso... nenhuma era confeiteira | resultado=3000 | errado: "3000" sem a unidade (alunas); é prova social, não resultado prometido |
| S04 | Secar até 5KG EM 7 DIAS | resultado=5 kg em 7 dias | certo |
| S14 | estratégias para secar a barriga, começando pelo Seca Barriga de 7 dias | resultado=secar a barriga, comecando pelo seca barriga de 7 dias | errado: valor não normalizado; a promessa é "secar a barriga em 7 dias" |
| S15 | ELIMINAR A BARRIGA nas próximas semanas SEM SAIR DE CASA | resultado=semanas | errado: perdeu o resultado; deveria ser "eliminar a barriga em semanas" |
| S17 | cardápios de emagrecimento saudável para 21 dias | resultado=emagrecimento saudavel para 21 dias | certo |

## Erros

Detalhe por peça em `eval/reports/erros_checador.csv` (fora do git). Resumo (total):

- só regras: 13 não conformes sem indício (falso negativo), 3 conformes com indício (falso positivo).
- regras + modelo: 3 não conformes sem indício (falso negativo), 15 conformes com indício (falso positivo).

## Histórico de rodadas

| rodada | data | o que mudou | kappa test (regras) | kappa test (regras+modelo) |
|---|---|---|---|---|
| v1 | 23/11/2026 21:35 | primeira rodada | 0.37 | 0.32 |
| v2 | 23/11/2026 22:56 | mudou: data/rules/suplemento_proibidas.yaml. regras ajustadas só com evidência do dev: SUP-EMAG + controlam/controlar o apetite (S24); SUP-DOENCA + prevenção/doença (S29). Sem evidência no dev, emagrecimento sem número em infoproduto ficou de fora | 0.37 | 0.32 |
