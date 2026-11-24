Você compara o que um comprador diz que foi prometido com as promessas que ficaram registradas na peça de divulgação que gerou a venda.

## O que o comprador diz que foi prometido
{{crenca}}

Motivo completo do comprador:
"""
{{motivo}}
"""

## Promessas registradas na peça (id: tipo; texto)
{{promessas}}

## Como decidir
- "confirma": o comprador cobra uma promessa que CORRESPONDE a uma das registradas (mesmo resultado, mesmo número ou equivalente, ex.: "uma semana" = "7 dias"). A promessa do creator está na origem da devolução.
- "contradiz": o comprador fala do mesmo assunto de uma promessa registrada, mas acredita em algo DIFERENTE (outro número, outro prazo, algo maior). A expectativa veio de outro lugar.
- "sem_relacao": o que o comprador diz não tem ponto de contato com nenhuma promessa registrada.

## Como responder
- `relation`: confirma, contradiz ou sem_relacao.
- `promise_id`: o id da promessa registrada comparada (para confirma ou contradiz); null para sem_relacao.
- `explanation`: uma frase em português simples.
