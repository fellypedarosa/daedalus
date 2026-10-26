# Daedalus MCP — instalação técnica

O servidor usa Markdown como fonte da verdade. Busca lexical não requer modelo;
inferência ONNX é opcional e local. Obsidian não é requisito do MCP.
Veja a [apresentação pública](../README.md) e as [orientações técnicas](AGENTS.md).

## Dependências

Da raiz, com Python 3.12:

```bash
python3.12 -m venv .mcp/.venv
.mcp/.venv/bin/python -m pip install -r .mcp/requirements.lock
```

`requirements.txt` instala apenas o servidor lexical; `requirements-search.txt`
acrescenta inferência e preparação explícita de modelos. O lock reúne ambos.

## Demonstração STDIO

Da raiz, isole os derivados e logs mesmo nas consultas de leitura:

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

Configure essas variáveis também no cliente MCP. Ele inicia o processo STDIO;
chame `test`, `summary`, `search` e `read`. Perguntas respondíveis: “Qual o limiar
de umidade?”, “Como recuperar a configuração?” e “Por quanto tempo guardar registros?”.
O corpus é fictício, não uma recomendação de operação agrícola.

Para testar escrita, copie `examples/vault` para um novo diretório ignorado e aponte
o vault e os estados para essa cópia. Nunca aplique ingestão no exemplar versionado.
`create_raw_note` apenas captura. Apresente `ingest_preview` e obtenha aprovação
antes de `ingest_apply`; acompanhe busca e publicação separadamente. Sem publicador,
`publication` pode continuar pendente.

## Docker local

O Compose usa porta `127.0.0.1:8000`, volumes próprios do projeto e cópia descartável
do exemplo. Não monta Git, SSH ou pesos de outra instalação. Da raiz:

```bash
mkdir -p .mcp/tmp
cp -R examples/vault .mcp/tmp/demo-vault
cp .mcp/tokens.example.json .mcp/tokens.json
```

Edite o arquivo local `tokens.json` e substitua o placeholder por um token novo,
aleatório e exclusivo; ative somente a entrada escolhida com `"active": true`.
O template tem todas as entradas inativas e é rejeitado sem essa configuração. A instalação HTTP
recusa configuração ausente, inválida ou sem tokens ativos válidos. Não publique
esse arquivo. Para uso somente de leitura, mantenha apenas `daedalus:read`;
escrita requer `daedalus:ingest` explicitamente.

```bash
env -i "$(command -v docker)" compose --env-file /dev/null -f .mcp/docker-compose.yml config --quiet
docker compose -f .mcp/docker-compose.yml build
docker compose -f .mcp/docker-compose.yml up -d --wait
```

Esses comandos de inicialização destinam-se à instalação local deliberada do leitor;
a preparação do repositório não os executa. `/health` e `/ready` não expõem notas;
`/mcp` requer Bearer token. HTTPS é necessário para implantação remota.
Não remova volumes para corrigir falhas sem decidir antes sobre seus dados locais.

## Modelos e avaliação

Consulte [SEARCH.md](docs/SEARCH.md) para preparação explícita do encoder e arquitetura.
Sem modelo, o fallback é lexical. O dataset em `tests/evaluation/queries.json`
contém perguntas didáticas sobre `examples/vault`; seus julgamentos são sintéticos,
sem revisão independente e sem validade como benchmark representativo.

```bash
DAEDALUS_INGEST_DIR="$PWD/.mcp/tmp/cli-state/ingest" \
DAEDALUS_SYNC_DIR="$PWD/.mcp/tmp/cli-state/sync" \
.mcp/.venv/bin/python .mcp/scripts/evaluate_search.py \
  --vault examples/vault --backend lexical --split all \
  --index-dir .mcp/tmp/evaluation-index --output .mcp/tmp/evaluation.json
```

Relatórios e índices ficam ignorados. Testes com vetores sintéticos verificam
contratos; a qualidade semântica exige avaliação própria e encoder real.

## Testes e operação avançada

```bash
XDG_STATE_HOME="$PWD/.mcp/tmp/test-state" \
  .mcp/.venv/bin/python -m unittest discover -s .mcp/tests -t .mcp -v
docker build -f .mcp/Dockerfile --target test --tag daedalus-public-test .mcp
```

A suíte completa inclui credenciais e layout. O target Docker cobre busca, ingestão,
publicação sintética e descoberta do vault; a validação do Compose está em `tests/test_compose.py` e roda separadamente.
Veja [testes](tests/README.md), [busca](docs/SEARCH.md), [ingestão](docs/INGESTION.md)
e [contrato editorial](INGEST.md). O [publicador e guard de atualização](deploy/deploy.md)
são opcionais: a instalação básica não instala cron, executa deploy ou publica notas.

## Verificar ingestão do exemplo público

```bash
.mcp/.venv/bin/python .mcp/scripts/check_demo_ingestion.py
```

O comando copia o corpus fictício para um diretório descartável e verifica captura,
preview, aplicação, preservação de fonte, busca, repetição e publicação com Git em
remoto local temporário. Não altera o exemplar versionado nem usa remotos ou
credenciais pessoais. O relatório fica em `.mcp/tmp/demo-ingestion-check.json`.
A verificação chama a API de serviço diretamente; não é prova dos transportes MCP.
O CI executa esse comando a partir da raiz, onde `examples/vault` está disponível.
