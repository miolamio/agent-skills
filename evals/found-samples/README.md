# ru-editor Found Samples

Реальные русскоязычные тексты, собранные из открытых источников, с явными признаками AI-генерации (AI-Slop). В отличие от `evals/seed-corpus/` (рукотворный фикстур-корпус), эта папка содержит **тройки `source.md` + `edited.md` + `brief.toml`** для отладки линтера на материале «из дикой природы».

## Что внутри

```
evals/found-samples/
  NN-<slug>/
    source.md     # verbatim русский текст с указанной страницы
    edited.md     # отредактированная версия (smoke-test эталон)
    brief.toml    # acceptance-контракт (см. ниже)
```

Каждый `source.md`/`edited.md` начинается с метаданных в HTML-комментарии, обёрнутых в `<!-- ru-lint:ignore-start -->`/`<!-- ru-lint:ignore-end -->`, чтобы маркеры в полях метаданных не фолсили линтер. Сама verbatim-часть `source.md` НЕ обёрнута — линтер должен на ней срабатывать.

## brief.toml schema

Зеркалит `seed-corpus/*/brief.toml` (schema_version 1.0):

```toml
[meta]
schema_version = "1.0"
genre = "marketing-landing"        # см. genre-таблицу ниже
intensity = "medium"                # light|medium|heavy
mode = "line_edit"                  # editing mode for smoke-test
expected_mode = "line_edit"
source_url = "https://..."          # specific to found-samples

[expected_findings]
hard_fail_min = 1
hard_fail_max = 3
warn_min = 1
warn_max = 5
checks_must_fire = ["no_banned_markers", "not_only_but_also"]
checks_must_not_fire_on_edited = ["no_banned_markers", ...]
expected_clean_on_lint = true       # 0 HARD_FAIL on edited.md (invariant)
```

## Поля метаданных в source.md

| Поле | Что значит |
|---|---|
| `source` | URL страницы-источника |
| `genre` | seo-listicle / corporate-blog / seo-landing / marketing-landing / educational / news / help-docs / b2b-listicle / research-summary / educational-tutorial / marketing-case-study |
| `collected` | Дата сбора (YYYY-MM-DD) |
| `verified_via` | Метод подтверждения текста (WebFetch + URL) |
| `markers_observed` | Маркеры, которые видны на странице — ground truth для линтера |
| `notes` | Опциональные заметки (например, что Haiku мог слегка переформулировать при экстракции) |

## Методология сбора

1. Поиск через Perplexity (`sonar-pro`) — поднял список кандидатов.
2. Верификация через WebFetch на каждый URL — извлекли verbatim-фрагменты непосредственно со страниц.
3. Один батч от Perplexity оказался сфабрикован (галлюцинации с искусственно набитыми маркерами в одном абзаце) — выкинут.

**Важный дисклеймер:** WebFetch проксирует через Haiku, который может слегка перефразировать. Для линтер-фикстур это приемлемо — главное, что AI-Slop-характер сохранён и набор маркеров реален. Для production-grade ground truth нужен ручной copy-paste с открытой страницы.

## Как использовать

Прогнать линтер по одному образцу:

```bash
python3 skills/ru-editor/scripts/ru_lint.py check evals/found-samples/01-vc-listicle-emoji/source.md
```

Прогнать acceptance-контракт по всем 13:

```bash
bash skills/ru-editor/scripts/run_phase2c_acceptance.sh
```

Ожидаемое поведение: каждый `source.md` фолит ≥0 HARD_FAIL в пределах `[hard_fail_min, hard_fail_max]`, а `edited.md` всегда чист (0 HARD_FAIL).

## Baseline после Phase 2G (2026-05-05)

Phase 2G: 33 зарегистрированных чека (11 HARD_FAIL + 22 WARN), +14 фраз WARN в `banned-markers.toml` (evaluation-without-proof + corporate-research-stamps), +3 regex-чека (`hedging_intro`, `sweeping_generalization`, `bold_in_prose_with_epithet`).

### Стратификация и fires (source.md)

| # | Жанр | Источник | HARD_FAIL | WARN | Что поймал |
|---|---|---|---|---|---|
| 01 | seo-listicle | vc.ru | 3 | 0 | `no_emoji` × 3 |
| 02 | corporate-blog | habr.com | 0 | 4 | `no_warn_markers` × 4 |
| 03 | corporate-blog (PR) | sostav.ru | 0 | 2 | «принципиально отличается», «первый представитель своего класса» |
| 04 | seo-landing | lpmotor.ru | 0 | 1 | «широкий спектр задач» |
| 05 | marketing-landing | yagla.ru | 1 | 2 | HARD «вот тут на помощь приходят» + `not_only_but_also` |
| 06 | educational | skillbox.ru | 0 | 2 | «оживляют пиксели», `filler_paragraph_opener` |
| 07 | news/listicle | it-world.ru | 0 | 2 | `parallel_kak_tak_i` + warn-marker |
| 08 | help-docs | giga.chat | 0 | 3 | `repeated_heading_template` × 2 + `em_dash_budget` |
| 09 | research-summary | ucaas.cnews.ru | 0 | 1 | `hedging_intro` «Вероятнее всего» |
| 10 | b2b-listicle | vc.ru | 0 | 1 | `em_dash_budget` (плотные тире-bullet) |
| 11 | educational-tutorial | skillbox.ru | 0 | 3 | `sweeping_generalization` × 2 + «значительно упрощают» |
| 12 | corporate-blog | cossa.ru | 0 | 5 | corporate-research-stamps × 5 |
| 13 | marketing-case-study | sostav.ru | 0 | 1 | `bold_in_prose_with_epithet` «**одним из ключевых перфоманс-каналов**» |

**Сравнение:**
- Стартовая Phase 2 (8 файлов): hard=3, warn=0. **1 из 8 файлов фолил.**
- Phase 2D (8 файлов): hard=4, warn=14. **8 из 8 файлов фолят.**
- Phase 2F (13 файлов): hard=4, warn=17. **9 из 13 файлов фолят.**
- Phase 2G (13 файлов): hard=4, warn=27. **13 из 13 файлов фолят.** Soft-AI-Slop gap закрыт.

## Закрытые пробелы (Phase 2G — 2026-05-05)

| Класс | Примеры в корпусе | Реализованный чек |
|---|---|---|
| Hedging-интро | «Вероятнее всего, это связано с…», «По всей видимости» (начало предложения) | `hedging_intro` (WARN) — sentence-level, disjoint от `filler_paragraph_opener` |
| Sweeping generalization | «применять их должны уметь все», «делает всё, что может понадобиться» | `sweeping_generalization` (WARN) — regex для «всё что может/нужно», «должны уметь все», «всем нужно знать» |
| Evaluation без proof | «значительно упрощают/повышают/ускоряют» | TOML `warn_markers` (6 форм) |
| Corporate research stamps | «ключевые данные и инсайты», «показатель зрелости рынка», «качественных площадках», «стратегический канал», «закрепился как стратегический» | TOML `warn_markers` (8 форм) |
| Bold inline-header без двоеточия (mid-sentence) | «**одним из ключевых перфоманс-каналов** проекта» | `bold_in_prose_with_epithet` (WARN) — bold с эпитетом «один из ключев*/главн*/основн*/важнейш*/ведущ*» |

Sample 08 — шаблонная структура — закрыта в Phase 2D через `repeated_heading_template`.

Opinion-жанр (sample 12-opinion-heavy в seed-corpus) — закрыт в Phase 2D через opinion-mode whitelist.

## Добавление нового образца

1. Возьми следующий незанятый номер NN.
2. Создай папку `NN-<short-slug>/`.
3. Найди реальную страницу с AI-Slop-признаками. Скопируй verbatim-фрагмент 300-1000 символов.
4. Запиши `source.md` по шаблону существующих файлов.
5. Запиши `edited.md` — твоя чистая версия по правилам ru-editor.
6. Прогони `ru_lint.py check source.md` — зафиксируй fires.
7. Запиши `brief.toml` с budget и обязательными чеками.
8. Прогони `bash skills/ru-editor/scripts/run_phase2c_acceptance.sh` — должно быть PASS.
