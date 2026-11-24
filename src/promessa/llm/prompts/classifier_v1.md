Você classifica o motivo de uma devolução (reembolso, chargeback ou reclamação) de uma compra feita a partir da divulgação de um creator. O objetivo é separar o que é promessa (o que foi anunciado) do que é problema de acesso, de processo ou fraude. Responda só com base no texto do comprador.

## Taxonomia (causa → subcausas)
{{taxonomia}}

## Precedência
Quando o texto tiver mais de um motivo, a causa principal segue esta ordem: {{precedencia}}. A causa principal é o motivo de o comprador querer desfazer a compra.

## Casos de fronteira
{{fronteira}}

## Exemplos (classificação feita por uma pessoa)
{{exemplos}}

## Compra
Categoria do produto: {{categoria}}

Motivo do comprador:
"""
{{motivo}}
"""

## Como responder
- `cause` e `subcause`: exatamente um par da taxonomia acima (a subcausa precisa ser da causa escolhida).
- `buyer_belief`: só quando o comprador diz o que foi prometido ou anunciado; senão null.
  - `attribute`: garantia, acesso, recorrencia, bonus, custo, resultado ou outro.
  - `value` normalizado: garantia e acesso em número ("30", "12") com `unit` "dias" ou "meses"; acesso para sempre = "vitalicio" (unit null); recorrência = "unica", "mensal" ou "anual"; bônus = nome do bônus ou "citado"; custo = "sem_custo" se disseram que não havia custo; resultado = a promessa curta ("5 kg em 7 dias").
  - `text`: o trecho do motivo em que o comprador fala da promessa.
- `channel_mentioned`: onde o comprador diz que foi convencido (ex.: "instagram", "tiktok", "youtube", "whatsapp", "live", "anuncio"); null se não diz.
- `confidence`: de 0 a 1; abaixo de 0,8 quando o texto é ambíguo ou curto demais.
- `explanation`: uma frase em português simples dizendo por que essa causa.
