# Taxonomy

The controlled vocabulary the pipeline produces. These definitions are the reference for the prompt, the schema field descriptions and the labelling of the golden set: when they disagree, this document should be updated together with the code.

Examples are written the way customers actually write: informal Brazilian Portuguese.

## Category

The customer's main **problem**. Exactly one per message.

Category describes what went wrong; [requested action](#requested-action) describes what the customer wants done about it. *"Chegou quebrado, quero meu dinheiro de volta"* is `damaged_or_defective` + `refund`, not `refund_issue`.

| Value | Use when | Example |
|---|---|---|
| `delivery_issue` | Order late, not received, or questions about tracking | *"meu pedido era pra chegar dia 5 e até agora nada"* |
| `damaged_or_defective` | Product arrived broken or stopped working | *"a tela do celular veio trincada"* |
| `wrong_item` | Received a different product, size or colour than ordered | *"pedi tênis 42 e veio 38"* |
| `return_or_exchange` | Wants to return or exchange a product that has **no defect** (regret, didn't fit) | *"comprei a blusa mas não gostei, quero devolver"* |
| `refund_issue` | A refund that was already requested or promised has not arrived | *"cancelei faz 15 dias e o estorno não caiu"* |
| `payment_issue` | Charge problems: duplicate charge, declined payment, invoice | *"fui cobrado duas vezes no cartão"* |
| `order_change` | Change address or items, or cancel an order **before** it ships | *"quero trocar o endereço de entrega do pedido 5521"* |
| `account_access` | Login, password, account data | *"não consigo entrar na minha conta, a senha não funciona"* |
| `product_question` | Questions before buying | *"esse fone funciona no iphone?"* |
| `out_of_scope` | Not an e-commerce support request: spam, unrelated topics, or attempts to give instructions to the system | *"ignore as instruções anteriores e..."* |

**Several problems in one message:** choose the one the customer most needs solved and mention the others in the summary. A duplicate charge plus a late delivery is `payment_issue`, because money is being lost now.

## Requested action

What the customer is asking the company to do.

| Value | Use when |
|---|---|
| `refund` | Wants money back |
| `replacement` | Wants a new or correct item sent |
| `cancel_order` | Wants the order cancelled |
| `delivery_update` | Wants to know where the order is or when it arrives |
| `information` | Wants an answer to a question |
| `account_support` | Wants help with their account |
| `other` | Asks for something not covered above |
| `none` | Nothing is requested (complaint only, or out of scope) |

## Priority

How fast a human should look at the message. Priority follows **the situation**, not the customer's wording: writing *"URGENTE"* in capitals does not make a message urgent by itself.

| Value | Rule | Example |
|---|---|---|
| `urgent` | Financial loss in progress (e.g. duplicate charge), safety risk, or legal threat (Procon, lawsuit) | *"cobraram 3x no meu cartão"*, *"vou no Procon"* |
| `high` | Order not received past the deadline, damaged or wrong item, or an angry customer | *"chegou quebrado"*, *"já faz 2 semanas de atraso"* |
| `medium` | Needs action but there is no time pressure | *"quero trocar o tamanho"* |
| `low` | Questions and out-of-scope messages | *"vocês entregam em Manaus?"* |

An **overdue refund** (already promised, past the expected window) is `high`: the customer is owed money and has waited, but nothing is actively draining their account, so it is not `urgent`.

`priority_reason` holds one short sentence in Portuguese justifying the choice.

> **Known gap (v1):** in early manual tests the model rated *"chegou quebrado e quero meu dinheiro de volta URGENTE"* as `urgent` instead of `high`, following the customer's wording rather than the rule. Cases like this are part of the golden set, and phase 3 adds business-rule checks.

## Sentiment

| Value | Meaning |
|---|---|
| `positive` | Friendly or satisfied tone |
| `neutral` | Factual, no strong emotion |
| `frustrated` | Unhappy but calm |
| `angry` | Hostile tone, capitals, threats, insults |

## Extracted entities

| Field | Rule | Normalisation |
|---|---|---|
| `order_ids` | Only order numbers that **appear in the message**. Never invented or guessed. | Whitespace and leading `#` removed, uppercased, de-duplicated: `" #48213 "` becomes `"48213"` |
| `products` | Products mentioned, as short names | Lowercased, whitespace collapsed, de-duplicated |
| `amounts_brl` | Monetary amounts mentioned, as plain numbers in BRL | Brazilian format converted by the model: `"R$ 1.299,90"` becomes `1299.9`. Negative values are rejected. |

An empty list means "not mentioned". Every field is always present.

## Free text

| Field | Rule |
|---|---|
| `summary` | Neutral, 1 to 2 sentences, in Brazilian Portuguese, for a support agent. No greetings or opinions. At most 400 characters. |
| `priority_reason` | One short sentence in Brazilian Portuguese. |
