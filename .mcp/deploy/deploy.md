# Operação avançada e voluntária

A demonstração local está no [README técnico](../README.md). Nenhum workflow público
executa deploy, SSH ou publicação. Não instale agendamento para experimentar o projeto.

## Publicador de ingestões

`scripts/sync_ingest.py publish --repo /caminho/vault` publica somente operações
concluídas e registradas. Requer uma instalação deliberada com Git, identidade e
remoto próprios. O repositório público do código não deve receber notas pessoais.
O executor mantém snapshots e recibos privados em `.mcp/.daedalus-sync/` ou em
`DAEDALUS_SYNC_DIR`. Fontes e destinos devem pertencer à instalação autorizada.
Conflitos e alterações alheias interrompem o envio; não use staging genérico.

`auto_backup.sh` é um wrapper desse publicador. `install_ingest_sync.py` modifica
crontab e é opcional; não é passo da instalação básica. Os testes simulam crontab
e usam remotos Git locais descartáveis para a publicação.

## Guard de atualização

`deploy.sh` e `sync_ingest.py deploy` são ferramentas avançadas preservadas com testes.
O guard exige a referência `ci/verified-main` no remoto da instalação, apontando ao
mesmo commit de `main`, além de checkout limpo. Ele coordena a publicação pendente,
a atualização fast-forward, o build e a recriação do container aguardando `/ready`.
Esta edição não fornece automação que produza essa referência. O comando não é uma
forma de iniciar a demonstração e não deve ser executado sem preparar uma instalação
independente e seu processo de verificação.

## Migração opcional

`scripts/migrate_hidden_layout.py` existe para instalações antigas independentes.
Uma instalação nova não precisa dele. O migrador reconhece o layout antigo com
container chamado `daedalus-mcp`; não se aplica ao novo Compose demonstrativo. Ele pode consultar Docker/crontab e mover
estado privado; não o execute durante a preparação pública. Os testes sintéticos
verificam colisões, symlinks, locks e preservação dos bytes, sem acessar outra instalação.
