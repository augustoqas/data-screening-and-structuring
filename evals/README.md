# Golden set

A fixed, hand-labelled dataset of realistic customer messages. It is the yardstick for the eval harness: the runner feeds every `message` through the pipeline and compares the result against `expected`, so a prompt or model change can be judged by numbers instead of impressions.

- **File:** [`golden_set.jsonl`](golden_set.jsonl), one JSON object per line. Blank lines and lines starting with `#` are section comments.
- **Loader and schema:** [`src/triage/eval/dataset.py`](../src/triage/eval/dataset.py).
- **Meaning of every field value:** the [taxonomy](../docs/taxonomy.md).

## Case format

```json
{
  "id": "012",
  "message": "comprei um fone dia 10, pedido 48213, chegou quebrado e quero meu dinheiro de volta URGENTE",
  "tags": ["ambiguous"],
  "expected": {
    "category": "damaged_or_defective",
    "requested_action": "refund",
    "priority": "high",
    "sentiment": "angry",
    "order_ids": ["48213"],
    "products": ["fone"],
    "amounts_brl": []
  },
  "notes": "Customer writes URGENTE, but a damaged item is high, not urgent..."
}
```

`expected` holds only the fields that can be judged objectively. `summary` and `priority_reason` are free text, with no single correct answer, so they are not labelled and not scored.

## Tags

Each case is tagged by the kind of challenge it represents, so results can be sliced ("how does the model do on injection attempts?"). A case can have several tags.

| Tag | What it tests |
|---|---|
| `simple` | A single, clearly stated problem |
| `ambiguous` | Category, priority or sentiment is a real judgement call |
| `multiple_issues` | Several problems in one message; the primary one must be chosen |
| `slang_typos` | Informal writing, abbreviations, misspellings |
| `malformed` | Degenerate input: empty, truncated, all caps, emojis only |
| `prompt_injection` | Instructions hidden in the customer text |
| `out_of_scope` | Not an e-commerce support request |

Each tag has at least three cases (enforced by the tests).

## Labelling guidelines

1. **Label the correct answer, not the likely answer.** When the model is known to get a case wrong, the label still follows the rules. Case `012` is labelled `high` even though the model tends to say `urgent`: that disagreement is exactly what the eval should surface.
2. **Priority follows the situation, not the wording.** "URGENTE" in capitals does not make a case `urgent`. See the [priority rules](../docs/taxonomy.md#priority).
3. **One category: the primary problem.** For messages with several issues, pick the one the customer most needs solved and rely on the (unlabelled) summary for the rest. A duplicate charge plus a late delivery is `payment_issue`, because money is being lost now.
4. **Requested action is what the customer asks for.** If they only describe a problem without asking for anything, the action is `none`.
5. **Entities must appear in the message.** `order_ids`, `products` and `amounts_brl` are only what is written, stored already normalised (order IDs without `#`, products lowercased, amounts as numbers). Never label an entity the text does not contain.
6. **Record the reasoning for hard cases** in `notes`, so a reviewer can agree or challenge the label.

## Adding or changing cases

- Keep `id`s unique and messages realistic (write them the way customers actually do).
- After editing, run the dataset tests: they re-validate every case against the pipeline schema, check that labels are already normalised, enforce unique ids and the per-tag minimum.

```bash
pytest tests/test_dataset.py
```

## Limitations

- **Single reference label per case.** A truly ambiguous case has one accepted answer here; a disagreement from the model counts as wrong even when its answer is defensible. The `ambiguous` tag marks these so they can be read separately.
- **Size.** ~34 cases is enough to compare configurations and catch regressions, not to produce statistically tight numbers. The set is meant to grow.
- **One labeller.** Labels reflect one reading of the taxonomy. `notes` make each decision reviewable.
