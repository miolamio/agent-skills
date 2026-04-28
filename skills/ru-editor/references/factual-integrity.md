# Factual Integrity
<!-- ru-lint:ignore-start -->

The most important rule of Russian editing: **never invent specificity**.

When the source text contains vague claims like «качественный», «эффективный», «уникальный», «быстро», «с большим опытом», the editor must NOT replace them with concrete facts that did not exist in the source.

## The Problem

AI editing models — and many human editors trained on AI output — believe good editing means making text more concrete. So they replace «качественный продукт» with «надёжный продукт, протестированный на 50 000 пользователей за 5 лет». The new version is more vivid. It is also fiction.

For internal notes this might be tolerable. For client-facing copy, marketing, contracts, technical documentation, journalism, or anything published — invented specifics are a critical error. They damage trust, create legal exposure, and corrupt the historical record.

This rule **overrides** the «add specificity» principle from informational style. Inforstyle says «replace evaluations with facts»; factual integrity says «only with facts you can point to in the source».

## Allowed Responses to Vague Claims

When you encounter a vague claim with no factual support in the source, choose one:

1. **Remove it.** «Мы предлагаем качественные услуги» becomes «Мы предлагаем услуги».
2. **Weaken it.** «Эффективное решение» becomes «Решение». «Уникальный продукт» becomes «Продукт».
3. **Ask for facts.** Add an editor note: «Здесь не хватает фактов: какие сроки, какие клиенты, какие результаты».
4. **Restructure.** If the entire sentence is empty evaluation, delete it; surrounding context usually carries enough meaning.

## Forbidden

Never invent:

| Category | Examples of forbidden inventions |
|---|---|
| Numbers | Years, counts, percentages, money, durations, dimensions |
| Dates | Specific days, months, years, time periods |
| Names | Companies, clients, people, products, places |
| Examples | Specific cases, scenarios, customer stories |
| Metrics | «80% reduction», «4x faster», «3 minutes vs 20» |
| Sources | «По данным McKinsey», «исследования показывают», «эксперты считают» |
| Guarantees | «100% результат», «возврат денег», «гарантированно» |
| Calls to action | «Попробуйте 14 дней бесплатно», «оставьте заявку до пятницы» |

## Test

Before returning edited text, scan every number, name, date, percentage in the output. For each one, point to the source location it came from. If you cannot — you invented it. Remove it.

## Examples

### Bad (current ru-editor v2.2 example, fixed in v2.3)

Source:
> Наша компания является ведущим поставщиком инновационных решений в области ИИ. Мы стремимся к совершенству и предлагаем широкий спектр услуг.

Old "good" output (invents specifics):
> Мы разрабатываем ИИ-решения: чат-боты, системы анализа данных и автоматизацию документооборота. **Работаем с 2018 года, сделали 80+ проектов для ритейла и финтеха. Средний срок запуска — 6 недель.**

The bolded segment was invented by the editor. Year, count, sectors, timeframe — none of this was in the source.

### Good (Factual Integrity-compliant)

Source: same as above.

Output (any of three valid approaches):

**Approach 1 — Remove empty claims:**
> Мы разрабатываем ИИ-решения для бизнеса.

**Approach 2 — Editor note:**
> Мы разрабатываем ИИ-решения для бизнеса.
>
> Editor note: текст не содержит фактов о сроках, числе проектов, отраслях или результатах. Для сильного маркетингового сообщения нужны конкретные данные от автора.

**Approach 3 — Ask the author:**
> [Editor question to author: какие конкретные продукты вы делаете? с какого года? сколько клиентов? в каких отраслях?]

## Why This Matters More Than «Make It Concrete»

Specificity makes text persuasive. That's why models invent it — they're optimizing for «sounds good». But persuasive fiction is fraud. The editor's job is to make a text **as good as the facts allow**, not better than them. If the facts are weak, the honest output is a weak text plus a note saying «here's what's missing».

A weak honest text is recoverable: the author adds facts, the editor revises. An invented confident text is unrecoverable: the lie is now in the document, and nobody knows it's a lie.
<!-- ru-lint:ignore-end -->
