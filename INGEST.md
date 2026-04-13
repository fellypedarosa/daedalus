# INGEST.md — Guia de Ingestão de Novas Fontes no Daedalus

Este arquivo contém as instruções completas para que **qualquer agente LLM** (Gemini, Claude, GPT, etc.) possa ingerir novas fontes brutas e integrá-las à wiki mantendo a qualidade e a integridade do grafo de conhecimento.

**Como usar:**  Forneça este arquivo como contexto ao agente e diga:
> *"Adicionei novas notas em `raw/clipper/`. Siga as instruções do INGEST.md."*

---

## Visão Geral do Fluxo

```
  raw/clipper/nota.md          ← Fonte bruta (artigo, transcrição)
        │
        ▼
  [1] LEITURA & ANÁLISE        ← Extrair conceitos, fatos, definições
        │
        ▼
  [2] MAPEAMENTO               ← Identicar nós wiki existentes que devem ser expandidos
        │                         ou novos nós que devem ser criados
        ▼
  [3] SÍNTESE                  ← Escrever/expandir nós wiki com conteúdo sintetizado
        │
        ▼
  [4] CONEXÃO                  ← Adicionar wikilinks bidirecionais entre nós
        │
        ▼
  [5] INDEXAÇÃO                ← Atualizar index.md, log.md, Ingestion_Tracker.md
        │
        ▼
  raw/clipper/cataloged/       ← Mover fonte processada para o arquivo
```

---

## Passo 1: Leitura & Análise

**Leia cada arquivo novo** em `raw/clipper/` (NÃO os arquivos em `cataloged/`).

Para cada fonte, identifique:
- **Conceitos centrais**: Os temas principais que a fonte aborda
- **Fatos e definições**: Informações concretas que devem ser preservadas
- **Relações**: Como os conceitos se conectam entre si e com o conhecimento existente

> ⚠️ **NUNCA modifique os arquivos em `raw/`** — eles são imutáveis.

---

## Passo 2: Mapeamento

Busque na wiki por nós existentes que cubram os temas da fonte.

**Se o MCP estiver disponível:**
```
search("conceito chave da fonte")
```

**Se estiver no diretório do Daedalus:**
```bash
./daedalus.py search "conceito chave" --limit 5
```

### Regras de Mapeamento:
1. **Se o conceito já existe como nó wiki** → EXPANDA esse nó (Passo 3a)
2. **Se o conceito é novo mas relevante** → CRIE um novo nó (Passo 3b)
3. **Se o conceito é periférico ou trivial** → NÃO crie nó; apenas mencione em nós relacionados

**Critério para criar um nó novo:**
- O conceito tem substância suficiente para pelo menos 15-20 linhas
- O conceito é suficientemente distinto dos nós existentes
- O conceito pode ser interligado com pelo menos 2 nós existentes

---

## Passo 3a: Expandir Nó Existente

> 🔴 **REGRA CARDINAL: NUNCA apague ou substitua conteúdo existente. APENAS adicione.**

Ao expandir um nó:
1. **Leia o nó atual** completamente para entender o que já está coberto
2. **Identifique lacunas** — informações novas que a fonte traz
3. **Adicione** novas seções, bullets ou parágrafos nos locais apropriados
4. **Adicione a fonte** ao frontmatter YAML na lista `sources`

**Exemplo de expansão correnzta:**
```markdown
## Seção Existente
Conteúdo existente que NÃO foi tocado...

### Nova Subseção (adicionada pela ingestão)
Novo conteúdo sintetizado da fonte recém-ingerida.
Inclui [[wikilinks|wikilinks]] para nós relacionados.
```

---

## Passo 3b: Criar Nó Novo

Cada nó novo DEVE seguir este template:

```markdown
---
tags: [domínio, subtópico_1, subtópico_2]
date_created: YYYY-MM-DD
sources:
  - "[[Nome_da_Fonte_Original]] (Clipper)"
---
# Título do Nó

Parágrafo introdutório de 2-3 linhas explicando o conceito de forma clara
e contextualizada. Deve estabelecer o "porquê" do conceito importar.

## Seção Principal
Conteúdo sintetizado — NÃO copie texto verbatim da fonte.
Use suas próprias palavras para criar uma explicação coesa.

Inclua links internos: [[Conceito_Relacionado|Conceito Relacionado]].

## Seções Adicionais
Organize por subtemas conforme necessário.

## Relações
- Relaciona-se com [[Nó_A|Nó A]] no contexto de X
- Expande conceitos de [[Nó_B|Nó B]]
```

### Regras do Frontmatter:
- `tags`: lista com domínio principal + subtópicos relevantes (minúsculas, snake_case)
- `date_created`: data de criação (formato YYYY-MM-DD)
- `sources`: lista de referências à fonte original

### Escolha do Domínio:
| Domínio | Quando usar |
|:---|:---|
| `Computer_Science/` | Algoritmos, compiladores, criptografia, teoria computacional |
| `Infrastructure_and_DevOps/` | Redes, storage, virtualização, Linux, containers |
| `Software_Engineering/` | Arquitetura de software, open source, design, licenças |
| `Databases/` | RDBMS, NoSQL, escalabilidade de dados |
| `Programming/` | Linguagens, paradigmas, concorrência, memória |
| `Operating_Systems/` | Internals de OS, boot, segurança, histórico |
| `Web_Development/` | Frontend, otimização, frameworks web |
| `Artificial_Intelligence/` | LLMs, infraestrutura de IA, ML |
| `Hardware/` | Arquitetura de hardware, CPUs, performance |
| `People/` | Perfis de figuras relevantes no campo |
| `Concepts/` | Conceitos transversais que não cabem em um domínio |

### Nomenclatura de Arquivos:
- Use **inglês** para nomes de arquivo
- Use **underscores** entre palavras: `Memory_Management.md`
- Seja descritivo mas conciso: `TLS_and_Certificate_Authorities.md` ✅ (não `TLS.md`)

---

## Passo 4: Conexão (Wikilinks)

Esta é a etapa **mais importante** para a qualidade do grafo.

### Formato de Wikilinks:
```
[[Stem_Com_Underscore|Nome Legível]]
```

**Exemplos:**
- `[[Memory_Management|Memory Management]]` ✅
- `[[Memory Management]]` ❌ (sem underscore = ghost link)
- `[[Memory_Management]]` ⚠️ (funciona, mas sem alias legível)

### Regras de Linkagem:
1. **Cada nó novo DEVE ter pelo menos 3 outlinks** para nós existentes
2. **Atualize nós existentes** para incluir backlinks ao nó novo (bidirecionalidade)
3. **Não force links** — só linke quando há relação semântica real
4. **Não linke dentro do frontmatter YAML** (exceto na lista `sources`)
5. **Linke na primeira menção** do conceito no texto, não em todas

### Densidade ideal:
- Nó médio: 3-6 outlinks
- Hub nodes (conceitos fundamentais): 6-15 outlinks
- Leaf nodes (conceitos específicos): 1-3 outlinks

### Padrão de bidirecionalidade:
Quando criar `Novo_Conceito.md` com link para `Conceito_Existente.md`:
1. No novo nó: `...utiliza princípios de [[Conceito_Existente|Conceito Existente]]...`
2. No nó existente: adicione uma menção tipo `...também relevante para [[Novo_Conceito|Novo Conceito]]...`

---

## Passo 5: Indexação

### 5.1 — Atualizar `wiki/index.md`
Adicione cada nó novo ao final da seção `## Pages`:
```markdown
- [[Domínio/Nome_do_Nó.md|Nome Legível]]: Descrição curta de uma linha.
```

### 5.2 — Atualizar `wiki/log.md`
Adicione uma entrada no final:
```markdown
## [YYYY-MM-DD] ingest | Descrição do que foi ingerido. Nós criados: X. Nós expandidos: Y. Fontes processadas: Z.
```

### 5.3 — Atualizar `wiki/Ingestion_Tracker.md`
Adicione um checkbox para a nova fonte:
```markdown
- [x] Nome da fonte (processada em YYYY-MM-DD)
```

### 5.4 — Mover fonte para `cataloged/`
```bash
mv raw/clipper/fonte_processada.md raw/clipper/cataloged/
```

---

## Passo 6: Verificação

Após completar a ingestão, rode o audit:

**Via MCP:**
```
audit()
```

**Via CLI:**
```bash
./daedalus.py audit
```

**Verifique:**
- [ ] 0 ghost links (todos os wikilinks resolvem para nós reais)
- [ ] 0 nós órfãos (todo nó tem pelo menos 1 backlink ou está no index)
- [ ] 0 missing frontmatter
- [ ] 0 nós faltando no index

**Se houver problemas**, corrija antes de considerar a ingestão completa.

---

## Checklist Rápido

Para cada fonte em `raw/clipper/`:

```
[ ] Fonte lida e conceitos identificados
[ ] Nós wiki existentes mapeados (search)
[ ] Nós expandidos com conteúdo novo (sem apagar nada)
[ ] Nós novos criados com frontmatter completo
[ ] Wikilinks bidirecionais adicionados (≥3 por nó novo)
[ ] Formato de link: [[Stem|Alias]] (com underscore)
[ ] wiki/index.md atualizado
[ ] wiki/log.md atualizado
[ ] wiki/Ingestion_Tracker.md atualizado
[ ] Fonte movida para raw/clipper/cataloged/
[ ] Audit rodado e limpo (0 issues)
```

---

## Anti-Padrões (O que NÃO fazer)

| ❌ Errado | ✅ Correto |
|:---|:---|
| Copiar texto verbatim da fonte | Sintetizar com suas próprias palavras |
| Apagar conteúdo existente ao expandir | Apenas adicionar seções novas |
| Usar `[[Nome Com Espaço]]` nos links | Usar `[[Nome_Com_Underscore\|Nome Com Espaço]]` |
| Criar nó com <10 linhas | Mínimo 15-20 linhas com substância |
| Criar nó sem wikilinks | Mínimo 3 outlinks para nós existentes |
| Criar nó sem frontmatter YAML | Sempre incluir tags, date_created, sources |
| Linkar conceitos sem relação semântica | Só linkar quando há conexão real |
| Esquecer de atualizar o index | Sempre adicionar ao index.md |
| Deixar fonte em `raw/clipper/` | Mover para `cataloged/` após processamento |

---

## Idioma

- **Nós wiki**: escritos em **inglês**
- **Fontes brutas**: podem estar em qualquer idioma (maioria em português)
- **Nomes de arquivo**: sempre em **inglês** com underscores
- **O agente deve sintetizar** o conteúdo da fonte em inglês, independente do idioma origimal
