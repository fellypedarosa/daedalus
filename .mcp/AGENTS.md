# Orientações técnicas do Daedalus 2.0

Siga as instruções locais e as autorizações da conversa. Apresente mudanças para
aprovação antes de editar; commit e publicação exigem pedido explícito.
A aplicação fica em `.mcp/`; a raiz do Git permanece no diretório pai.

## Ambiente e dados

- Não use servidores, clientes MCP globais, tokens ou volumes de outras instalações.
- Defina `DAEDALUS_VAULT_DIR` explicitamente. Leituras demonstrativas usam `examples/vault`; escritas usam uma cópia em `.mcp/tmp/`.
- Isole também `DAEDALUS_INDEX_DIR`, `DAEDALUS_INGEST_DIR`, `DAEDALUS_SYNC_DIR`, `DAEDALUS_AUDIT_LOG` e `DAEDALUS_TEST_AUDIT_LOG`.
- Registre inventários e ocorrências sensíveis apenas em `tmp/`, ignorada. Nunca reproduza segredos em relatórios públicos.
- Modelos são preparados por download explícito; busca lexical funciona sem pesos.

## Contrato MCP

O servidor não requer Obsidian; a CLI auxiliar tem contrato próprio.
Antes de afirmar que um processo MCP funciona, chame `test()` nesse processo e apresente o retorno.
Consulte `summary`, `search` e `read` para obter evidências, conferindo caminhos e passagens.
Não trate scores como probabilidades de verdade.

Captura com `create_raw_note` não solicita ingestão. Para sínteses, siga
`ingest_sources → ingest_prepare → search/read → ingest_preview`, leia todas as
páginas da fonte e apresente o diff. Aplique somente após aprovação humana;
o digest verifica integridade, não consentimento. Siga [INGEST.md](INGEST.md).
Inclua `Autor: [[LLM]]` nas notas criadas por agente e preserve fontes e conteúdo anterior.

Gravação, indexação e publicação são estados distintos. Sem publicador configurado,
a publicação pode ficar pendente. A demonstração não instala cron nem executa deploy.
HTTP exige autenticação válida; escrita exige `daedalus:ingest`.

## Verificação

Execute a suíte descrita no [README técnico](README.md). Testes de escrita usam
bases sintéticas e remotos Git locais descartáveis. Nunca edite notas reais para
fazer um teste passar. Preserve cobertura de autenticação, recuperação e conflitos.
Revise exceções do scanner: apenas exemplos sintéticos justificados podem permanecer.
O detector de credenciais não comprova anonimização nem inspeciona histórico/binários.
