# Vincula · Identidade visual e guia de interface

> Para o Claude Code aplicar no painel (`app/`). Versão 1 · 24/11/2026.
> Escopo: **só a camada de apresentação**. O pacote Python continua `promessa`, as ferramentas MCP e os enums não mudam.
> Salvar no repositório como `docs/BRAND.md`.

---

## 1. Nome e ideia da marca

### 1.1 Nome: **Vincula**

O CDC, art. 30, diz que a oferta e a publicidade **vinculam** o fornecedor: o que foi prometido no anúncio vira parte do contrato. É exatamente o que o produto prova. "Vincula" também quer dizer "liga": o link rastreado liga a peça à venda, e a venda à devolução.

| Uso | Forma |
|---|---|
| Nome do produto | Vincula |
| Descritor (abaixo do nome, no painel e na capa do pitch) | promessa rastreável |
| Frase de assinatura | A promessa que vende é a promessa que vincula. |
| Frase curta (botões, rodapé, slide final) | Cada promessa com o seu desfecho. |
| Dentro da YouShop | Vincula, da YouShop |

**Por que não outros nomes:** "Lastro" já é marca de uma proptech brasileira de IA; "Dito" já é marca de uma empresa de CRM para varejo em Belo Horizonte. "Vincula" não apareceu em uso no mesmo setor numa busca rápida (existe uma edtech "Vinculo", sem relação). **Antes de uso externo, consultar o INPI.** Para o case, basta.

**Alternativas, se o nome não agradar:** *Palavra Dada* (o compromisso do creator) ou *Canhoto* (a via que fica como prova da promessa).

### 1.2 Ideia visual: o canhoto e o fio

Dois objetos do mundo real dão forma à marca:

1. **O canhoto.** No talão, o canhoto é a parte que fica como prova. No Vincula, o link rastreado é o canhoto da promessa: ele guarda o que foi dito, em qual versão da ficha, com um carimbo de "registrada". É o elemento mais memorável da interface e aparece **uma vez**, quando o link é gerado.
2. **O fio.** Uma linha que liga dois pontos: o que foi prometido (ponto cheio) e o que aconteceu (ponto vazado). Ela vira o símbolo da marca e aparece nos relatórios ligando a promessa registrada à crença do comprador.

E uma regra que organiza toda a tipografia: **o que alguém disse aparece em serifa itálica; o que o sistema diz aparece em sans.** Trechos da peça, promessas registradas e o que o comprador entendeu são "o dito". Explicações, rótulos, números e botões são a voz do Vincula.

### 1.3 Princípios de interface

1. **Ajuda, não polícia.** O produto existe para o creator acertar antes de publicar. Nada de vermelho gritando, ícones de alerta em excesso ou palavras como "infração", "punição", "irregular". Vermelho só para `bloquear`, e sempre com a sugestão de como corrigir ao lado.
2. **Mostrar a prova.** Toda decisão mostra de onde veio: regra (`rule_key`, fonte, versão) ou modelo. O rastro é parte da interface, não um detalhe escondido.
3. **Ousadia em um lugar só.** O canhoto, o marca-texto e o fio são os momentos fortes. Todo o resto (tabelas, formulários, barra lateral) é quieto e disciplinado.
4. **Escrever do lado de quem usa.** "Checar peça", não "Executar check_content". "Ficha do produto", não "product_facts".

---

## 2. Paleta

Base fria com um leve tom violeta, tirado da tinta de carimbo de cartório. Nada de creme, terracota ou preto com acento neon.

### 2.1 Cores da marca

| Token | Hex | Uso |
|---|---|---|
| `--vc-papel` | `#F6F5F9` | Fundo da página |
| `--vc-folha` | `#FFFFFF` | Superfícies: canhoto, área do texto checado, formulários |
| `--vc-tinta` | `#1E1A2E` | Texto principal, wordmark |
| `--vc-grafite` | `#5C5770` | Texto secundário, legendas, metadados (contraste 6,3:1 sobre `papel`) |
| `--vc-risco` | `#DCD8E6` | Bordas, divisórias, picote do canhoto |
| `--vc-carimbo` | `#4B2FA8` | Cor primária: botões, links, foco, ponto cheio do fio, carimbo, promessa `confirma` |
| `--vc-carimbo-claro` | `#ECE7FB` | Fundo de item selecionado, realce suave |
| `--vc-linha` | `#0E7C7B` | Cor secundária: sinais para a marca, relação `contradiz`, ponto vazado do fio (contraste 5:1 sobre branco) |
| `--vc-linha-claro` | `#DDF1F0` | Fundo de "sinal para a marca" |

### 2.2 Cores das decisões do checador

Cada saída tem três tons: o texto do chip, o marca-texto (fundo do trecho) e a borda.

| Saída | Rótulo na tela | Texto | Marca-texto | Borda |
|---|---|---|---|---|
| `bloquear` | Bloqueado | `#A3261F` | `#FCE4E1` | `#E9A39B` |
| `revisar` | Revisar | `#8A5300` | `#FFE59A` | `#E8C15A` |
| `registrar` | Registrado | `#17663F` | `#D6F0E0` | `#8CCBA8` |
| `limpo` | Sem achados | `#5C5770` | — | `#DCD8E6` |

Contraste verificado: texto do chip sobre o próprio marca-texto fica entre 5:1 e 6:1 (AA). Dentro do texto destacado, a letra continua `--vc-tinta`.

### 2.3 Cores da relação com a promessa (relatórios)

| `relation` | Rótulo na tela | Cor | Estilo do fio |
|---|---|---|---|
| `confirma` | Confirma a promessa | `--vc-carimbo` | linha contínua |
| `contradiz` | Contradiz o registro | `--vc-linha` | tracejada (6 4) |
| `sem_relacao` | Sem relação | `#9A95AB` | pontilhada (1 5, ponta redonda) |
| `nao_aplicavel` | Não se aplica | `--vc-risco` | sem fio |

### 2.4 Cores das causas de devolução (gráficos)

Sempre a mesma cor para a mesma causa, em todos os gráficos. Usar escala explícita (Altair `scale=alt.Scale(domain=..., range=...)`), não a ordem automática.

| `cause` | Rótulo | Hex |
|---|---|---|
| `promessa_explicita` | Promessa do anúncio | `#4B2FA8` |
| `promessa_expectativa` | Expectativa | `#9C8AE0` |
| `acesso_entrega` | Acesso ou entrega | `#0E7C7B` |
| `processo` | Processo | `#7D8A9C` |
| `fraude` | Fraude | `#8C2F5A` |
| `outros` | Outros | `#B9B4C7` |

O agrupamento já conta a história: tons de violeta = promessa (o que pode pesar no creator); o resto = "não é com você".

---

## 3. Tipografia

### 3.1 Famílias

| Papel | Família | Pesos | Onde |
|---|---|---|---|
| **Voz do sistema** | Schibsted Grotesk (variável) | 400, 500, 700, 800 | Toda a interface: títulos, texto, rótulos, botões, números |
| **O dito** | Newsreader (variável, com eixo `opsz`) | 400 e 500, itálico | Trechos da peça, promessas registradas, crença do comprador, sugestão de reescrita |
| **Identificadores** | IBM Plex Mono | 400, 500 | Só valores que alguém copia ou confere: `rule_key`, id do link, versão da ficha, `prompt_version` |

As três são do Google Fonts, gratuitas e cobrem acentos do português. Servir os arquivos **localmente** (seção 6.2), para o painel funcionar offline na demo.

Não usar mono como enfeite em rótulos pequenos. Se não é um código que se copia, é Schibsted.

### 3.2 Escala (razão 1,25, base 16 px)

| Token | Tamanho / altura de linha | Família e peso | Espaçamento | Uso |
|---|---|---|---|---|
| `display` | 40 / 44 | Schibsted 800 | -0,025em | Título da página (um por página) |
| `h2` | 28 / 34 | Schibsted 700 | -0,015em | Seções da página |
| `h3` | 21 / 28 | Schibsted 700 | -0,01em | Blocos dentro da seção |
| `h4` | 16 / 24 | Schibsted 600 | 0 | Título de grupo pequeno (em caixa normal, nunca em maiúsculas) |
| `corpo` | 16 / 26 | Schibsted 400 | 0 | Texto corrido, explicações |
| `pequeno` | 13 / 20 | Schibsted 500 | 0,005em | Metadados, legendas, cor `grafite` |
| `numero` | 40 / 40 | Schibsted 800, `font-variant-numeric: tabular-nums` | -0,02em | Métricas |
| `dito-grande` | 20 / 31 | Newsreader 400 itálico, `opsz` automático | 0 | Texto da peça checada, promessa no canhoto |
| `dito-inline` | 1,08em do texto ao redor | Newsreader 400 itálico | 0 | Trecho citado dentro de uma frase em sans |
| `id` | 13 / 20 | Plex Mono 500 | 0 | Identificadores |

### 3.3 Regras de composição

- Texto corrido com no máximo **68 caracteres por linha** (`max-width: 68ch`). A explicação ao creator e o briefing respeitam isso mesmo em tela larga.
- O dito vai **entre aspas curvas** (“ ”), em itálico. Nunca aspas retas.
- Caixa normal em tudo: títulos, botões, rótulos. A única exceção é o carimbo (seção 5.3), porque imita um objeto que é assim no mundo real.
- Sem sobrancelha (rótulo pequeno em maiúsculas acima do título). O título diz o que a página é; a linha abaixo diz o que se faz nela.
- Sem destacar uma palavra só do título com cor ou itálico.
- Números com `tabular-nums` em tabelas e métricas, para alinhar.
- Datas no formato "24/11 às 10:42" (America/Sao_Paulo), percentuais com vírgula ("25,6%").

---

## 4. Espaço, forma e estrutura

| Token | Valor | Uso |
|---|---|---|
| Espaçamento | 4, 8, 12, 16, 24, 32, 48, 64 px | Múltiplos de 4. Entre seções: 48. Dentro de bloco: 16. |
| `--vc-raio-p` | 4 px | Chips, inputs, botões |
| `--vc-raio-m` | 10 px | Painéis (canhoto, texto checado) |
| `--vc-raio-carimbo` | 3 px | Carimbo |
| Sombra | nenhuma por padrão | Elevação se faz com `folha` sobre `papel` + borda `risco`. A única sombra é a do canhoto: `0 1px 0 var(--vc-risco), 0 12px 24px -16px rgba(75,47,168,.25)`. |
| Foco | `outline: 2px solid var(--vc-carimbo); outline-offset: 2px` | Todo elemento interativo, inclusive os nativos do Streamlit |

**Estrutura carrega informação, não enfeite:**
- A barra colorida de 3 px à esquerda de um achado é a cor da decisão. Não usar barra lateral colorida em nada que não seja decisão.
- Números de sequência (1, 2, 3) só onde há ordem real: os passos "colar → checar → corrigir → gerar link" na página do checador. Em nenhum outro lugar.
- Não picotar o conteúdo em cartões iguais. Métricas ficam em linha, separadas por um filete vertical `risco`, sem caixa em volta.

---

## 5. Componentes

Todos em `app/ui/components.py`, renderizados com `st.html(...)`. **Todo texto que vem de usuário passa por `html.escape`** (o texto da peça é colado pelo creator).

### 5.1 Marca e barra lateral

**Símbolo (o fio):** ponto cheio violeta, traço tracejado, ponto vazado verde-petróleo. Promessa ligada ao desfecho.

```svg
<svg viewBox="0 0 40 16" width="40" height="16" aria-hidden="true">
  <circle cx="6" cy="8" r="5" fill="#4B2FA8"/>
  <line x1="14" y1="8" x2="27" y2="8" stroke="#4B2FA8" stroke-width="2"
        stroke-dasharray="3 3" stroke-linecap="round"/>
  <circle cx="34" cy="8" r="4.5" fill="none" stroke="#0E7C7B" stroke-width="2"/>
</svg>
```

**Wordmark:** "vincula" em minúsculas, Schibsted Grotesk 800, 24 px, `letter-spacing: -0.035em`, cor `tinta`. Símbolo à esquerda, alinhado pela linha de base. Descritor "promessa rastreável" embaixo, 13 px, `grafite`.

**Favicon:** quadrado 64 px, fundo `carimbo`, raio 14, o mesmo fio em branco. Gerar `app/static/favicon.png` a partir do SVG e passar em `st.set_page_config(page_title="Vincula", page_icon=...)`.

**Barra lateral, de cima para baixo:** wordmark; "Você está vendo como" com o seletor de papel (Marca, Creator, Operações), de preferência `st.segmented_control` se a versão tiver; período; navegação. Fundo `folha`, borda direita `risco`.

### 5.2 Cabeçalho de página

```
Checar peça                                         ← display
Cole a legenda ou o roteiro. O Vincula compara      ← corpo, grafite, max 68ch
com a ficha do produto antes de gerar o link.
Treino em Casa 12M, ficha v1                        ← pequeno; "v1" em mono
```

Títulos das páginas (substituem os atuais na tela, não nos arquivos):

| Arquivo | Título | Linha de apoio |
|---|---|---|
| `1_Ficha.py` | Ficha do produto | O que este produto pode prometer, com a fonte de cada regra. |
| `2_Checador.py` | Checar peça | Cole a legenda ou o roteiro. O Vincula compara com a ficha antes de gerar o link. |
| `3_Fila_de_revisao.py` | Fila de revisão | Bloqueios contestados e classificações com pouca confiança. A decisão é sua. |
| `4_Relatorios.py` | Devoluções e promessas | Por que as vendas voltaram e o que cada lado pode mudar. |
| `5_Avaliacao.py` | Teste dos agentes | Como o checador e o classificador se saíram contra os gabaritos. |

### 5.3 Texto checado com marca-texto (momento forte nº 1)

O texto inteiro da peça em `dito-grande` (Newsreader itálico 20/31) sobre `folha`, com cada trecho achado pintado como um marca-texto na cor da decisão. É assim que um editor marca um roteiro.

```html
<div class="vc-peca is-new">
  <p>Treino em casa com
    <mark class="vc-marca vc-marca--bloquear" style="--i:0">acesso vitalício</mark> e
    <mark class="vc-marca vc-marca--bloquear" style="--i:1">30 dias para testar</mark>.
  </p>
</div>
```

```css
.vc-marca {
  color: inherit;
  background-image: linear-gradient(var(--tom), var(--tom));
  background-repeat: no-repeat;
  background-size: 100% 78%;
  background-position: 0 70%;
  -webkit-box-decoration-break: clone; box-decoration-break: clone;
  padding: 0 .12em; border-radius: 2px;
}
.vc-marca--bloquear  { --tom: #FCE4E1; text-decoration: underline 2px #E9A39B; text-underline-offset: 4px; }
.vc-marca--revisar   { --tom: #FFE59A; }
.vc-marca--registrar { --tom: #D6F0E0; }
```

O sublinhado extra no `bloquear` garante que a decisão não dependa só de cor.

Abaixo do texto, a lista de achados em ordem de gravidade:

```
▌ Bloqueado   “acesso vitalício”
▌ A ficha deste produto diz acesso por 12 meses. Prometer acesso vitalício
▌ cria uma obrigação que o produto não cumpre.
▌ Troque por “12 meses de acesso”.
▌ COND-ACESSO, regra da ficha v1                          [Contestar bloqueio]
```

- Barra de 3 px à esquerda na cor de borda da decisão.
- Chip: texto na cor da decisão, fundo no marca-texto, raio 4, Schibsted 600 13 px.
- Trecho e sugestão em Newsreader itálico; explicação em Schibsted.
- Linha de rastro em `pequeno`: `rule_key` em mono + origem em texto ("regra da ficha v1" ou "modelo, prompt checker_v1").
- Identificação publicitária fica fora da lista, numa linha própria acima do botão: "Falta identificar como publicidade. Inclua #publi na legenda." (não conta como achado, decisão D5).

### 5.4 O canhoto (momento forte nº 2)

Aparece só depois de "Gerar link". Lado esquerdo: as promessas que ficaram presas ao link. Picote. Lado direito: o link e o carimbo.

```
┌──────────────────────────────────────────────────┬ ─ ┬──────────────────────┐
│ Promessas presas a este link                     ╎   │ Link                 │
│                                                  ╎   │ youshop.example/l/   │
│ “12 meses de acesso”          Registrada         ╎   │ K7Q2M9XA   (mono)    │
│ “7 dias de garantia”          Registrada         ╎   │                      │
│ “5 kg em 7 dias”              Em revisão         ╎   │   ╔═══════════╗      │
│                                                  ╎   │   ║REGISTRADA ║  ↺4°  │
│ Ficha v1 do Treino em Casa 12M, checada em       ╎   │   ╚═══════════╝      │
│ 24/11 às 10:42                                   ╎   │ Copiar link          │
└──────────────────────────────────────────────────┴ ─ ┴──────────────────────┘
```

```css
.vc-canhoto {
  display: grid; grid-template-columns: 1fr 0 minmax(14rem, 18rem);
  background: var(--vc-folha); border: 1px solid var(--vc-risco);
  border-radius: var(--vc-raio-m);
  box-shadow: 0 1px 0 var(--vc-risco), 0 12px 24px -16px rgba(75,47,168,.25);
}
.vc-canhoto__corpo, .vc-canhoto__via { padding: 24px; }
.vc-canhoto__picote { border-left: 2px dashed var(--vc-risco); position: relative; margin: 10px 0; }
.vc-canhoto__picote::before, .vc-canhoto__picote::after {
  content: ""; position: absolute; left: -10px; width: 18px; height: 18px;
  border-radius: 50%; background: var(--vc-papel); border: 1px solid var(--vc-risco);
}
.vc-canhoto__picote::before { top: -21px; }
.vc-canhoto__picote::after  { bottom: -21px; }

.vc-carimbo {
  display: inline-block; padding: 6px 12px;
  font: 800 15px/1 var(--vc-f-sistema); letter-spacing: .1em; text-transform: uppercase;
  color: var(--vc-carimbo); border: 2.5px solid currentColor; border-radius: var(--vc-raio-carimbo);
  transform: rotate(-4deg); opacity: .92; mix-blend-mode: multiply;
}
```

Em tela estreita (< 720 px), o canhoto empilha: corpo em cima, picote horizontal, via embaixo.

### 5.5 O fio (relatórios)

Liga a promessa registrada ao que o comprador entendeu, com a relação no meio. É a "costura" do produto, desenhada.

```
 Prometido na peça                                  O comprador entendeu
 ● “12 meses de acesso” ─ ─ ─ Contradiz o registro ─ ─ ─ ○ “acesso vitalício”
                              14 devoluções
```

- Ponto cheio `carimbo`, ponto vazado com a cor da relação, linha no estilo da tabela 2.3.
- Rótulo da relação num chip sobre a linha (fundo `folha` para "cortar" o fio).
- Usar em: "Promessas mais contestadas" (`confirma`) e "Sinais para a marca" (`contradiz`).
- **Na visão Creator**, o lado direito só mostra a crença normalizada agregada ("acesso vitalício", com contagem). Nunca o `reason_text` (invariante 5).

### 5.6 Métricas

Linha de 3 a 5 números, sem caixa, separados por filete vertical `risco`. Rótulo **em cima**, em `pequeno` e caixa normal; número em `numero`; uma linha de contexto embaixo quando ajuda ("de 212 vendas").

"Dados insuficientes" (creator com menos de 30 vendas) aparece no lugar do número, em Schibsted 500 16 px `grafite`, com a linha: "O indicador aparece a partir de 30 vendas no período."

### 5.7 Botões e campos

| Elemento | Estilo |
|---|---|
| Primário (`Checar peça`, `Gerar link`) | Fundo `carimbo`, texto branco, Schibsted 600 15 px, raio 4, altura 40. Hover: `#3E2590`. Ativo: `translateY(1px)`. |
| Secundário (`Contestar bloqueio`, `Copiar link`) | Fundo transparente, borda `risco`, texto `tinta`. Hover: borda `carimbo`. |
| Desabilitado (`Gerar link` com bloqueio) | Fundo `risco`, texto `grafite`, e a linha ao lado explica o motivo: "Ainda há 2 trechos bloqueados. Ajuste o texto ou conteste o bloqueio." |
| Textarea da peça | Fundo `folha`, borda `risco`, Newsreader 18 px (o creator escreve "o dito"), mínimo 6 linhas. Foco com o anel padrão. |

---

## 6. Movimento

Três momentos, cada um respondendo a uma ação. Nada se mexe sozinho ao abrir a página.

| Momento | Gatilho | Animação | Duração |
|---|---|---|---|
| **Marca-texto** | Resultado de "Checar peça" | Cada trecho é pintado da esquerda para a direita, na ordem em que aparece no texto. `background-size: 0% 78%` → `100% 78%`. Atraso `calc(var(--i) * 70ms + 120ms)`. | 420 ms cada |
| **Carimbo** | "Gerar link" com sucesso | O carimbo cai sobre o canhoto: `scale(1.6) rotate(-9deg)`, opacidade 0 → `scale(.96) rotate(-3deg)` → `scale(1) rotate(-4deg)`. O canhoto entra antes, com opacidade 0 → 1 e `translateY(8px)` → 0 em 200 ms. | 260 ms (carimbo começa aos 160 ms) |
| **Fio** | Expandir uma promessa no relatório | A linha se desenha do ponto cheio ao vazado: `clip-path: inset(0 100% 0 0)` → `inset(0 0 0 0)`. O chip da relação aparece no fim. | 500 ms |

```css
:root { --vc-ease: cubic-bezier(.2,.7,.2,1); }

@keyframes vc-marcar   { from { background-size: 0% 78%; } to { background-size: 100% 78%; } }
@keyframes vc-entrar   { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
@keyframes vc-carimbar {
  0%   { opacity: 0; transform: scale(1.6) rotate(-9deg); }
  60%  { opacity: .92; transform: scale(.96) rotate(-3deg); }
  100% { opacity: .92; transform: scale(1) rotate(-4deg); }
}
@keyframes vc-fiar     { from { clip-path: inset(0 100% 0 0); } to { clip-path: inset(0 0 0 0); } }

.is-new .vc-marca        { animation: vc-marcar 420ms var(--vc-ease) both; animation-delay: calc(var(--i, 0) * 70ms + 120ms); }
.is-new.vc-canhoto       { animation: vc-entrar 200ms var(--vc-ease) both; }
.is-new .vc-carimbo      { animation: vc-carimbar 260ms var(--vc-ease) 160ms both; }
.is-new .vc-fio__linha   { animation: vc-fiar 500ms var(--vc-ease) both; }

@media (prefers-reduced-motion: reduce) {
  .is-new *, .is-new { animation: none !important; }
}
```

**Cuidado com o Streamlit:** a página roda de novo a cada interação, e o HTML é recriado. Sem controle, o marca-texto repete toda vez que alguém mexe num filtro. A classe `is-new` só entra na execução logo depois da ação:

```python
# depois de check_content com sucesso
st.session_state["vc_anim"] = ("peca", result.piece_id)

# ao renderizar
is_new = st.session_state.pop("vc_anim", None) == ("peca", result.piece_id)
```

Micro-interações permitidas: hover de botão (cor, 120 ms), `translateY(1px)` no clique. Nada de hover que levanta cartões, nada de entrada animada em cada seção.

---

## 7. Texto da interface

### 7.1 Tom

Português do Brasil simples, frases curtas, voz ativa, caixa normal. O Vincula fala como um colega que conhece as regras, não como um fiscal. Erro explica o que aconteceu e como resolver; não pede desculpas e não é vago.

### 7.2 Rótulos dos enums na tela

O banco e o MCP continuam com os valores originais. Criar `app/ui/labels.py` com este mapa e usar só ele na tela.

| Valor | Na tela |
|---|---|
| `bloquear` / `revisar` / `registrar` / `limpo` | Bloqueado / Revisar / Registrado / Sem achados |
| `registrada` / `em_revisao` (promessa) | Registrada / Em revisão |
| `confirma` / `contradiz` / `sem_relacao` / `nao_aplicavel` | Confirma a promessa / Contradiz o registro / Sem relação / Não se aplica |
| `promessa_explicita` / `promessa_expectativa` / `acesso_entrega` / `processo` / `fraude` / `outros` | Promessa do anúncio / Expectativa / Acesso ou entrega / Processo / Fraude / Outros |
| `marca` / `creator` / `operacoes` | Marca / Creator / Operações |
| `contestado` / `mantido` / `revertido` | Contestado / Bloqueio mantido / Bloqueio revertido |
| `regra` / `modelo` (origem) | regra da ficha vN / modelo (prompt X) |

### 7.3 Ações e confirmações (o nome se mantém do botão à confirmação)

| Botão | Confirmação |
|---|---|
| Checar peça | (o resultado aparece; sem toast) |
| Gerar link | Link gerado. As promessas ficaram registradas. |
| Copiar link | Link copiado |
| Contestar bloqueio | Contestação enviada para a marca |
| Manter bloqueio / Reverter bloqueio | Bloqueio mantido / Bloqueio revertido |
| Reclassificar | Classificação atualizada |
| Criar nova versão (ficha) | Versão 2 criada. A versão 1 continua guardada. |

### 7.4 Erros e estados vazios

| Situação | Texto |
|---|---|
| `BLOQUEIO_PENDENTE` | Ainda há N trechos bloqueados. Ajuste o texto ou conteste o bloqueio. |
| `FICHA_DESATUALIZADA` | A ficha deste produto mudou depois da checagem. Cheque a peça de novo para gerar o link. |
| `FICHA_INVALIDA` (garantia < 7) | A garantia precisa ser de pelo menos 7 dias (CDC, art. 49). |
| `PAPEL_NAO_AUTORIZADO` | Só a marca ou Operações podem decidir sobre uma contestação. |
| Checador sem peça | Nenhuma peça checada ainda. Cole a legenda ou o roteiro acima para começar. |
| Fila vazia | Nada esperando revisão agora. |
| Sem devoluções no período | Nenhuma devolução neste período. Tente um período maior. |
| Sem chave de API | Checagem feita só com as regras. O modelo está desligado. |

---

## 8. Implementação no Streamlit

### 8.1 Arquivos

```
.streamlit/config.toml          # tema (8.2)
app/static/fonts/*.woff2        # fontes locais
app/static/favicon.png
app/ui/__init__.py
app/ui/theme.css                # tokens + componentes + animações
app/ui/theme.py                 # apply_theme(): injeta o CSS uma vez por página
app/ui/components.py            # page_header, wordmark, peca_marcada, achado, canhoto, fio, metricas, chip
app/ui/labels.py                # mapa da seção 7.2
```

Cada página começa com `apply_theme()` e `page_header(...)`. Os componentes recebem os modelos que os serviços já devolvem; nenhuma lógica de negócio entra em `app/ui/`.

### 8.2 `config.toml` (ponto de partida)

Conferir cada chave contra a versão instalada (`uv run streamlit config show`) e remover as que não existirem. A pasta `static` é servida a partir da pasta do script de entrada; confirmar o caminho das URLs abrindo uma delas no navegador.

```toml
[server]
enableStaticServing = true

[theme]
base = "light"
primaryColor = "#4B2FA8"
backgroundColor = "#F6F5F9"
secondaryBackgroundColor = "#FFFFFF"
textColor = "#1E1A2E"
linkColor = "#4B2FA8"
borderColor = "#DCD8E6"
showWidgetBorder = true
baseRadius = "4px"
baseFontSize = 16
font = "Schibsted Grotesk"
headingFont = "Schibsted Grotesk"
codeFont = "IBM Plex Mono"
chartCategoricalColors = ["#4B2FA8", "#9C8AE0", "#0E7C7B", "#7D8A9C", "#8C2F5A", "#B9B4C7"]

[theme.sidebar]
backgroundColor = "#FFFFFF"

[[theme.fontFaces]]
family = "Schibsted Grotesk"
url = "app/static/fonts/SchibstedGrotesk-Variable.woff2"
weight = "400 900"
style = "normal"

[[theme.fontFaces]]
family = "Newsreader"
url = "app/static/fonts/Newsreader-Italic-Variable.woff2"
weight = "200 800"
style = "italic"

[[theme.fontFaces]]
family = "IBM Plex Mono"
url = "app/static/fonts/IBMPlexMono-Regular.woff2"
weight = "400"
style = "normal"

[[theme.fontFaces]]
family = "IBM Plex Mono"
url = "app/static/fonts/IBMPlexMono-Medium.woff2"
weight = "500"
style = "normal"
```

Fontes: baixar os `.woff2` do subconjunto **latin** (cobre á, ã, ç, é, õ) a partir da API do Google Fonts e salvar em `app/static/fonts/`. Se a rede falhar, usar as URLs do `fonts.gstatic.com` direto no `config.toml` e registrar em `docs/decisoes.md` que a demo precisa de internet.

### 8.3 Tokens em CSS (início de `theme.css`)

```css
:root {
  --vc-papel: #F6F5F9;  --vc-folha: #FFFFFF;  --vc-tinta: #1E1A2E;
  --vc-grafite: #5C5770; --vc-risco: #DCD8E6;
  --vc-carimbo: #4B2FA8; --vc-carimbo-claro: #ECE7FB;
  --vc-linha: #0E7C7B;   --vc-linha-claro: #DDF1F0;

  --vc-bloquear: #A3261F;  --vc-bloquear-mt: #FCE4E1;  --vc-bloquear-bd: #E9A39B;
  --vc-revisar: #8A5300;   --vc-revisar-mt: #FFE59A;   --vc-revisar-bd: #E8C15A;
  --vc-registrar: #17663F; --vc-registrar-mt: #D6F0E0; --vc-registrar-bd: #8CCBA8;
  --vc-sem-relacao: #9A95AB;

  --vc-f-sistema: "Schibsted Grotesk", system-ui, sans-serif;
  --vc-f-dito: "Newsreader", Georgia, serif;
  --vc-f-id: "IBM Plex Mono", ui-monospace, monospace;

  --vc-raio-p: 4px; --vc-raio-m: 10px; --vc-raio-carimbo: 3px;
  --vc-ease: cubic-bezier(.2,.7,.2,1);
}

h1 { font: 800 40px/44px var(--vc-f-sistema); letter-spacing: -0.025em; }
h2 { font: 700 28px/34px var(--vc-f-sistema); letter-spacing: -0.015em; }
h3 { font: 700 21px/28px var(--vc-f-sistema); letter-spacing: -0.01em; }
.vc-dito  { font-family: var(--vc-f-dito); font-style: italic; font-size: 1.08em; }
.vc-id    { font: 500 13px/20px var(--vc-f-id); }
.vc-texto { max-width: 68ch; }
:focus-visible { outline: 2px solid var(--vc-carimbo); outline-offset: 2px; }
```

Para ajustar elementos nativos do Streamlit (barra lateral, `stMetric`, botões), **inspecionar o DOM real** com o Playwright já instalado e usar os `data-testid` que existirem. Não adivinhar seletores.

### 8.4 O que não pode quebrar

- `app/` continua sem importar `promessa.db.models` (critério da T14).
- Na visão Creator, nenhum texto de comprador aparece (invariante 5). O fio mostra só a crença normalizada e agregada.
- Todo texto de usuário passa por `html.escape` antes de entrar em `st.html`.
- `make lint test` continua verde.
- **Roteiros de gravação do ensaio (Playwright):** eles acham botões e páginas pelo texto. Se um rótulo mudou (seção 7), atualizar os roteiros no mesmo commit e rodar o teste curto de gravação.

---

## 9. Ordem de aplicação (com o prazo de hoje)

| Prioridade | O que | Tempo |
|---|---|---|
| **P0** | `config.toml`, fontes locais, `theme.css` com tokens, wordmark na barra lateral, favicon, `labels.py`, cabeçalhos das 5 páginas, cores das decisões nos chips | 45 min |
| **P1** | Texto checado com marca-texto + lista de achados (5.3); canhoto com carimbo (5.4); as duas animações com `is-new` | 45 min |
| **P2** | Fio nos relatórios (5.5) com animação; métricas em linha (5.6); gráficos de causas com a paleta fixa | 40 min |
| **P3** | Mesmos tokens nos slides do pitch: capa com wordmark e a frase de assinatura | fora do painel |

Se o tempo apertar, P0 e o canhoto sozinho já mudam a percepção da demo.

**Decisão a registrar em `docs/decisoes.md`:** "D8. Nome de exibição: Vincula (promessa rastreável). Código, pacote, ferramentas MCP e enums mantêm `promessa`. Mudança só na camada de apresentação."
