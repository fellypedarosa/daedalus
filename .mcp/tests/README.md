# Testes do Daedalus

Os testes verificam o contrato MCP, a recuperação de conhecimento, a atualização do índice, o protocolo de deploy e a presença de possíveis credenciais. Testes de escrita usam bases sintéticas temporárias; não devem modificar as notas reais de `wiki/` ou `raw/`.

Os comandos abaixo partem da raiz do repositório. A varredura de credenciais continua cobrindo o repositório inteiro, inclusive wiki/raw e os caminhos privados antigos e novos.

## Execução

Use Python 3.12 e as dependências de `.mcp/requirements.lock` em um ambiente virtual:

```bash
XDG_STATE_HOME="$PWD/.mcp/tmp/test-state" \
  .mcp/.venv/bin/python -m unittest discover -s .mcp/tests -t .mcp -v
PYTHONPATH=.mcp .mcp/.venv/bin/python -m unittest tests.test_sensitive_data -v
```

O teste com encoder real exige um modelo previamente preparado:

```bash
DAEDALUS_TEST_MODEL_DIR=/caminho/modelos/e5-small \
  PYTHONPATH=.mcp .mcp/.venv/bin/python -m unittest tests.search.test_semantic.RealModelTests -v
```

Sem essa configuração, o teste opcional de modelo real é ignorado. Os testes sintéticos continuam verificando contratos, limites e cache, mas não comprovam qualidade semântica. Para verificar o ambiente do container:

```bash
docker build -f .mcp/Dockerfile --target test --tag daedalus-search-test .mcp
```

O target Docker executa `tests/search`, `tests/ingest` e o teste de descoberta do vault em `tests/test_layout.py`; a suíte completa também inclui a varredura de credenciais. Os workflows executam somente CI; não há deploy automático. Os julgamentos em `evaluation/` são exemplos sintéticos sobre `examples/vault`, sem validade de benchmark; detalhes em [SEARCH.md](../docs/SEARCH.md).

## Criação de notas brutas pelo .mcp

Os testes de criação remota (`tests/ingest/test_capture.py`, `test_mcp.py` e `test_git_sync.py`) usam apenas vaults sintéticos e remotos Git locais descartáveis. Cobrem as quatro categorias, preservação de UTF-8/CRLF, ausência de ingestão automática, colisões, repetição, arquivos catalogados, bloqueio de caminhos/symlinks, triagem de credenciais, autorização HTTP, retomada após interrupção e reconexão, publicação exclusiva da nota e ingestão posterior. Não enviam notas ao MCP de produção nem fazem push para o GitHub.

## Varredura de credenciais

`test_sensitive_data.py` examina arquivos versionados e arquivos novos não ignorados no diretório de trabalho. Não examina o histórico Git nem arquivos ignorados, e não verifica se uma credencial está ativa. Arquivos binários ficam fora da inspeção textual. A auditoria usa heurísticas e não garante a ausência de segredos.

Os checks incluem formatos de tokens, cabeçalhos de chaves privadas e atribuições suspeitas. A regra genérica `CREDENTIAL_ASSIGNMENT` exige valores de pelo menos oito caracteres; em código-fonte, examina atribuições literais. Há verificações adicionais de nomes de arquivos sensíveis e de arquivos privados que devem permanecer ignorados e não versionados.

Ao encontrar uma ocorrência, revisar arquivo, linha, valor e contexto com o responsável. Não apagar ou alterar notas para fazer o teste passar. Credenciais reais exigem uma decisão do responsável; a marcação de exceção serve somente para falsos positivos aprovados.

## Marcação de exceção para exemplos

Coloque um comentário imediatamente antes da linha que contém o exemplo aprovado:

```yaml
# daedalus-scan: allow CREDENTIAL_ASSIGNMENT value="senha_demonstrativa" reason="Exemplo didático aprovado"
POSTGRES_PASSWORD: senha_demonstrativa
```

Em Markdown fora de blocos de código, use um comentário HTML:

```markdown
<!-- daedalus-scan: allow CREDENTIAL_ASSIGNMENT value="senha_demonstrativa" reason="Exemplo didático aprovado" -->
POSTGRES_PASSWORD: senha_demonstrativa
```

A marcação não cria uma detecção: apenas permite uma correspondência que o detector já reconheceria.

A diretiva exige uma regra conhecida, o valor literal completo e um motivo não vazio. `value` e `reason` são strings JSON entre aspas duplas; escape aspas e barras invertidas conforme JSON. A grafia `daedalus-scan: allow` e os nomes das regras distinguem maiúsculas de minúsculas.

- Vale somente na linha imediatamente seguinte, inclusive dentro de blocos de código.
- Libera uma única correspondência com a regra e o valor exatos.
- Não libera outros valores, outras regras ou uma segunda ocorrência na mesma linha.
- Uma linha em branco ou outra linha intermediária encerra seu alcance.
- Não cria uma exceção para o arquivo inteiro nem permite versionar arquivos privados.
- Uma diretiva malformada gera `INVALID_ALLOW_MARKER` e não libera a linha seguinte.

As regras reconhecidas são `CREDENTIAL_ASSIGNMENT`, `PROVIDER_TOKEN`, `AWS_ACCESS_KEY_ID`, `DAEDALUS_TOKEN` e `PRIVATE_KEY`. Um mesmo trecho pode acionar mais de uma regra; a autorização de uma regra não elimina as demais detecções. Não há delimitador genérico como `%...%` nem bloco inteiro de exclusão.

Os testes do próprio detector verificam que a exceção não se propaga e que valores diferentes continuam sendo detectados. Uma marcação sem correspondência não falha por estar sem uso; ao mudar ou remover um exemplo, revise também seu comentário.

## Histórico e dados privados

Mover um arquivo versionado para `.mcp/tmp/` impede novos commits dessa cópia, mas não apaga versões anteriores do Git. A limpeza do histórico é uma operação separada: altera hashes de commits e tags e exige sincronizar os clones existentes. Não reintroduza o histórico antigo por merge ou push de uma cópia desatualizada.

## Ingestão

`tests/ingest/` verifica captura sem sobrescrita, caminhos e colisões, cobertura/evidências, preservação UTF-8/CRLF, proposta sem escrita, aprovação vinculada ao digest, interrupção antes/depois de cada publicação e retomada. Testa também bloqueio de indexação parcial, clientes com permissões distintas e fluxo completo por HTTP e STDIO em bases sintéticas. O detector de credenciais é compartilhado em `daedalus_validation/credentials.py`; as regras e as marcações permanecem as mesmas.

Os testes estruturais não certificam fidelidade de uma síntese produzida por LLM. Antes de produção, um piloto real escolhido pelo usuário precisa de revisão da proposta e autorização específica para aplicar e arquivar. Nenhum teste usa o acervo real para escrita.

`test_git_sync.py` usa um remoto bare local e clones independentes de computador/servidor. Verifica publicação restrita aos arquivos aprovados, índice/staging alheio, arquivos ignorados, múltiplas operações, conflito de fonte, push concorrente, rede indisponível, resposta de push perdida, retomada e bloqueio do deploy. Os testes de manutenção constroem um índice inicial durante o healthcheck para detectar deadlock. `test_sync_install.py` verifica o instalador de cron com comandos simulados, sem alterar o agendamento da máquina. Git real é necessário; a imagem de testes o instala apenas no target `test`.

## Reorganização em .mcp

`test_layout.py` copia apenas código para um repositório sintético e testa MCP STDIO e CLI a partir da raiz, de `.mcp/` e de um terceiro diretório, sem configurar DAEDALUS_VAULT_DIR. Confere também o INGEST.md e o destino padrão do log em `.mcp/`. Com Docker Compose disponível, valida .mcp/docker-compose.yml sem ambiente herdado, verificando mounts, contexto, nome do projeto e volumes. Os testes do cron verificam a conversão de entradas antigas/novas num único job; os testes Git executam .mcp/scripts/auto_backup.sh a partir de outro diretório e preservam o journal em `.mcp/.daedalus-sync/`.

Os testes de deploy exercitam .mcp/deploy/deploy.sh, verificando bloqueio de execuções simultâneas, propagação do código de saída e proteção contra comandos acrescentados durante a atualização do próprio script. A imagem de testes inclui somente o contexto `.mcp/` e executa os testes do script e do publicador em Python 3.12.

`test_hidden_layout.py` verifica inspeção sem movimentação, preservação de bytes/permissões, colisões, operações incompletas, links simbólicos e recusa de container/cron ativos. `test_git_sync.py` interrompe uma publicação antes do push, migra pedidos/recibos/blobs e comprova a retomada sem duplicar o commit. A pasta oculta da aplicação continua coberta pela varredura de credenciais.

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
