# Recuperação de conhecimento no Daedalus

Comandos de host deste guia são executados na raiz do repositório, acima de .mcp/.

## Uso pelo agente

`search(query, limit=5, scope="all", mode="auto", output="text")` pesquisa Markdown de `wiki/` e `raw/`. Os dois argumentos antigos continuam válidos; o escopo padrão agora inclui fontes brutas. Use `scope="wiki"` ou `scope="raw"` para restringir a consulta.

- `mode="auto"`: lexical e, quando preparado, semântico multilíngue.
- `mode="exact"`: correspondência literal, distinguindo maiúsculas/minúsculas, sem aproximação semântica.
- `mode="themes"`: representantes de documentos relevantes com diversidade de domínios e tags. A saída não garante cobertura exaustiva.
- `output="json"`: string JSON com `schema_version=1`; não é uma migração para `structuredContent` nativo.
- `limit`: de 1 a 20 documentos; até duas passagens por documento, dentro do orçamento da resposta.

O resultado identifica documento, camada, seção, linhas, offsets de caracteres, hash da versão, canais de recuperação e referências de origem. Os offsets referem-se ao texto decodificado em UTF-8, com substituição de bytes inválidos. O score ordena resultados; não representa probabilidade de verdade.

As passagens são literais. Uma passagem encurtada recebe `excerpt=true`; seu hash continua identificando a passagem indexada completa, enquanto o hash do documento permite verificar a versão. `read(path)` fornece o conteúdo integral. Documentos alterados depois da indexação são omitidos, com aviso de atualização pendente.

`read`, `backlinks`, `outlinks` e `crawl` aceitam caminhos, nomes, aliases e referências `file://` resolvíveis. Nomes ambíguos apresentam os caminhos candidatos. Links para fontes raw são navegáveis. `crawl` lê somente o documento solicitado e lista seus vizinhos.

`summary`, `list_nodes` e `audit` continuam descrevendo os nós wiki. Arquivos homônimos são distintos. O índice, log e tracker não são resultados temáticos, mas permanecem explicitamente legíveis por seus caminhos. Código, configurações e arquivos externos a wiki/raw não integram a consulta.

## Arquitetura

`daedalus_search/` independe de FastMCP e Obsidian. A CLI `daedalus.py` continua usando o Obsidian.

1. O parser lê Markdown, separa metadados, encontra referências e cria passagens por seção/bloco. Blocos extensos são divididos por linhas ou offsets, sem reescrever sua origem. Links dentro de cercas de código não formam relações.
2. SQLite/FTS5 mantém documentos, passagens e relações. BM25 pondera título, aliases, seção e corpo; símbolos técnicos também têm correspondência literal.
3. O encoder ONNX local gera vetores normalizados. A busca compara uma matriz de vetores por similaridade exata, sem banco vetorial externo.
4. RRF combina posições dos rankings lexical, semântico e literal.
5. O grafo pode acrescentar candidatos de um salto, com limites de sementes e passagens. Autoria não promove relevância temática.
6. A seleção agrupa por documento, reduz repetição e limita o contexto. Reranking local é opcional.

Referências técnicas: [FTS5](https://www.sqlite.org/fts5.html), [RRF](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion), [recuperação e reordenação](https://www.sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html).

## Índice e atualização

O Markdown é a fonte da verdade. Nenhuma operação do indexador edita notas, faz ingestão ou corrige conteúdo.

Cada atualização prepara um banco imutável `generation-<id>.sqlite`, reutiliza embeddings compatíveis, verifica integridade e hashes e publica `current.json` atomicamente. Consultas usam uma geração consistente. Um lock de arquivo serializa escritores; a geração anterior permanece disponível durante a preparação.

Hashes detectam alterações, renomeações e remoções. Versões de parser, schema, tokenizer, segmentação e modelo invalidam derivados incompatíveis. Os modelos são identificados pelo manifesto, revisão e checksums de seus arquivos. Mudanças de pesos/configuração de modelos devem ser acompanhadas de reinício do processo. Um cache auxiliar de vetores, confirmado por lotes e identificado por modelo/hash da entrada, permite retomar cálculos interrompidos sem publicar uma geração parcial.

O servidor prepara um índice lexical quando não existe índice e atualiza periodicamente em uma thread. A construção semântica ocorre em segundo plano, preservando a busca lexical. Se um modelo falhar, a resposta identifica o funcionamento lexical. Banco ilegível ou incompatível produz erro explícito, não uma busca vazia bem-sucedida.

As gerações anteriores são preservadas para leitores durante as atualizações. Sua limpeza é administrativa: não remover a geração ativa nem gerações ainda em uso. Arquivos `building-*` de processos interrompidos podem ser removidos somente após confirmar que não há escritor ativo.

```bash
DAEDALUS_INGEST_DIR="$PWD/.mcp/tmp/cli-state/ingest" \
DAEDALUS_SYNC_DIR="$PWD/.mcp/tmp/cli-state/sync" \
.mcp/.venv/bin/python .mcp/scripts/reindex_search.py \
  --vault examples/vault --index-dir .mcp/tmp/search-index --lexical-only

DAEDALUS_INGEST_DIR="$PWD/.mcp/tmp/cli-state/ingest" \
DAEDALUS_SYNC_DIR="$PWD/.mcp/tmp/cli-state/sync" \
.mcp/.venv/bin/python .mcp/scripts/reindex_search.py \
  --vault examples/vault --index-dir .mcp/tmp/search-index \
  --model-dir /tmp/daedalus-models/e5-small
```

Não usar um SQLite ativo dentro da sincronização do Dropbox. O padrão local é um diretório por vault/configuração em `/tmp/daedalus-search/`. Ao informar o diretório explicitamente, usar diretórios diferentes para experimentos com modelos ou segmentações diferentes. O Compose público usa `search-index`, com nome isolado pelo projeto, sem volumes externos.

## Preparação dos modelos

Instalar as dependências locais opcionais:

```bash
.mcp/.venv/bin/python -m pip install -r .mcp/requirements-search.txt
```

Somente o preparador acessa a rede, para baixar artefatos públicos. Ele não lê as notas nem envia perguntas ou documentos. O servidor carrega apenas arquivos locais, verifica seus hashes e não faz download durante consultas.

```bash
.mcp/.venv/bin/python .mcp/scripts/prepare_search_model.py \
  e5-small /tmp/daedalus-models/e5-small

.mcp/.venv/bin/python .mcp/scripts/prepare_search_model.py \
  minilm /tmp/daedalus-models/minilm

.mcp/.venv/bin/python .mcp/scripts/prepare_search_model.py \
  reranker /tmp/daedalus-models/reranker
```

No Compose público, `search-models` é um volume do projeto montado somente para
leitura. Sem pesos, a demonstração funciona em modo lexical. Para experimentar o
encoder, prefira a preparação em Python descrita no [README público](../../README.md#habilitar-embeddings-locais),
com diretório persistente explícito. Reinicie o processo após alterar modelo ou pesos.
A preparação de um volume Docker com pesos é uma operação avançada não incluída no exemplo básico.

O preparador resolve a revisão e registra o commit exato em `model.json`. Para reproduzir um experimento, passar `--revision <commit-do-modelo>`. Preservar também esse manifesto na implantação. Os modelos disponíveis são exports ONNX quantizados do E5 multilíngue pequeno, MiniLM multilíngue e mMARCO MiniLM para reordenação. O E5 recebe os prefixos de pergunta e passagem exigidos por seu treinamento.

O tamanho da passagem usa o tokenizer do modelo, reservando contexto para título e seção. Inputs que excedem a janela são rejeitados, sem truncamento silencioso. Consultas longas demais para o modelo podem resultar em fallback lexical; o aviso identifica a indisponibilidade semântica.

## Configuração

| Variável | Finalidade / padrão local |
| --- | --- |
| `DAEDALUS_VAULT_DIR` | Raiz das notas; padrão local: raiz do repositório, acima de .mcp/ |
| `DAEDALUS_INDEX_DIR` | Diretório de gerações; padrão local fora do vault em `/tmp` |
| `DAEDALUS_MODEL_DIR` | Diretório preparado do encoder; ausente significa busca lexical |
| `DAEDALUS_RERANKER_DIR` | Diretório preparado do reranker; ausente significa desativado |
| `DAEDALUS_INDEX_INTERVAL` | Intervalo de atualização em segundos; 60; zero desativa a thread |
| `DAEDALUS_PASSAGE_TOKENS` | Alvo de segmentação; 256, limitado pelo contexto do modelo |
| `DAEDALUS_CONTEXT_CHARS` | Orçamento da resposta JSON; 18.000 |
| `DAEDALUS_GRAPH` | `1` habilita expansão; padrão MCP `0` até aprovação da avaliação |

No Compose, o grafo começa desativado; o reranker permanece opcional. O encoder de
referência é E5 multilíngue pequeno. Não há benchmark público validado nem medições
do corpus privado nesta distribuição.

`/health` informa que o processo HTTP responde. `/ready` retorna 200 somente com uma geração legível para consulta, ou 503 quando o índice não está disponível. Readiness lexical não significa que todos os vetores já foram construídos. O estado detalhado está disponível administrativamente por `SearchEngine.status()`, sem expor perguntas nem conteúdo em um endpoint público.

## Testes e avaliação

```bash
XDG_STATE_HOME="$PWD/.mcp/tmp/test-state" \
  .mcp/.venv/bin/python -m unittest discover -s .mcp/tests -t .mcp -v

DAEDALUS_TEST_MODEL_DIR=/tmp/daedalus-models/e5-small \
  PYTHONPATH=.mcp .mcp/.venv/bin/python -m unittest tests.search.test_semantic.RealModelTests -v

docker build -f .mcp/Dockerfile --target test --tag daedalus-search-test .mcp
```

Os testes de escrita do MCP usam vaults sintéticos temporários. Testes de vetor sintético verificam o contrato e o cache; não comprovam qualidade semântica. O teste de modelo real exige opt-in com um modelo já preparado.

O runner inclui oito perguntas didáticas sobre `examples/vault`, com julgamentos
sintéticos sem revisão independente. Elas demonstram reprodução e conferência de
citações; não comprovam qualidade geral ou superioridade de uma arquitetura.

```bash
DAEDALUS_INGEST_DIR="$PWD/.mcp/tmp/cli-state/ingest" \
DAEDALUS_SYNC_DIR="$PWD/.mcp/tmp/cli-state/sync" \
.mcp/.venv/bin/python .mcp/scripts/evaluate_search.py \
  --vault examples/vault --backend legacy --split tuning --output .mcp/tmp/baseline.json

DAEDALUS_INGEST_DIR="$PWD/.mcp/tmp/cli-state/ingest" \
DAEDALUS_SYNC_DIR="$PWD/.mcp/tmp/cli-state/sync" \
.mcp/.venv/bin/python .mcp/scripts/evaluate_search.py \
  --vault examples/vault --backend hybrid --split tuning \
  --model-dir /tmp/daedalus-models/e5-small \
  --vault examples/vault --index-dir .mcp/tmp/search-index --output .mcp/tmp/hybrid.json
```

Comparar `legacy`, `lexical`, `hybrid`, `graph` e `rerank`. Para `rerank`, fornecer também `--reranker-dir`. Selecionar configurações no conjunto `tuning` antes de executar `validation`. O relatório registra manifesto do corpus, hashes da implementação, dataset, configuração, métricas por categoria, referências verificadas e consumo de memória. A comparação de ranking entre versões deve filtrar o mesmo escopo wiki; a cobertura nova em raw é avaliada separadamente.

CI executa somente verificações, incluindo o detector de credenciais; não há deploy automático. Correspondências existentes precisam de triagem com o usuário. Não editar notas nem afrouxar regras silenciosamente para tornar a suíte verde. A configuração de proteção da main no GitHub e os limites operacionais de produção exigem revisão dos checks e das medições.
