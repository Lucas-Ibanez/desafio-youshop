# Teste 1 do classificador (H1, 172 compradores)

- **Data:** 23/11/2026 22:56
- **Rodada:** v1 (primeira rodada)
- **Prompt:** `classifier_v1` · **Modelo:** `gemini-3.5-flash-lite`
- **Exemplos no prompt (só do split dev):** H10, H08, P18, M10, T02, E09, P49, E08
- **Texto classificado:** resumo em paráfrase (coluna "Resumo" da H1).

## Vazamentos conhecidos (CONTEXTO 14.4)

- O texto da H1 é uma **paráfrase escrita por quem codificou**: pode carregar a categoria nas palavras. O resultado com paráfrase tende a ser otimista.
- Os 8 exemplos do prompt vêm só do split `dev`; a métrica principal é a do `test`.
- Depois da primeira rodada no `test`, mudança de prompt, exemplos ou taxonomia vira nova rodada.
- A rodada só com o título usa as palavras do comprador (slug do Reclame Aqui) e serve de contraprova (não rodou nesta versão; use `--com-titulos`).

## Critério de corte do guia

**O classificador separa promessa de acesso e processo com acerto aceitável? SIM.** Nas 121 reclamações do `test` cujo gabarito é promessa, acesso ou processo, o classificador acertou 83% (meta ≥ 80%) com kappa 0.76 (meta ≥ 0,6).

## Metas do guia

`test` é o split principal. ✅/❌ em cada coluna; nada é escondido.

| Meta | Texto | dev | test | total |
|---|---|---|---|---|
| Acurácia na causa principal, meta ≥ 80% | resumo em paráfrase | 95% ✅ | 81% ✅ | 84% ✅ |
| Kappa na causa principal, meta ≥ 0,6 | resumo em paráfrase | 0.93 ✅ | 0.74 ✅ | 0.78 ✅ |
| Acurácia do subtipo nas reclamações de promessa, meta ≥ 70% | resumo em paráfrase | 80% (10) ✅ | 74% (34) ✅ | 75% (44) ✅ |

## Promessa explícita (é o que pesa no creator: precisão importa mais)

| Texto | split | precisão | recall | gabarito | predito |
|---|---|---|---|---|---|
| resumo em paráfrase | dev | 88% | 88% | 8 | 8 |
| resumo em paráfrase | test | 63% | 100% | 19 | 30 |
| resumo em paráfrase | total | 68% | 96% | 27 | 38 |

## Matriz de confusão da causa principal (resumo em paráfrase, test)

Diagonal em negrito = acerto.

| gabarito \ predito | promessa | acesso | processo | fraude | outros | total |
|---|---|---|---|---|---|---|
| promessa | **30** | 0 | 3 | 1 | 0 | 34 |
| acesso | 6 | **35** | 1 | 3 | 0 | 45 |
| processo | 1 | 1 | **36** | 0 | 4 | 42 |
| fraude | 1 | 0 | 2 | **6** | 0 | 9 |
| outros | 1 | 1 | 0 | 0 | **0** | 2 |

Total (dev + test):

| gabarito \ predito | promessa | acesso | processo | fraude | outros | total |
|---|---|---|---|---|---|---|
| promessa | **39** | 0 | 4 | 1 | 0 | 44 |
| acesso | 7 | **48** | 1 | 3 | 0 | 59 |
| processo | 1 | 1 | **49** | 0 | 4 | 55 |
| fraude | 1 | 0 | 2 | **9** | 0 | 12 |
| outros | 1 | 1 | 0 | 0 | **0** | 2 |

## Erros

Detalhe por reclamação em `eval/reports/erros_classificador.csv` (fora do git).

- resumo em paráfrase: 27 de 172 com causa principal diferente do gabarito.

## Histórico de rodadas

| rodada | data | o que mudou | acurácia test | kappa test |
|---|---|---|---|---|
| v1 | 23/11/2026 22:56 | primeira rodada | 81% | 0.74 |
