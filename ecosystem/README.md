# GPTDoug Ecosystem Swarm

This layer connects Dream-RSI's exploration-policy loop to the Sonoxo ecosystem through explicit repository adapters instead of copying repositories into one monolith.

## Stack

- **Dream-RSI** (`sonoxo/GPT-DOUG-Dream-RSI`) — meta-exploration, history replay, policy improvement.
- **Zyra** (`sonoxo/zyra`) — governed ontology/runtime integration target.
- **XUNIA** — federation rooted in `sonoxo/xuniahub`, with geospatial/simulation components including `gods-eye-viewXUNIA`, `AIT-CoreXUNIA`, `plandevXUNIA-`, and `MMGISxunia-`.
- **BlackHouse** — adapter slot configured with `BLACKHOUSE_REPO`. No repository literally named `blackhouse` was present in the connected Sonoxo repository listing when this integration was created, so this target is intentionally not guessed.

## ForeverRuleGPTDOUGLLMMAXMIMIXK

The swarm scales parallel candidate exploration up to `GPTDOUG_MAX_PARALLEL_AGENTS`, subject to runtime capacity. Each generation uses explorer, architect, integrator, evaluator, critic, and security-review roles. Candidate changes remain proposals until tests/evaluation and review gates pass.

## Flow

```text
objective
  -> repository context
  -> parallel candidate branches
  -> evaluators
  -> scored + diverse survivors
  -> lineage/history store
  -> Dream-RSI replay
  -> improved exploration policy
  -> next generation
```

## Environment

```bash
export GPTDOUG_MAX_PARALLEL_AGENTS=32
export BLACKHOUSE_REPO=sonoxo/<actual-blackhouse-repository>
```

The manifest deliberately does not store credentials. Repository/provider tokens belong in the runtime secret store or environment.

## Integration contract

All systems communicate through `event.schema.json`. An adapter declares its repository and capabilities using `adapter.schema.json`. Cross-repository writes are disabled by default; a swarm worker may inspect context, produce candidate patches, and evaluate them, while promotion is handled through an explicit reviewed branch/PR workflow.

## Next implementation stage

Implement runtime adapters for each configured repository, a persistent lineage/event store, sandboxed candidate evaluation, concurrency control, and evaluator plugins. When the exact BlackHouse repository is identified, set `BLACKHOUSE_REPO` and add its adapter without changing the core orchestration contract.
