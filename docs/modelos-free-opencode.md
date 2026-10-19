# Modelos free — pool do provider opencode-free (Paseo)

Este documento lista os modelos gratuitos (free tier) disponíveis no catálogo do OpenCode que compõem o pool de workers do provider customizado **opencode-free** usado pelo Paseo para subagentes. Apenas modelos marcados como "free" no catálogo oficial (`opencode models` / `opencode zen free`) são incluídos aqui.

## Catálogo curado (10 modelos)

| Ordem | ID exato | Rótulo curto |
|-------|----------|--------------|
| 1 | opencode/nemotron-3.5-super-vl-free | Nemotron 3.5 Super VL |
| 2 | opencode/beam-free | Beam |
| 3 | opencode/longcat-2.5-preview-free | LongCat 2.5 Preview |
| 4 | opencode/space-bunny-free | Space Bunny |
| 5 | opencode/mimo-v2.6-flash-free | Mimo v2.6 Flash |
| 6 | opencode/deepseek-v4.1-flash-free | DeepSeek v4.1 Flash |
| 7 | opencode/glm-5.3-flash-free | GLM 5.3 Flash |
| 8 | opencode/nemotron-3.5-lightning-free | Nemotron 3.5 Lightning |
| 9 | opencode/nemotron-3-ultra-free | Nemotron 3 Ultra |
| 10 | opencode/big-pickle | Big Pickle |

## Validação (2026-10-19)

```bash
opencode run -m opencode/deepseek-v4.1-flash-free "Responda apenas: OK"
```
→ respondeu `OK`.

Pelo menos um modelo free (DeepSeek v4.1 Flash) respondeu corretamente a uma chamada mínima.

## Observações

- O catálogo `zen` do OpenCode contém **41 modelos no total**; os **10 listados acima** correspondem exclusivamente ao *free tier*.
- **OpenRouter NÃO está configurado** nesta instalação do OpenCode — trata-se de uma extensão opcional futura. Caso venha a ser habilitado, a chave será referenciada **apenas pelo NOME** (ex.: `OPENROUTER_API_KEY`), nunca pelo valor, em arquivos, logs, evidências ou guias.
- Este documento **não contém segredos, chaves de API nem tokens**.