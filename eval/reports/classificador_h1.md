# Teste 1 do classificador (H1, 172 compradores)

- **Data:** 24/11/2026 07:59
- **Rodada:** v2 (mudou: prompt classifier_v1, prompt classifier_v2. esquema de saída: cause restrita às causas da taxonomia (enum gerado do YAML); prompt classifier_v2 com a mesma instrução reforçando o nome exato da causa)
- **Prompt:** `classifier_v2` · **Modelo:** `gemini-3.5-flash-lite`
- **Exemplos no prompt (só do split dev):** H10, H08, P18, M10, T02, E09, P49, E08
- **Texto classificado:** resumo em paráfrase (coluna "Resumo" da H1).

## Vazamentos conhecidos (CONTEXTO 14.4)

- O texto da H1 é uma **paráfrase escrita por quem codificou**: pode carregar a categoria nas palavras. O resultado com paráfrase tende a ser otimista.
- Os 8 exemplos do prompt vêm só do split `dev`; a métrica principal é a do `test`.
- Depois da primeira rodada no `test`, mudança de prompt, exemplos ou taxonomia vira nova rodada.
- A rodada só com o título usa as palavras do comprador (slug do Reclame Aqui) e serve de contraprova (não rodou nesta versão; use `--com-titulos`).

## Critério de corte do guia

**O classificador separa promessa de acesso e processo com acerto aceitável? SIM.** Nas 121 reclamações do `test` cujo gabarito é promessa, acesso ou processo, o classificador acertou 86% (meta ≥ 80%) com kappa 0.79 (meta ≥ 0,6).

## Metas do guia

`test` é o split principal. ✅/❌ em cada coluna; nada é escondido.

| Meta | Texto | dev | test | total |
|---|---|---|---|---|
| Acurácia na causa principal, meta ≥ 80% | resumo em paráfrase | 95% ✅ | 83% ✅ | 86% ✅ |
| Kappa na causa principal, meta ≥ 0,6 | resumo em paráfrase | 0.93 ✅ | 0.77 ✅ | 0.80 ✅ |
| Acurácia do subtipo nas reclamações de promessa, meta ≥ 70% | resumo em paráfrase | 80% (10) ✅ | 74% (34) ✅ | 75% (44) ✅ |

## Promessa explícita (é o que pesa no creator: precisão importa mais)

| Texto | split | precisão | recall | gabarito | predito |
|---|---|---|---|---|---|
| resumo em paráfrase | dev | 88% | 88% | 8 | 8 |
| resumo em paráfrase | test | 61% | 100% | 19 | 31 |
| resumo em paráfrase | total | 67% | 96% | 27 | 39 |

## Matriz de confusão da causa principal (resumo em paráfrase, test)

Diagonal em negrito = acerto.

| gabarito \ predito | promessa | acesso | processo | fraude | outros | total |
|---|---|---|---|---|---|---|
| promessa | **30** | 0 | 3 | 1 | 0 | 34 |
| acesso | 5 | **35** | 3 | 2 | 0 | 45 |
| processo | 3 | 0 | **39** | 0 | 0 | 42 |
| fraude | 1 | 0 | 2 | **6** | 0 | 9 |
| outros | 1 | 0 | 1 | 0 | **0** | 2 |

Total (dev + test):

| gabarito \ predito | promessa | acesso | processo | fraude | outros | total |
|---|---|---|---|---|---|---|
| promessa | **39** | 0 | 4 | 1 | 0 | 44 |
| acesso | 6 | **48** | 3 | 2 | 0 | 59 |
| processo | 3 | 0 | **52** | 0 | 0 | 55 |
| fraude | 1 | 0 | 2 | **9** | 0 | 12 |
| outros | 1 | 0 | 1 | 0 | **0** | 2 |

## Erros

Detalhe por reclamação em `eval/reports/erros_classificador.csv` (fora do git).

- resumo em paráfrase: 24 de 172 com causa principal diferente do gabarito.

## Histórico de rodadas

| rodada | data | o que mudou | acurácia test | kappa test |
|---|---|---|---|---|
| v1 | 23/11/2026 22:56 | primeira rodada | 81% | 0.74 |
| v2 | 24/11/2026 07:59 | mudou: prompt classifier_v1, prompt classifier_v2. esquema de saída: cause restrita às causas da taxonomia (enum gerado do YAML); prompt classifier_v2 com a mesma instrução reforçando o nome exato da causa | 83% | 0.77 |
