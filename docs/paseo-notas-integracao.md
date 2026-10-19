# Notas de integração — Paseo / Antigravity (Fase 1)

Este documento consolida as notas de integração do sistema **Paseo** (repo `getpaseo/paseo`; CLI `@getpaseo/cli@0.11.4`) com o provider **Antigravity** (`agy`, modo full-access) como orquestrador e o provider custom **opencode-free** (modelos free do OpenCode zen) para subagentes. Fonte única das notas: `.swarm/context.md` (estado em 2026-10-19, pós reset-session). Notas brutas adicionais: `.swarm/integration-notes-paseo.md`.

## Paseo — schema do config

- O config do Paseo viverá em `C:\Users\Breno\.paseo\config.json` (a ser criado na Fase 2; backup `.bak` antes de qualquer edição).
- Estrutura prevista:
  - `daemon.mcp` — habilitado, incluindo `injectIntoAgents`: as MCP tools são injetadas nos agents que suportam isso.
  - `providers`:
    - `opencode-free` — provider custom que estende o provider `opencode` + a lista de modelos free (ver seção "Provider opencode-free");
    - `antigravity` — provider baseado no CLI `agy`.

## Provider antigravity — mecânica

Contrato do provider (código real em `plugins/antigravity-provider`):

- Sessão é spawns de:
  ```
  agy --input-format stream-json --output-format stream-json --add-dir <cwd> --disable-slash-commands --dangerously-skip-permissions [--model X] [--conversation ID]
  ```
- `command: ["agy"]` — resolvido por PATH no daemon; `--version` e `models` usam timeout de 10 s.
- Modo único: `full-access`. O effort é embutido no ID do modelo.

Catálogo e versão:

- Catálogo de modelos via `agy models` (formato TSV `id<TAB>label`; o aviso "Fetching available models..." vai para STDERR — requisito do parser do Paseo).
- Versão via `agy --version` (semver compatível com o Paseo: `>= 1.1.15`; atualmente reporta `1.4.2`).

Binário real vs. shim quebrado:

- O binário real instalado é `C:\Users\Breno\AppData\Local\agy\bin\agy.exe`.
- O `agy` no PATH é um alias legado **quebrado** (`C:\Users\Breno\AppData\Roaming\npm\agy.cmd` → `Antigravity\bin\agy-node.cmd` → `ELECTRON_RUN_AS_NODE=1` + `Antigravity.exe %*` sem script → Electron entra em REPL sem entrypoint; causa do hang/"Acesso negado").
- A resolução desse caminho precisa ser corrigida no daemon do Paseo (PATH/ordem ou correção do `agy.cmd`, com backup `.bak`). Lição: nunca diagnosticar o CLI pelo `agy` do PATH — usar sempre o caminho absoluto.
- Ordem: resolver/clarificar o `agy` ANTES do smoke E2E do Paseo.

MCP e orquestração:

- O Paseo **NÃO** injeta MCP tools no Antigravity → a orquestração do lead agy se dá via CLI `paseo run`.
- Skills `/paseo` instaladas nos dois ecossistemas (OpenCode e agy, incl. `~/.gemini/config/skills`).

## Descobertas REA (read-only)

- Análise read-only de `Antigravity.exe` via ferramentas REA:
  - `app.asar` (sha `bd10a005…`): análise retida (`ev_93757cabf981…`), extração feita (`ev_cb24805c…`; grafo com 1219 nós / 1248 edges).
  - Fuses do Electron inspecionados.
  - Bundle exportado em `E:\Temp\opencode\rea-evidence` (203 MB).
  - REA capture de processos: indisponível no Windows.

## agy-customizations

Customizações globais do agy (doc `agy-customizations`):

- Skills globais: `C:\Users\Breno\.gemini\config\skills\`
- Plugins: `C:\Users\Breno\.gemini\config\plugins\`
- MCP: `C:\Users\Breno\.gemini\config\mcp_config.json`
- A skill `/paseo` pode ser instalada globalmente em `~/.gemini/config/` e também para o OpenCode.

## Provider opencode-free

- Provider custom do Paseo backed pelos **10 modelos free** do catálogo zen do OpenCode (todos $0).
- A lista curada, IDs exatos e a validação de chamada vivem em [modelos-free-opencode.md](modelos-free-opencode.md).
- **OpenRouter NÃO está configurado** no OpenCode (extensão opcional futura; caso habilitado, a chave será referenciada apenas por NOME, nunca por valor).

## Autorização e regras do projeto

- **AUTORIZAÇÃO**: o usuário Breno concedeu permissão total explícita para instalar e configurar o sistema Paseo nesta máquina (npm global install, criação de `C:\Users\Breno\.paseo\config.json`, instalação de skills em `~/.config/opencode` e `~/.gemini/config`, configuração de MCP no cross-subagent).
- **REGRA 1 — SEGREDOS**: valores de chaves/tokens/credenciais NUNCA devem ser gravados, impressos ou ecoados em arquivos do projeto, logs, evidências, contexto ou guia. Referência sempre por NOME (ex.: `OPENROUTER_API_KEY`). Valores podem ser copiados de fontes locais para configs, sem exibição.
- **REGRA 2 — GUARDRAIL DE ESCRITA**: se um guardrail bloquear escrita fora do workspace (`E:\PC_checkup`), PARAR a operação e reportar ao usuário para concessão explícita. Proibido contorno: wrapper de shell, eval, heredoc, interpreter `-c`/`-e`, mv/rename como bypass.
- **REGRA 3 — ROLLBACK**: toda operação de máquina deve ter rollback documentado; arquivos existentes recebem backup (`.bak`) antes de edição (e comandos de desinstalação para instalações).
- **REGRA 4 — ESCOPO**: `files_touched` do plano aceita apenas caminhos relativos ao projeto (absolutos são rejeitados — `PLAN_TASK_SCOPE_INVALID`). Alvos de escrita de máquina são declarados no TEXTO das tarefas.

## Declaração

Este documento **não contém segredos, chaves de API nem tokens** — apenas referências por nome.
