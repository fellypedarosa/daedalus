# AGENTS.md — Instruções para Agentes LLM no Daedalus

Este arquivo define o protocolo operacional para **qualquer agente LLM** (Antigravity, GeminiCLI, Claude Code, etc.) que interaja com o repositório Daedalus.

---

## Arquitetura do Repositório

```
Daedalus/
├── wiki/                  ← CAMADA PRINCIPAL: nós síntese gerados pelo LLM
│   ├── index.md           ← Índice global (leia primeiro em toda sessão)
│   ├── log.md             ← Log cronológico de operações
│   ├── Ingestion_Tracker.md ← Status de ingestão de fontes brutas
│   └── [Domínio]/
│       └── [Nó].md        ← Páginas de conhecimento sintetizado
├── raw/                   ← Fontes brutas (IMUTÁVEIS — nunca modifique)
│   └── clipper/
│       ├── [fonte].md     ← Transcrições e artigos originais
│       └── cataloged/     ← Fontes já ingeridas na wiki
├── daedalus.py            ← CLI de navegação (requer Obsidian CLI)
└── daedalus_mcp.py        ← MCP Server (acesso cross-project, sem dependências)
```

---

## Acesso Cross-Project (MCP Server)

O Daedalus MCP Server está registrado globalmente em `~/.gemini/settings.json`.
Qualquer agente LLM (Gemini CLI, Antigravity) em **qualquer diretório** pode usar
as tools nativamente — sem shell-out, sem parsing de texto.

### Tools MCP Disponíveis:
| Tool | Descrição |
|:---|:---|
| `summary()` | Visão condensada: domínios, hubs, folhas. **Use primeiro.** |
| `search(query, limit)` | Busca full-text com scoring de relevância |
| `read(filepath)` | Lê o conteúdo completo de um nó (aceita stem ou path) |
| `list_nodes()` | Lista todos os nós agrupados por domínio |
| `backlinks(node_name)` | Quem aponta PARA este nó |
| `outlinks(node_name)` | Para onde este nó aponta |
| `crawl(node_name)` | Contexto completo: conteúdo + links in/out |
| `audit()` | Diagnóstico de saúde: ghost links, orphans, coverage |

---

## Operações Disponíveis

### 🔍 Busca Contextual
```bash
# Buscar no wiki (padrão, só nós síntese)
./daedalus.py search "minha query"

# Buscar incluindo fontes brutas
./daedalus.py search "minha query" --all

# Limitar resultados
./daedalus.py search "minha query" --limit 5
```

### 📖 Leitura de Nó
```bash
./daedalus.py read wiki/Domínio/Nome_do_Nó.md
```

### 🔗 Navegação por Links
```bash
# Quem aponta PARA este nó?
./daedalus.py backlinks wiki/Domínio/Nome_do_Nó.md

# Para onde este nó aponta?
./daedalus.py outlinks wiki/Domínio/Nome_do_Nó.md

# Crawl completo: backlinks + outlinks + conteúdo
./daedalus.py crawl wiki/Domínio/Nome_do_Nó.md
```

### 🩺 Diagnóstico do Vault
```bash
# Audit completo: ghost links, orphans, frontmatter, coverage
./daedalus.py audit

# Output estruturado para consumo programático
./daedalus.py audit --format json
```

### 📊 Resumo do Vault
```bash
# Visão condensada: domínios, hubs, folhas
./daedalus.py summary

# Output JSON para agentes
./daedalus.py summary --format json
```

### 🖥️ Sincronização de UI (abre no Obsidian do usuário)
```bash
obsidian search:open query="minha query"
```

---

## Fluxo de Trabalho: Respondendo Perguntas Complexas

0. **[ORIENTAÇÃO]** `./daedalus.py summary --format json` para entender a topologia do vault antes de buscar
1. **[BUSCA]** `./daedalus.py search "<termos da pergunta>" --limit 5`
2. **[IDENTIFICAR]** Ler a lista de nós retornados; priorizar nós em `wiki/` sobre fontes em `raw/`
3. **[LER]** `./daedalus.py read wiki/[arquivo_relevante]`
4. **[EXPANDIR]** `./daedalus.py backlinks wiki/[arquivo]` para descobrir nós relacionados
5. **[SINTETIZAR]** Consolidar os dados lidos para responder ao usuário

---

## Fluxo de Trabalho: Ingerindo Novas Fontes

1. Mover o arquivo de `raw/clipper/` para `raw/clipper/cataloged/` após ingestão
2. Ler o arquivo fonte: `./daedalus.py read raw/clipper/[fonte].md`
3. Identificar nós wiki existentes relevantes: `./daedalus.py search "<conceito>"`
4. Expandir nós existentes com `multi_replace_file_content` (NUNCA apagar conteúdo)
5. Criar novos nós se necessário
6. Atualizar `wiki/index.md` com o novo nó
7. Atualizar `wiki/log.md` com a entrada de ingestão
8. Marcar a fonte em `wiki/Ingestion_Tracker.md`

---

## Fluxo de Trabalho: Lint (Pente Fino)

Periodicamente, execute:
```bash
# Audit completo integrado — substitui scripts avulsos
./daedalus.py audit

# Output JSON para processamento
./daedalus.py audit --format json
```

---

## Convenções de Nós Wiki

Cada arquivo `.md` em `wiki/` deve ter:
```yaml
---
tags: [domínio, subtópico]
date_created: YYYY-MM-DD
sources:
  - "[[Nome da Fonte]] (Clipper)"
---
```

- **Nunca remova ou delete conteúdo existente** — apenas expanda
- **Use `LNK [Nome](path)` na seção Metadata** para rastrear fontes originais
- **Use `#ingested` na tag Status** apenas após verificação completa

---

## Domínios Existentes

| Domínio                         | Escopo                                               |
|---------------------------------|------------------------------------------------------|
| `Computer_Science/`             | Algoritmos, Compiladores, Criptografia, Teoria       |
| `Infrastructure_and_DevOps/`    | Redes, Storage, Virtualização, Linux, Containers     |
| `Software_Engineering/`         | Arquitetura Web, Open Source, Design, Licenças       |
| `Databases/`                    | RDBMS, NoSQL, Escalabilidade                         |
| `Programming/`                  | Ecossistema de Linguagens, Memória, Concorrência      |
| `Operating_Systems/`            | Histórico, Internals, Segurança                      |
| `Web_Development/`              | Frontend, Otimização                                 |
| `Artificial_Intelligence/`      | LLMs, Infraestrutura de IA                           |
| `Hardware/`                     | Arquitetura, Performance, CPUs                       |
| `People/`                       | Perfis de figuras relevantes                         |
| `Concepts/`                     | Conceitos transversais                               |
