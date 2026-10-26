# Daedalus 2.0

**Uma base de conhecimento em Markdown que agentes podem consultar, conectar e expandir pelo Model Context Protocol (MCP).**

O Daedalus transforma fontes e notas em uma wiki persistente, com referências ao material original e ferramentas para buscar informações em ambas as camadas. A versão 2.0 acrescenta uma engine de busca híbrida local, resultados com evidências e um fluxo de ingestão revisável.

Esta edição pública é uma **prova de conceito** extraída de uma implementação existente. Seu histórico Git começa nesta publicação; a identificação 2.0 corresponde ao estágio do projeto.

## Ideia e inspiração

O projeto foi inspirado no [LLM Wiki, de Andrej Karpathy](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f): manter fontes originais e uma wiki de sínteses interligadas, construída e atualizada com a ajuda de um agente. O conhecimento elaborado permanece em arquivos que podem ser consultados e revisados ao longo do tempo.

O Daedalus implementa esse padrão com acesso por MCP, busca sobre fontes e sínteses e um processo de ingestão que apresenta as alterações antes de aplicá-las. É uma implementação independente, sem vínculo oficial ou endosso de Karpathy.

## Como funciona

```text
Fontes e notas do usuário
          |
          v
        raw/ --------------------+
          |                      |
  agente lê e propõe             |
          |                      |
  revisão e aprovação            |
          v                      |
        wiki/ -------------------+
          |                      |
          +---- índice local ----+
                       |
              busca e navegação MCP
                       |
              agente lê as evidências
                       |
              resposta com referências
```

- **`raw/`** guarda fontes originais: notas autorais, textos e outros documentos Markdown.
- **`wiki/`** guarda sínteses por assunto, fontes e relações explícitas por wikilinks.
- **`.mcp/`** contém a aplicação, os testes e a documentação técnica.

Uma fonte pode ser um texto escrito pelo próprio usuário; não precisa vir de um site ou artigo externo. O indexador lê os arquivos e mantém dados derivados, sem reescrever o acervo.

## A busca na versão 2.0

A engine anterior consultava o texto das notas wiki com pontuação simples e expansão de termos por um dicionário fixo. A versão 2.0 oferece uma arquitetura própria de recuperação:

| Camada | Papel |
| --- | --- |
| SQLite FTS5/BM25 | Recuperar termos, títulos, aliases e seções relevantes |
| Embeddings multilíngues ONNX | Recuperar passagens por proximidade semântica quando há modelo preparado |
| Reciprocal Rank Fusion | Combinar as posições dos resultados dos canais de recuperação |
| Passagens e evidências | Identificar seção, linhas, offsets, versão do documento e origem |
| Índice incremental | Reaproveitar embeddings compatíveis e publicar gerações consistentes do índice |
| Wikilinks | Navegar entre conceitos, sínteses e fontes |

O modelo de embeddings roda no processo do servidor, com inferência local. Não exige uma API de embeddings nem um banco vetorial externo. Seu download é explícito; consultas não baixam pesos. Um diretório persistente permite reutilizar o mesmo modelo nas próximas execuções.

**Sem modelo disponível, a busca continua em modo lexical.** A expansão de candidatos pelo grafo e o reranker são recursos opcionais, desativados por padrão no MCP. A navegação por links funciona independentemente deles.

Essa evolução amplia os mecanismos de recuperação e a rastreabilidade dos resultados. Ainda não há um benchmark público validado que quantifique ganhos gerais de precisão frente à versão anterior.

### Exemplos de consulta pelo MCP

```python
search(query="Como recuperar dados depois de uma falha?", scope="all", mode="auto")
search(query="um identificador literal", scope="raw", mode="exact")
search(query="armazenamento e recuperação", scope="wiki", mode="themes", limit=5)
```

Essas expressões representam chamadas de ferramentas pelo cliente MCP. `scope` aceita `wiki`, `raw` e `all`; `auto` combina os canais disponíveis, `exact` procura correspondência literal e `themes` seleciona representantes temáticos. O modo temático não garante um inventário exaustivo do acervo.

Use `read` com o caminho retornado para conferir o documento completo. O score serve para ordenar resultados; não é uma medida de veracidade.

## Ferramentas para agentes

| Grupo | Ferramentas principais |
| --- | --- |
| Orientação | `summary`, `list_nodes`, `test` |
| Consulta | `search`, `read` |
| Relações | `backlinks`, `outlinks`, `crawl` |
| Diagnóstico | `audit` |
| Captura | `create_raw_note` |
| Ingestão | `ingest_sources`, `ingest_prepare`, `ingest_preview`, `ingest_apply`, `ingest_status` |

Uma consulta costuma seguir `summary → search → read → navegação por links`. O agente usa as evidências recuperadas para elaborar a resposta.

A engine de busca não chama um LLM para produzir respostas. A interpretação, a síntese e as decisões editoriais ficam com o agente conectado. Obsidian pode ser usado para navegar e editar a base, mas não é requisito do servidor MCP. A CLI auxiliar integrada ao Obsidian tem funcionamento próprio.

## Captura e ingestão são etapas separadas

1. O agente usa `create_raw_note` para enviar o conteúdo de uma nota à categoria escolhida: `ai`, `clipper`, `youtube` ou `local`.
2. Quando solicitado, lista fontes pendentes e prepara a ingestão, lendo a fonte e os nós relacionados.
3. Propõe criações ou expansões e apresenta o diff retornado por `ingest_preview`.
4. Após a aprovação humana, aplica a proposta e acompanha o estado com `ingest_status`.

O contrato editorial orienta a preservação das fontes e expansões aditivas. Um digest identifica a proposta validada; a aprovação humana continua sendo responsabilidade do fluxo do agente.

Gravação, disponibilidade na busca e publicação Git têm estados separados. Há suporte a um executor de publicação no host, mas ele exige configuração deliberada. A demonstração local não deve instalar cron nem publicar notas automaticamente em um remoto público. Sem executor, uma operação salva pode informar publicação pendente.

## Estrutura da edição pública

```text
daedalus/
|-- README.md
|-- LICENSE
|-- .gitignore
|-- .github/workflows/       # Testes da edição pública
|-- .mcp/                   # Aplicação, testes e documentação
|-- examples/vault/         # Corpus sintético da demonstração
|   |-- raw/
|   `-- wiki/
|-- raw/                    # Acervo local pessoal, ignorado pelo Git
`-- wiki/                   # Sínteses pessoais, ignoradas pelo Git
```

A distribuição pública deve conter apenas exemplos sintéticos revisados. A instalação privada de origem, suas notas, tokens, índices e configurações de infraestrutura não fazem parte desta demonstração.

## Começar localmente

Os comandos partem da raiz do repositório. O ambiente de referência usa Linux e Python 3.12; alguns componentes de coordenação usam `fcntl`/`flock`. No Windows, considere um ambiente Linux como WSL2; suporte nativo não foi validado.

```bash
python3.12 -m venv .mcp/.venv
.mcp/.venv/bin/python -m pip install -r .mcp/requirements.lock
```

O lock inclui as dependências de inferência. Uma instalação somente lexical pode usar `.mcp/requirements.txt`; `.mcp/requirements-search.txt` contém as dependências adicionais da busca semântica.

O corpus sintético fictício está em `examples/vault`. Para consultas de leitura, inicie o servidor em STDIO com derivados isolados:

```bash
mkdir -p .mcp/tmp/demo-state
DAEDALUS_VAULT_DIR="$PWD/examples/vault" \
DAEDALUS_INDEX_DIR="$PWD/.mcp/tmp/demo-state/index" \
DAEDALUS_INGEST_DIR="$PWD/.mcp/tmp/demo-state/ingest" \
DAEDALUS_SYNC_DIR="$PWD/.mcp/tmp/demo-state/sync" \
DAEDALUS_AUDIT_LOG="$PWD/.mcp/tmp/demo-state/access.jsonl" \
DAEDALUS_TEST_AUDIT_LOG="$PWD/.mcp/tmp/demo-state/test.jsonl" \
DAEDALUS_MODEL_DIR="" DAEDALUS_RERANKER_DIR="" \
  .mcp/.venv/bin/python .mcp/daedalus_mcp.py
```

STDIO é um transporte para um cliente MCP. Normalmente, o cliente inicia esse processo; ele não é uma interface de chat no terminal. Um exemplo genérico de configuração, cujos caminhos devem ser substituídos por caminhos absolutos locais:

```json
{
  "mcpServers": {
    "daedalus-local": {
      "command": "/caminho/daedalus/.mcp/.venv/bin/python",
      "args": ["/caminho/daedalus/.mcp/daedalus_mcp.py"],
      "env": {
        "DAEDALUS_VAULT_DIR": "/caminho/daedalus/examples/vault",
        "DAEDALUS_INDEX_DIR": "/caminho/daedalus/.mcp/tmp/client/index",
        "DAEDALUS_INGEST_DIR": "/caminho/daedalus/.mcp/tmp/client/ingest",
        "DAEDALUS_SYNC_DIR": "/caminho/daedalus/.mcp/tmp/client/sync",
        "DAEDALUS_AUDIT_LOG": "/caminho/daedalus/.mcp/tmp/client/access.jsonl",
        "DAEDALUS_TEST_AUDIT_LOG": "/caminho/daedalus/.mcp/tmp/client/test.jsonl",
        "DAEDALUS_MODEL_DIR": "",
        "DAEDALUS_RERANKER_DIR": ""
      }
    }
  }
}
```

Crie antes o diretório `.mcp/tmp/client` para os logs. A sintaxe e o local da configuração dependem do cliente. Confira a conexão chamando `test` e depois `summary`. Para demonstrar criação e ingestão, use uma cópia temporária do corpus de exemplo, com estados isolados.

### Habilitar embeddings locais

Prepare o modelo uma vez em um diretório persistente fora do repositório:

```bash
mkdir -p "$HOME/.local/share/daedalus-public/models"
.mcp/.venv/bin/python .mcp/scripts/prepare_search_model.py \
  e5-small "$HOME/.local/share/daedalus-public/models/e5-small" \
  --revision 761b726dd34fb83930e26aab4e9ac3899aa1fa78
```

Esse comando baixa artefatos públicos do modelo `Xenova/multilingual-e5-small`; não lê nem envia notas. O preparador registra a revisão e os checksums em `model.json`.

Passe o diretório ao processo MCP, ou acrescente a variável à configuração do cliente:

```bash
DAEDALUS_VAULT_DIR="$PWD/examples/vault" \
DAEDALUS_MODEL_DIR="$HOME/.local/share/daedalus-public/models/e5-small" \
DAEDALUS_INDEX_DIR="$PWD/.mcp/tmp/model-demo/index" \
DAEDALUS_INGEST_DIR="$PWD/.mcp/tmp/model-demo/ingest" \
DAEDALUS_SYNC_DIR="$PWD/.mcp/tmp/model-demo/sync" \
DAEDALUS_AUDIT_LOG="$PWD/.mcp/tmp/demo-state/access.jsonl" \
DAEDALUS_TEST_AUDIT_LOG="$PWD/.mcp/tmp/demo-state/test.jsonl" \
DAEDALUS_RERANKER_DIR="" \
  .mcp/.venv/bin/python .mcp/daedalus_mcp.py
```

O modelo é reutilizado enquanto seus arquivos forem preservados. Um novo download é necessário se você remover esses arquivos ou decidir trocar a revisão/modelo. A construção dos embeddings das notas é uma etapa distinta, executada pelo indexador, e pode continuar em segundo plano.

## Acesso remoto e privacidade

O servidor também oferece Streamable HTTP autenticado. Cada instalação precisa de seus próprios tokens e base de conhecimento; obter o código público não concede acesso a outra instalação.

- Tokens e configurações locais devem permanecer fora do Git.
- Escrita HTTP exige o escopo explícito `daedalus:ingest`.
- A inicialização HTTP exige configuração de autenticação válida; requisições sem token ou com token inválido devem ser recusadas.
- O transporte remoto deve ter HTTPS configurado na implantação. O modo STDIO é local.
- O cálculo de embeddings é local, mas o agente cliente recebe os trechos consultados. O uso desses trechos por um provedor de LLM depende da configuração e das políticas desse cliente.

Docker é uma opção de empacotamento. A configuração local usa porta em `127.0.0.1`, uma cópia descartável do exemplo e volumes isolados. Consulte o [guia técnico](.mcp/README.md#docker-local).

## Testes e limites

A cópia pública foi verificada com bases sintéticas em Python 3.12 e 3.14, build Docker e chamadas reais por STDIO e HTTP. O encoder real permanece opcional e não foi validado nesta preparação.

```bash
XDG_STATE_HOME="$PWD/.mcp/tmp/test-state" \
  .mcp/.venv/bin/python -m unittest discover -s .mcp/tests -t .mcp -v
docker build -f .mcp/Dockerfile --target test --tag daedalus-public-test .mcp
```

Os testes de escrita usam bases sintéticas e remotos Git locais temporários. Há cobertura de busca, autenticação, limites de caminhos, ingestão, preservação das fontes e coordenação de publicação. A suíte completa inclui heurísticas de detecção de credenciais; o target Docker executa um subconjunto documentado.

O teste opcional de encoder real exige um modelo preparado. Testes com vetores sintéticos verificam contratos e cache, sem medir qualidade semântica. O avaliador permite comparar implementações, mas uma avaliação de qualidade exige perguntas representativas, julgamentos de relevância revisados e corpus fixo.

Esta prova de conceito não promete escalabilidade ilimitada, isolamento multitenant ou anonimização automática. A recuperação semântica compara vetores localmente; o consumo de memória e o tempo de resposta dependem do acervo. As sínteses do agente também precisam de revisão e referência às fontes.

## Documentação

Consulte:

- [Instalação e operação técnica](.mcp/README.md).
- [Arquitetura da busca](.mcp/docs/SEARCH.md).
- [Fluxo de ingestão](.mcp/docs/INGESTION.md).
- [Contrato editorial](.mcp/INGEST.md).
- [Testes](.mcp/tests/README.md).

## Versão e licença

A primeira publicação deste histórico será identificada pela tag `2.0`, criada após revisão e testes. A versão apresenta a implementação existente com uma demonstração pública; não implica que os commits privados anteriores estejam disponíveis.

O código de origem utiliza a [licença MIT](LICENSE). A edição pública deve preservar os avisos de autoria aplicáveis. Modelos, dependências e textos de terceiros têm seus próprios termos; os pesos dos modelos são obtidos separadamente.
