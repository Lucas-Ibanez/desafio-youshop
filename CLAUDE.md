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

Comandos: make test | make test-llm | make lint | make seed | make simulate | make eval | make demo | make painel | make mcp
