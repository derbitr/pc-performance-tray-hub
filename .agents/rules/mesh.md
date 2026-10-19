---
trigger: always_on
description: Protocolo da Cross-Project Mesh — este projeto faz parte de um ecossistema; consulte e avise os outros projetos.
---

# Protocolo da Malha Entre Projetos (cross-project-mesh)

Este workspace é o projeto **`pc-checkup`** (`E:/PC_checkup`) e faz parte de um ecossistema de projetos do mesmo
dono, conectados pelo servidor MCP **`cross-project-mesh`**. Siga este protocolo em toda sessão.

## 1. Início de sessão (obrigatório, antes da primeira resposta)

1. Chame `read_project_inbox("pc-checkup")`.
2. Se houver eventos pendentes, **apresente-os ao usuário primeiro**, em ordem de severidade
   (`critical` > `high` > `normal` > `low`), dizendo o projeto de origem e a ação pedida.
3. Para `breaking_change` e `contract_change`: leia o contrato novo no projeto de origem com
   `read_cross_project_code` antes de propor qualquer alteração aqui, e proponha a adaptação.
4. Só chame `ack_cross_project_event` (status `done`, com nota do que foi feito) **depois** que a adaptação estiver
   aplicada e verificada, ou `dismissed` se o usuário decidir ignorar. Nunca dê ack só por ter lido.

Se existir `.agents/rules/mesh-inbox.md`, ele é a mesma fila já injetada: trate-a do mesmo jeito.

## 2. Antes de criar algo novo: reaproveite

Antes de criar uma **Skill**, um **servidor/integração MCP**, um **parser/validador** ou um **schema**:

1. Chame `search_ecosystem("<palavras-chave>")`.
2. Se outro projeto já tem algo equivalente:
   - para usar uma vez: `borrow_skill_from_project(origem, skill, mode="read")` e aplique as instruções;
   - para usar sempre e acompanhar a evolução: `mode="link"` com `target_project="pc-checkup"`;
   - para divergir de propósito: `mode="copy"`.
   - para MCP: `inspect_project_mcp_config(origem, servidor)` e replique a configuração (sem copiar segredos).
3. Diga ao usuário o que foi reaproveitado e de onde. Só crie do zero se nada servir, e explique por quê.

## 3. Ao mudar algo que outro projeto consome: avise

Considere **contrato** qualquer coisa listada em `interfaces` do `project.mesh.json` ou consumida por um projeto em
`provides_to`: API HTTP, CLI (args, saída, exit codes), banco SQLite/JSON, formato de arquivo, pacote importável,
tools de MCP expostas, Skills emprestadas por link.

Quando uma mudança alterar um contrato:

1. Antes de editar, chame `get_project_deep_context("pc-checkup")` e veja `dependencies.provides_to`.
2. Para cada dependente, confira o lado consumidor com `read_cross_project_code` e diga ao usuário o impacto.
3. Depois de aplicar, chame
   `emit_cross_project_event("pc-checkup", "<dependente ou @dependents>", "breaking_change" | "contract_change", payload)`
   com `payload` contendo: `summary`, `files_changed`, `before`, `after` (exemplos reais de dados),
   `action_required` e, se houver, `migration`.
   - remoção/renomeação de campo, mudança de tipo, endpoint ou flag removidos → `breaking_change`, severidade `high`;
   - campo novo opcional, endpoint novo → `contract_change`, severidade `normal`.
4. Mudou `interfaces` ou dependências? Atualize o `project.mesh.json` deste projeto na mesma tarefa.

## 4. Governança

- Uma Skill útil em mais de um projeto deve ser proposta ao usuário para `promote_skill_to_global`.
- Nunca copie `.env`, chaves ou tokens entre projetos; `inspect_project_mcp_config` mostra só os nomes das variáveis.
- `read_cross_project_code` é somente leitura: nunca edite arquivos de outro projeto a partir daqui. Para pedir uma
  mudança lá, emita um evento `task`.
