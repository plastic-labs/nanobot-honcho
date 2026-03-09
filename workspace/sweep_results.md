# Dialectic Ablation Sweep Results

**Started:** 2026-03-06
**Status:** Running

## Configuration

- **Component:** Dialectic
- **Reasoning Level:** medium (fixed)
- **Temperature:** 0.0 (fixed, Deriver)
- **Evals:** LoCoMo, LongMemEval, BEAM

### Sweep Parameters

| Parameter | Values |
|-----------|--------|
| Models | claude-haiku-4-5, claude-sonnet-4-5, gemini-2.5-flash, qwen/qwen3.5-32b, gpt-4o-mini, gpt-4o |
| Thinking Budgets | 0, 512, 1024, 2048, 4096 |
| Tool Iterations | 1, 5, 10, 15, 20 |

**Total Configs:** 6 models × 5 budgets × 5 iterations = 150
**Total Runs:** 150 × 3 evals = 450

### Model → Provider Mapping

| Model | Provider | Model ID |
|-------|----------|----------|
| Claude Haiku 4.5 | anthropic | claude-haiku-4-5 |
| Claude Sonnet 4.5 | anthropic | claude-sonnet-4-5 |
| Gemini 2.5 Flash | google | gemini-2.5-flash |
| Qwen 3.5 35B | custom | qwen/qwen3.5-32b |
| GPT-4o-mini | openai | gpt-4o-mini |
| GPT-4o | openai | gpt-4o |

---

## Results

### LoCoMo

| Model | Provider | Thinking Budget | Tool Iterations | Accuracy | Cost (tokens) | Latency (s) | Status |
|-------|----------|-----------------|-----------------|----------|---------------|-------------|--------|

| claude-haiku-4-5 | anthropic | 0 | 1 | N/A | None | 0.7 | failed |
| claude-haiku-4-5 | anthropic | 0 | 5 | N/A | None | 0.6 | failed |
| claude-haiku-4-5 | anthropic | 0 | 10 | N/A | None | 0.6 | failed |
| claude-haiku-4-5 | anthropic | 0 | 15 | N/A | None | 0.6 | failed |
| claude-haiku-4-5 | anthropic | 0 | 20 | N/A | None | 0.7 | failed |
| claude-haiku-4-5 | anthropic | 512 | 1 | N/A | None | 0.6 | failed |
| claude-haiku-4-5 | anthropic | 512 | 5 | N/A | None | 0.6 | failed |
| claude-haiku-4-5 | anthropic | 512 | 10 | N/A | None | 0.6 | failed |
| claude-haiku-4-5 | anthropic | 512 | 15 | N/A | None | 0.6 | failed |
| claude-haiku-4-5 | anthropic | 512 | 20 | N/A | None | 0.6 | failed |
| claude-haiku-4-5 | anthropic | 1024 | 1 | N/A | None | 0.6 | failed |
| claude-haiku-4-5 | anthropic | 1024 | 5 | N/A | None | 0.6 | failed |
| claude-haiku-4-5 | anthropic | 1024 | 10 | N/A | None | 0.6 | failed |
| claude-haiku-4-5 | anthropic | 1024 | 15 | N/A | None | 0.7 | failed |
| claude-haiku-4-5 | anthropic | 1024 | 20 | N/A | None | 0.7 | failed |
| claude-haiku-4-5 | anthropic | 2048 | 1 | N/A | None | 0.7 | failed |
| claude-haiku-4-5 | anthropic | 2048 | 5 | N/A | None | 0.6 | failed |
| claude-haiku-4-5 | anthropic | 2048 | 10 | N/A | None | 0.7 | failed |
| claude-haiku-4-5 | anthropic | 2048 | 15 | N/A | None | 0.7 | failed |
| claude-haiku-4-5 | anthropic | 2048 | 20 | N/A | None | 0.7 | failed |
| claude-haiku-4-5 | anthropic | 4096 | 1 | N/A | None | 0.7 | failed |
| claude-haiku-4-5 | anthropic | 4096 | 5 | N/A | None | 0.6 | failed |
| claude-haiku-4-5 | anthropic | 4096 | 10 | N/A | None | 0.7 | failed |
| claude-haiku-4-5 | anthropic | 4096 | 15 | N/A | None | 0.7 | failed |
| claude-haiku-4-5 | anthropic | 4096 | 20 | N/A | None | 0.7 | failed |
| claude-sonnet-4-5 | anthropic | 0 | 1 | N/A | None | 0.6 | failed |
| claude-sonnet-4-5 | anthropic | 0 | 5 | N/A | None | 0.6 | failed |
| claude-sonnet-4-5 | anthropic | 0 | 10 | N/A | None | 0.6 | failed |
| claude-sonnet-4-5 | anthropic | 0 | 15 | N/A | None | 0.7 | failed |
| claude-sonnet-4-5 | anthropic | 0 | 20 | N/A | None | 0.6 | failed |
| claude-sonnet-4-5 | anthropic | 512 | 1 | N/A | None | 0.6 | failed |
| claude-sonnet-4-5 | anthropic | 512 | 5 | N/A | None | 0.6 | failed |
| claude-sonnet-4-5 | anthropic | 512 | 10 | N/A | None | 0.6 | failed |
| claude-sonnet-4-5 | anthropic | 512 | 15 | N/A | None | 0.6 | failed |
| claude-sonnet-4-5 | anthropic | 512 | 20 | N/A | None | 0.6 | failed |
| claude-sonnet-4-5 | anthropic | 1024 | 1 | N/A | None | 0.6 | failed |
| claude-sonnet-4-5 | anthropic | 1024 | 5 | N/A | None | 0.7 | failed |
| claude-sonnet-4-5 | anthropic | 1024 | 10 | N/A | None | 0.7 | failed |
| claude-sonnet-4-5 | anthropic | 1024 | 15 | N/A | None | 0.6 | failed |
| claude-sonnet-4-5 | anthropic | 1024 | 20 | N/A | None | 0.6 | failed |
| claude-sonnet-4-5 | anthropic | 2048 | 1 | N/A | None | 0.6 | failed |
| claude-sonnet-4-5 | anthropic | 2048 | 5 | N/A | None | 0.6 | failed |
| claude-sonnet-4-5 | anthropic | 2048 | 10 | N/A | None | 0.7 | failed |
| claude-sonnet-4-5 | anthropic | 2048 | 15 | N/A | None | 0.6 | failed |
| claude-sonnet-4-5 | anthropic | 2048 | 20 | N/A | None | 0.7 | failed |
| claude-sonnet-4-5 | anthropic | 4096 | 1 | N/A | None | 0.6 | failed |
| claude-sonnet-4-5 | anthropic | 4096 | 5 | N/A | None | 0.6 | failed |
| claude-sonnet-4-5 | anthropic | 4096 | 10 | N/A | None | 0.7 | failed |
| claude-sonnet-4-5 | anthropic | 4096 | 15 | N/A | None | 0.6 | failed |
| claude-sonnet-4-5 | anthropic | 4096 | 20 | N/A | None | 0.6 | failed |
| gemini-2.5-flash | google | 0 | 1 | N/A | None | 0.6 | failed |
| gemini-2.5-flash | google | 0 | 5 | N/A | None | 0.6 | failed |
| gemini-2.5-flash | google | 0 | 10 | N/A | None | 0.6 | failed |
| gemini-2.5-flash | google | 0 | 15 | N/A | None | 0.6 | failed |
| gemini-2.5-flash | google | 0 | 20 | N/A | None | 0.7 | failed |
| gemini-2.5-flash | google | 512 | 1 | N/A | None | 0.7 | failed |
| gemini-2.5-flash | google | 512 | 5 | N/A | None | 0.6 | failed |
| gemini-2.5-flash | google | 512 | 10 | N/A | None | 0.6 | failed |
| gemini-2.5-flash | google | 512 | 15 | N/A | None | 0.6 | failed |
| gemini-2.5-flash | google | 512 | 20 | N/A | None | 0.6 | failed |
| gemini-2.5-flash | google | 1024 | 1 | N/A | None | 0.6 | failed |
| gemini-2.5-flash | google | 1024 | 5 | N/A | None | 0.6 | failed |
| gemini-2.5-flash | google | 1024 | 10 | N/A | None | 0.6 | failed |
| gemini-2.5-flash | google | 1024 | 15 | N/A | None | 0.6 | failed |
| gemini-2.5-flash | google | 1024 | 20 | N/A | None | 0.6 | failed |
| gemini-2.5-flash | google | 2048 | 1 | N/A | None | 0.6 | failed |
| gemini-2.5-flash | google | 2048 | 5 | N/A | None | 0.6 | failed |
| gemini-2.5-flash | google | 2048 | 10 | N/A | None | 0.6 | failed |
| gemini-2.5-flash | google | 2048 | 15 | N/A | None | 0.6 | failed |
| gemini-2.5-flash | google | 2048 | 20 | N/A | None | 0.6 | failed |
| gemini-2.5-flash | google | 4096 | 1 | N/A | None | 0.7 | failed |
| gemini-2.5-flash | google | 4096 | 5 | N/A | None | 0.6 | failed |
| gemini-2.5-flash | google | 4096 | 10 | N/A | None | 0.7 | failed |
| gemini-2.5-flash | google | 4096 | 15 | N/A | None | 0.6 | failed |
| gemini-2.5-flash | google | 4096 | 20 | N/A | None | 0.6 | failed |
| qwen/qwen3.5-32b | custom | 0 | 1 | N/A | None | 0.7 | failed |
| qwen/qwen3.5-32b | custom | 0 | 5 | N/A | None | 0.7 | failed |
| qwen/qwen3.5-32b | custom | 0 | 10 | N/A | None | 0.6 | failed |
| qwen/qwen3.5-32b | custom | 0 | 15 | N/A | None | 0.6 | failed |
| qwen/qwen3.5-32b | custom | 0 | 20 | N/A | None | 0.6 | failed |
| qwen/qwen3.5-32b | custom | 512 | 1 | N/A | None | 0.6 | failed |
| qwen/qwen3.5-32b | custom | 512 | 5 | N/A | None | 0.7 | failed |
| qwen/qwen3.5-32b | custom | 512 | 10 | N/A | None | 0.6 | failed |
| qwen/qwen3.5-32b | custom | 512 | 15 | N/A | None | 0.7 | failed |
| qwen/qwen3.5-32b | custom | 512 | 20 | N/A | None | 0.7 | failed |
| qwen/qwen3.5-32b | custom | 1024 | 1 | N/A | None | 0.7 | failed |
| qwen/qwen3.5-32b | custom | 1024 | 5 | N/A | None | 0.6 | failed |
| qwen/qwen3.5-32b | custom | 1024 | 10 | N/A | None | 0.7 | failed |
| qwen/qwen3.5-32b | custom | 1024 | 15 | N/A | None | 0.7 | failed |
| qwen/qwen3.5-32b | custom | 1024 | 20 | N/A | None | 0.9 | failed |
| qwen/qwen3.5-32b | custom | 2048 | 1 | N/A | None | 1.0 | failed |
| qwen/qwen3.5-32b | custom | 2048 | 5 | N/A | None | 1.0 | failed |
| qwen/qwen3.5-32b | custom | 2048 | 10 | N/A | None | 0.8 | failed |
| qwen/qwen3.5-32b | custom | 2048 | 15 | N/A | None | 0.7 | failed |
| qwen/qwen3.5-32b | custom | 2048 | 20 | N/A | None | 0.8 | failed |
| qwen/qwen3.5-32b | custom | 4096 | 1 | N/A | None | 0.7 | failed |
| qwen/qwen3.5-32b | custom | 4096 | 5 | N/A | None | 0.6 | failed |
| qwen/qwen3.5-32b | custom | 4096 | 10 | N/A | None | 0.6 | failed |
| qwen/qwen3.5-32b | custom | 4096 | 15 | N/A | None | 0.7 | failed |
| qwen/qwen3.5-32b | custom | 4096 | 20 | N/A | None | 0.7 | failed |
| gpt-4o-mini | openai | 0 | 1 | N/A | None | 0.6 | failed |
| gpt-4o-mini | openai | 0 | 5 | N/A | None | 0.6 | failed |
| gpt-4o-mini | openai | 0 | 10 | N/A | None | 0.6 | failed |
| gpt-4o-mini | openai | 0 | 15 | N/A | None | 0.7 | failed |
| gpt-4o-mini | openai | 0 | 20 | N/A | None | 0.7 | failed |
| gpt-4o-mini | openai | 512 | 1 | N/A | None | 0.7 | failed |
| gpt-4o-mini | openai | 512 | 5 | N/A | None | 0.7 | failed |
| gpt-4o-mini | openai | 512 | 10 | N/A | None | 0.7 | failed |
| gpt-4o-mini | openai | 512 | 15 | N/A | None | 0.7 | failed |
| gpt-4o-mini | openai | 512 | 20 | N/A | None | 0.7 | failed |
| gpt-4o-mini | openai | 1024 | 1 | N/A | None | 0.7 | failed |
| gpt-4o-mini | openai | 1024 | 5 | N/A | None | 0.7 | failed |
| gpt-4o-mini | openai | 1024 | 10 | N/A | None | 0.7 | failed |
| gpt-4o-mini | openai | 1024 | 15 | N/A | None | 0.7 | failed |
| gpt-4o-mini | openai | 1024 | 20 | N/A | None | 0.7 | failed |
| gpt-4o-mini | openai | 2048 | 1 | N/A | None | 0.7 | failed |
| gpt-4o-mini | openai | 2048 | 5 | N/A | None | 0.7 | failed |
| gpt-4o-mini | openai | 2048 | 10 | N/A | None | 0.7 | failed |
| gpt-4o-mini | openai | 2048 | 15 | N/A | None | 0.6 | failed |
| gpt-4o-mini | openai | 2048 | 20 | N/A | None | 0.7 | failed |
| gpt-4o-mini | openai | 4096 | 1 | N/A | None | 0.6 | failed |
| gpt-4o-mini | openai | 4096 | 5 | N/A | None | 0.6 | failed |
| gpt-4o-mini | openai | 4096 | 10 | N/A | None | 0.7 | failed |
| gpt-4o-mini | openai | 4096 | 15 | N/A | None | 0.6 | failed |
| gpt-4o-mini | openai | 4096 | 20 | N/A | None | 0.7 | failed |
| gpt-4o | openai | 0 | 1 | N/A | None | 0.7 | failed |
| gpt-4o | openai | 0 | 5 | N/A | None | 0.7 | failed |
| gpt-4o | openai | 0 | 10 | N/A | None | 0.7 | failed |
| gpt-4o | openai | 0 | 15 | N/A | None | 0.7 | failed |
| gpt-4o | openai | 0 | 20 | N/A | None | 0.8 | failed |
| gpt-4o | openai | 512 | 1 | N/A | None | 0.8 | failed |
| gpt-4o | openai | 512 | 5 | N/A | None | 0.7 | failed |
| gpt-4o | openai | 512 | 10 | N/A | None | 0.7 | failed |
| gpt-4o | openai | 512 | 15 | N/A | None | 0.7 | failed |
| gpt-4o | openai | 512 | 20 | N/A | None | 0.7 | failed |
| gpt-4o | openai | 1024 | 1 | N/A | None | 0.7 | failed |
| gpt-4o | openai | 1024 | 5 | N/A | None | 0.7 | failed |
| gpt-4o | openai | 1024 | 10 | N/A | None | 0.6 | failed |
| gpt-4o | openai | 1024 | 15 | N/A | None | 0.6 | failed |
| gpt-4o | openai | 1024 | 20 | N/A | None | 0.7 | failed |
| gpt-4o | openai | 2048 | 1 | N/A | None | 0.6 | failed |
| gpt-4o | openai | 2048 | 5 | N/A | None | 0.7 | failed |
| gpt-4o | openai | 2048 | 10 | N/A | None | 0.7 | failed |
| gpt-4o | openai | 2048 | 15 | N/A | None | 0.7 | failed |
| gpt-4o | openai | 2048 | 20 | N/A | None | 0.7 | failed |
| gpt-4o | openai | 4096 | 1 | N/A | None | 0.7 | failed |
| gpt-4o | openai | 4096 | 5 | N/A | None | 0.7 | failed |
| gpt-4o | openai | 4096 | 10 | N/A | None | 0.8 | failed |
| gpt-4o | openai | 4096 | 15 | N/A | None | 0.7 | failed |
| gpt-4o | openai | 4096 | 20 | N/A | None | 0.7 | failed |
### LongMemEval

| Model | Provider | Thinking Budget | Tool Iterations | Accuracy | Cost (tokens) | Latency (s) | Status |
|-------|----------|-----------------|-----------------|----------|---------------|-------------|--------|

| claude-haiku-4-5 | anthropic | 0 | 1 | N/A | None | 0.7 | failed |
| claude-haiku-4-5 | anthropic | 0 | 5 | N/A | None | 0.6 | failed |
| claude-haiku-4-5 | anthropic | 0 | 10 | N/A | None | 0.6 | failed |
| claude-haiku-4-5 | anthropic | 0 | 15 | N/A | None | 0.7 | failed |
| claude-haiku-4-5 | anthropic | 0 | 20 | N/A | None | 0.6 | failed |
| claude-haiku-4-5 | anthropic | 512 | 1 | N/A | None | 0.6 | failed |
| claude-haiku-4-5 | anthropic | 512 | 5 | N/A | None | 0.6 | failed |
| claude-haiku-4-5 | anthropic | 512 | 10 | N/A | None | 0.7 | failed |
| claude-haiku-4-5 | anthropic | 512 | 15 | N/A | None | 0.7 | failed |
| claude-haiku-4-5 | anthropic | 512 | 20 | N/A | None | 0.6 | failed |
| claude-haiku-4-5 | anthropic | 1024 | 1 | N/A | None | 0.7 | failed |
| claude-haiku-4-5 | anthropic | 1024 | 5 | N/A | None | 0.7 | failed |
| claude-haiku-4-5 | anthropic | 1024 | 10 | N/A | None | 0.7 | failed |
| claude-haiku-4-5 | anthropic | 1024 | 15 | N/A | None | 0.7 | failed |
| claude-haiku-4-5 | anthropic | 1024 | 20 | N/A | None | 0.7 | failed |
| claude-haiku-4-5 | anthropic | 2048 | 1 | N/A | None | 0.7 | failed |
| claude-haiku-4-5 | anthropic | 2048 | 5 | N/A | None | 0.7 | failed |
| claude-haiku-4-5 | anthropic | 2048 | 10 | N/A | None | 0.6 | failed |
| claude-haiku-4-5 | anthropic | 2048 | 15 | N/A | None | 0.7 | failed |
| claude-haiku-4-5 | anthropic | 2048 | 20 | N/A | None | 0.6 | failed |
| claude-haiku-4-5 | anthropic | 4096 | 1 | N/A | None | 0.7 | failed |
| claude-haiku-4-5 | anthropic | 4096 | 5 | N/A | None | 0.7 | failed |
| claude-haiku-4-5 | anthropic | 4096 | 10 | N/A | None | 0.7 | failed |
| claude-haiku-4-5 | anthropic | 4096 | 15 | N/A | None | 0.9 | failed |
| claude-haiku-4-5 | anthropic | 4096 | 20 | N/A | None | 0.7 | failed |
| claude-sonnet-4-5 | anthropic | 0 | 1 | N/A | None | 0.7 | failed |
| claude-sonnet-4-5 | anthropic | 0 | 5 | N/A | None | 0.8 | failed |
| claude-sonnet-4-5 | anthropic | 0 | 10 | N/A | None | 0.7 | failed |
| claude-sonnet-4-5 | anthropic | 0 | 15 | N/A | None | 0.7 | failed |
| claude-sonnet-4-5 | anthropic | 0 | 20 | N/A | None | 0.7 | failed |
| claude-sonnet-4-5 | anthropic | 512 | 1 | N/A | None | 0.7 | failed |
| claude-sonnet-4-5 | anthropic | 512 | 5 | N/A | None | 0.7 | failed |
| claude-sonnet-4-5 | anthropic | 512 | 10 | N/A | None | 0.6 | failed |
| claude-sonnet-4-5 | anthropic | 512 | 15 | N/A | None | 0.7 | failed |
| claude-sonnet-4-5 | anthropic | 512 | 20 | N/A | None | 0.6 | failed |
| claude-sonnet-4-5 | anthropic | 1024 | 1 | N/A | None | 0.6 | failed |
| claude-sonnet-4-5 | anthropic | 1024 | 5 | N/A | None | 0.7 | failed |
| claude-sonnet-4-5 | anthropic | 1024 | 10 | N/A | None | 0.6 | failed |
| claude-sonnet-4-5 | anthropic | 1024 | 15 | N/A | None | 0.6 | failed |
| claude-sonnet-4-5 | anthropic | 1024 | 20 | N/A | None | 0.6 | failed |
| claude-sonnet-4-5 | anthropic | 2048 | 1 | N/A | None | 0.6 | failed |
| claude-sonnet-4-5 | anthropic | 2048 | 5 | N/A | None | 0.6 | failed |
| claude-sonnet-4-5 | anthropic | 2048 | 10 | N/A | None | 0.6 | failed |
| claude-sonnet-4-5 | anthropic | 2048 | 15 | N/A | None | 0.6 | failed |
| claude-sonnet-4-5 | anthropic | 2048 | 20 | N/A | None | 0.6 | failed |
| claude-sonnet-4-5 | anthropic | 4096 | 1 | N/A | None | 0.6 | failed |
| claude-sonnet-4-5 | anthropic | 4096 | 5 | N/A | None | 0.7 | failed |
| claude-sonnet-4-5 | anthropic | 4096 | 10 | N/A | None | 0.7 | failed |
| claude-sonnet-4-5 | anthropic | 4096 | 15 | N/A | None | 0.7 | failed |
| claude-sonnet-4-5 | anthropic | 4096 | 20 | N/A | None | 0.7 | failed |
| gemini-2.5-flash | google | 0 | 1 | N/A | None | 0.7 | failed |
| gemini-2.5-flash | google | 0 | 5 | N/A | None | 0.7 | failed |
| gemini-2.5-flash | google | 0 | 10 | N/A | None | 0.7 | failed |
| gemini-2.5-flash | google | 0 | 15 | N/A | None | 0.7 | failed |
| gemini-2.5-flash | google | 0 | 20 | N/A | None | 0.7 | failed |
| gemini-2.5-flash | google | 512 | 1 | N/A | None | 0.7 | failed |
| gemini-2.5-flash | google | 512 | 5 | N/A | None | 0.7 | failed |
| gemini-2.5-flash | google | 512 | 10 | N/A | None | 0.7 | failed |
| gemini-2.5-flash | google | 512 | 15 | N/A | None | 0.7 | failed |
| gemini-2.5-flash | google | 512 | 20 | N/A | None | 0.7 | failed |
| gemini-2.5-flash | google | 1024 | 1 | N/A | None | 0.7 | failed |
### BEAM

| Model | Provider | Thinking Budget | Tool Iterations | Accuracy | Cost (tokens) | Latency (s) | Status |
|-------|----------|-----------------|-----------------|----------|---------------|-------------|--------|

---

## Notes

- Sweep initiated by nanobot on 2026-03-06
- Running sequentially to avoid rate limits
- Results will be appended as runs complete

