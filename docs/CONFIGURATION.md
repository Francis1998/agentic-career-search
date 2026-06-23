# Configuration (Extended Notes)

Primary configuration reference: [CONFIGURATION.md](../CONFIGURATION.md).

This page captures deployment-specific guidance that complements the root variable table.

## Provider selection matrix

| `LLM_PROVIDER` | Required keys | API style |
|---|---|---|
| `gemini` | `GEMINI_API_KEY`, optional `GEMINI_MODEL` | Google Generative Language REST |
| `kimi` | `KIMI_API_KEY`, optional `KIMI_MODEL`, `KIMI_BASE_URL` | OpenAI-compatible chat completions |
| `claude` | `CLAUDE_API_KEY`, optional `CLAUDE_MODEL` | Anthropic Messages API |
| `gpt` | `OPENAI_API_KEY`, optional `OPENAI_MODEL`, `OPENAI_BASE_URL` | OpenAI-compatible chat completions |

## GPT-compatible endpoints

`gpt` uses the OpenAI chat completions shape. Point `OPENAI_BASE_URL` at compatible gateways when needed:

```env
LLM_ENABLE_ENRICHMENT=true
LLM_PROVIDER=gpt
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-5.5
OPENAI_BASE_URL=https://api.openai.com/v1
```

## Safety-oriented defaults

- Keep `MAX_JOBS_PER_SOURCE` bounded in shared environments.
- Leave enrichment disabled in CI (`LLM_ENABLE_ENRICHMENT=false`) for deterministic tests.
- Use explicit `HTTP_USER_AGENT` values for attribution in logs and upstream monitoring.

## See also

- [DEPLOYMENT.md](./DEPLOYMENT.md)
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
