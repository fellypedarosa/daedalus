# Operação da ingestão

O contrato editorial, o template e o formato das propostas estão em [INGEST.md](../INGEST.md). O cliente LLM sintetiza e solicita autorização; o servidor valida, aplica e enfileira a publicação. O processo MCP não executa Git, SSH nem outro modelo de IA. Um executor no host publica os arquivos aprovados.

## Preparar a demonstração

1. Instale conforme o [README técnico](../README.md), sem cron ou publicador.
2. Copie `examples/vault` para um diretório novo em `.mcp/tmp/` e aponte o vault e todos os estados para essa cópia.
3. Para HTTP, use token local exclusivo. Escrita requer `daedalus:ingest`; tokens sem `scopes` não recebem escrita automaticamente.
4. Revise o preview antes de autorizar aplicação. Preserve as fontes e acompanhe busca e publicação separadamente.

Nenhuma nova variável é obrigatória no `.env`. A imagem define `DAEDALUS_INGEST_DIR=/var/lib/daedalus-ingest`; o Compose monta o volume nomeado nesse caminho. Em execução Python local, o padrão é uma pasta por vault sob `$XDG_STATE_HOME/daedalus-ingest` ou `~/.local/state/daedalus-ingest`, fora do checkout/Dropbox. Uma configuração explícita não pode apontar para wiki ou raw.

## Criar a fonte remotamente, sem ingerir

Use `create_raw_note(category, filename, content)` com categoria `ai`, `clipper`, `youtube` ou `local`. O cliente lê um arquivo local ou redige o texto solicitado e transmite seu conteúdo integral; um caminho local sozinho não envia o arquivo. A ferramenta aceita somente nomes `.md` sem subdiretórios e até 2 MB de texto UTF-8, preservando os bytes UTF-8 do texto recebido. Ao copiar, o cliente deve preservar também as quebras de linha; uma leitura local que normalize CRLF já altera o conteúdo antes do envio.

O comando cria exclusivamente a fonte, sem síntese, arquivamento, tracker ou log da wiki. Mesmo nome/conteúdo é reutilizado; conteúdo diferente é recusado. Uma fonte já catalogada não é recriada. Os bloqueios de deploy, de operação incompleta e as verificações de credenciais também valem para criação. Possíveis credenciais exigem triagem do usuário, sem reescrever a nota nem adicionar exceções automaticamente.

Novas criações entram no mesmo executor de publicação, com um pedido que contém apenas o novo arquivo e seu checksum. Não há publicação retroativa de notas preexistentes. A resposta `saved` confirma o arquivo no servidor, `ingestion_requested=false` confirma que esta operação não fez ingestão, e `publication` informa separadamente o envio ao Git. `operation_id` permite consultar `ingest_status`, respeitando o proprietário da operação. Para criações, esse status descreve a criação original, sem certificar o estado de uma ingestão posterior. Na reutilização de uma nota preexistente sem operação deste cliente, o id é nulo e a publicação é `not_requested`.

Repita exatamente a mesma chamada após falha ou perda de resposta. A operação preserva uma intenção antes da escrita, cria o arquivo atomicamente e retoma a fila sem duplicação. Uma operação interrompida bloqueia outras escritas até a retomada. A criação não depende de inicializar o índice de busca; a indexação segue o mecanismo normal de atualização. Só inicie `ingest_prepare` quando o usuário pedir ingestão.

`save_raw_ai_memory(title, content)` permanece compatível: transforma o título no nome legado em `raw/ai`, usa a mesma criação/publicação e retorna texto com o id da operação e o estado de publicação.

## Fluxo de uma fonte

- Colocar o Markdown em uma categoria autorizada de `raw/`. `raw/local/` é apropriado para notas copiadas manualmente; subpastas são aceitas. Assets, symlinks e fontes catalogadas não entram na lista de pendências.
- Usar um `request_id` estável em `ingest_prepare`. Repetir o pedido lê outras páginas ou prepara alvos sem criar outra operação. Conteúdo alterado exige nova preparação/revisão.
- `ingest_preview` devolve diff de notas, índice wiki, tracker, log e movimento aprovado. Ele invalida qualquer digest anterior, inclusive quando a nova proposta é inválida.
- Depois da aprovação, `ingest_apply` usa o digest exato. Novos nós são publicados sem sobrescrita; expansões inserem bytes sem reformatar o texto anterior.
- O arquivamento vem por último e preserva o conteúdo original. Referências canônicas anteriores continuam resolvendo para `cataloged/`, inclusive para fontes em subpastas.
- `ingest_status` diferencia aplicação e busca. Uma fonte adiada permanece no raw e não é declarada arquivada.
- A aplicação registra uma solicitação durável de publicação, inclusive os bytes exatos e as movimentações aprovadas. A revisão deve informar que o executor configurado publicará esse conjunto. O agente acompanha `publication`; não precisa chamar uma função de salvar nem executar Git.

O MVP aceita uma fonte por operação (até 2 MB), até 20 alterações e uma proposta JSON de até 500 KB. Evidências usam linhas da fonte; paginação usa caracteres Unicode; inserções usam offsets em bytes UTF-8 do snapshot original. A preparação informa tamanho em bytes e hash dos alvos. A existência de um trecho citado não comprova sua suficiência semântica.

## Estados e recuperação

| Estado | Ação |
| --- | --- |
| `prepared` | Ler fonte/alvos e produzir proposta. Nenhuma nota foi aplicada. |
| `validated` | Revisar diff e obter aprovação. Alterações externas impedem aplicação. |
| `applying` / `failed_recoverable` | Conferir a causa e retomar com o mesmo `operation_id` e digest. |
| `conflict` | Preservar a edição externa; pedir decisão ao responsável. Não restaurar snapshots automaticamente. |
| `committed` | Notas e registros foram aplicados; não aplicar uma operação nova para repetir a indexação. |
| `search_pending` | Aguardar/tentar atualizar a busca; as notas não precisam ser reescritas. |
| `search_ready` | A geração consultável contém os hashes esperados das notas e da fonte. |

As operações pertencem ao cliente identificado pelo token; outro cliente não pode aplicá-las ou ler seu estado privado. O digest vincula os bytes revisados, mas não é uma assinatura de aprovação humana. O aplicativo e o agente precisam obter a confirmação do usuário.

O diário e os resultados preparados persistem em `daedalus-ingest`, por vault. Ao iniciar a escrita, um marcador durável impede outras escritas/indexações até a conclusão ou retomada. A busca preserva a última geração publicada. Se o índice descartável for perdido, a recuperação da ingestão continua disponível sem depender de iniciá-lo.

Uma operação envolve vários arquivos e não é uma transação global atômica. Leituras diretas podem observar etapas gravadas; a ferramenta `read` sinaliza operação incompleta. Uma interrupção depois da publicação de um arquivo é reconhecida pelo hash esperado e não duplica a inserção. Se o usuário alterou o arquivo durante a interrupção, a operação para em conflito. O estado não deve ser apagado para contornar o bloqueio; a recuperação precisa preservar o trabalho posterior.

O volume de ingestão não é um cache: preserve-o junto ao backup das notas. Não use `docker compose down -v` para atualizar o serviço. Propostas privadas e snapshots do diário não pertencem ao Git nem ao corpus de busca.

## Uso local e servidor

A operação afeta o vault da instância que recebeu a chamada. No MCP remoto, as notas ficam no servidor; a publicação automática depende do executor instalado no host. Para recebê-las no Obsidian local, fazer pull depois de `publication.state=published`. Um computador desatualizado pode precisar integrar as alterações do servidor antes de conseguir publicar novas notas.

Os helpers antigos mantêm nomes e retorno textual, com validações mais estritas. `auto_catalog_ai_memory` exige nós existentes que realmente citem a fonte; listas vazias ou declarações sem suporte não finalizam a ingestão. Novos clientes devem usar preview/apply/status para revisar o conjunto inteiro antes da escrita.

## Publicação opcional

O Compose público persiste pedidos e recibos no volume isolado `sync-state`,
montado em `/var/lib/daedalus-sync`. Não há publicador ativo na demonstração;
a publicação pode continuar pendente sem impedir gravação e indexação.
Em Python local, configure `DAEDALUS_SYNC_DIR` na área temporária ignorada.
Pedidos, recibos e snapshots contêm notas e devem ser preservados como estado privado.

Para uma instalação independente que precise publicar notas em seu próprio remoto,
consulte a [operação avançada](../deploy/deploy.md). Ela requer autorização e
configuração deliberadas. Não conecte o executor ao repositório público do código.
Operações anteriores à fila não ganham autorização retroativa pela repetição de apply.

O processo usa a mesma coordenação da ingestão/deploy. Valida checksums e a continuidade entre operações, prepara commits com índice Git temporário e atualiza somente os caminhos aprovados no índice real. Staging alheio e commits locais desconhecidos não entram na publicação. Arquivos ignorados exigem revisão, sem adição forçada. Alvos legados/já cobertos precisam estar versionados na forma revisada antes de publicar o arquivamento.

Cada operação tem um ponto de recuperação em `refs/daedalus/ingest/<operation_id>` no Git do servidor. Uma interrupção depois do commit é retomada pelo mesmo ponto. Se o push ocorreu mas a resposta/recibo se perdeu, a presença do commit no histórico remoto confirma o envio sem criar outro commit.

| `publication.state` | Significado |
| --- | --- |
| `not_requested` | Operação antiga/ainda não aplicada, sem pedido de publicação. |
| `applying` | Pedido preservado; a aplicação das notas ainda precisa terminar/ser retomada. |
| `pending` | Arquivos preservados; aguardando executor ou nova tentativa de rede. Pode já ter `commit`. |
| `saved` | Commit local preservado; envio ainda não confirmado. |
| `published` | Commit alcançável no remoto Git configurado, indicado por `published_commit`. |
| `conflict` | Mudanças externas ou divergência de conteúdo exigem revisão; cópias permanecem preservadas. |

## Push concorrente e proteção do deploy

Se o computador publicou alterações compatíveis de código, o publicador combina os históricos numa cópia temporária, faz push normal e deixa os arquivos em uso intactos. Se uma nota/fonte ou uma dependência revisada mudou no outro lado, a integração para; nenhum marcador de conflito é escrito na wiki. São feitas no máximo três tentativas de push por execução, sem force push, reset ou clean.

Para resolver um conflito, revise o commit preservado e a versão remota numa cópia de revisão. Com autorização do responsável, pode publicar aquele commit numa branch de revisão e integrar as versões. Não reescreva o resultado da operação ou seus recibos para fazê-la passar. Depois que a main contiver o commit preservado, uma nova tentativa reconhece a publicação por ancestralidade.

O guard avançado de atualização bloqueia novas escritas durante a recriação e
permite a construção do índice e `/ready`. Exige um processo externo que mantenha
a referência de verificação; o CI desta edição não a produz nem executa deploy.
Veja o [contrato dessa operação](../deploy/deploy.md#guard-de-atualização).
O índice é reconstruível; diários, pedidos, recibos e commits preservados não são.
