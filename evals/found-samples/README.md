# ru-editor Found Samples

Реальные русскоязычные тексты, собранные из открытых источников, с явными признаками AI-генерации (AI-Slop). В отличие от `evals/seed-corpus/` (рукотворный фикстур-корпус с полным acceptance-контрактом), эта папка содержит **пары `source.md` + `edited.md`** для отладки линтера на материале «из дикой природы».

## Что внутри

```
evals/found-samples/
  NN-<slug>/
    source.md     # verbatim русский текст с указанной страницы
    edited.md     # отредактированная версия (smoke-test эталон)
```

Каждый `source.md`/`edited.md` начинается с метаданных в HTML-комментарии, обёрнутых в `<!-- ru-lint:ignore-start -->`/`<!-- ru-lint:ignore-end -->`, чтобы маркеры в полях метаданных не фолсили линтер. Сама verbatim-часть `source.md` НЕ обёрнута — линтер должен на ней срабатывать.

Пара `source.md` ↔ `edited.md` создавалась как smoke-test для ru-editor (commit 8212b95): запуск `ru_lint both source.md edited.md` должен проходить без HARD_FAIL. Это упрощённый аналог `expected.md` из seed-corpus, но без `brief.toml`-метаданных.

## Поля метаданных

| Поле | Что значит |
|---|---|
| `source` | URL страницы-источника |
| `genre` | marketing-landing / seo-listicle / corporate-blog / educational / news / help-docs |
| `collected` | Дата сбора (YYYY-MM-DD) |
| `verified_via` | Метод подтверждения текста (WebFetch + URL) |
| `markers_observed` | Маркеры, которые видны на странице — ground truth для линтера |
| `notes` | Опциональные заметки (например, что Haiku мог слегка переформулировать при экстракции) |

## Методология сбора

1. Поиск через Perplexity (`sonar-pro`) — поднял список кандидатов.
2. Верификация через WebFetch на каждый URL — извлекли verbatim-фрагменты непосредственно со страниц.
3. Один батч от Perplexity оказался сфабрикован (галлюцинации с искусственно набитыми маркерами в одном абзаце) — выкинут.

**Важный дисклеймер:** WebFetch проксирует через Haiku, который может слегка перефразировать. Для линтер-фикстур это приемлемо — главное, что AI-Slop-характер сохранён и набор маркеров реален. Для production-grade ground truth (golden corpus, Phase 5) нужен ручной copy-paste с открытой страницы.

## Как использовать

Прогнать линтер по одному образцу:

```bash
python3 skills/ru-editor/scripts/ru_lint.py check evals/found-samples/01-vc-listicle-emoji/source.md
```

Прогнать по всем:

```bash
for f in evals/found-samples/*/source.md; do
  echo "=== $f ==="
  python3 skills/ru-editor/scripts/ru_lint.py check "$f"
done
```

Ожидаемое поведение: каждый файл должен дать ≥1 HARD_FAIL и/или несколько WARN. Если линтер ничего не нашёл на тексте, помеченном как AI-Slop, — это потенциальный false negative и повод доработать regex/правила.

## Baseline после Phase 2C (2026-04-28)

Phase 2C расширила линтер 12 phrase-маркерами в `banned-markers.toml` (2 HARD_FAIL, 10 WARN) и 5 regex-чеками: `not_only_but_also`, `parallel_kak_tak_i`, `bold_inline_header_in_list`, `filler_paragraph_opener`, `unsourced_percentage` (все WARN).

| # | Файл | HARD_FAIL | WARN | Что поймал |
|---|---|---|---|---|
| 01 | vc-listicle-emoji | 3 | 0 | `no_emoji` × 3 (💥, 📌, 📌) |
| 02 | habr-studyai-corp | 0 | 4 | warn-маркеры «настоящий прорыв», «также отметим», «стремительно растёт», `not_only_but_also` |
| 03 | sostav-press-release | 0 | 2 | «принципиально отличается», «первый представитель своего класса» |
| 04 | lpmotor-seo-landing | 0 | 1 | «широкий спектр задач» (+ потенциально `unsourced_percentage`, см. ниже) |
| 05 | yagla-marketing-banners | 1 | 1 | HARD «вот тут на помощь приходят» + `not_only_but_also` |
| 06 | skillbox-edu-img | 0 | 2 | «оживляют пиксели» (или близкое), `filler_paragraph_opener` («Кроме того») |
| 07 | it-world-tech-news | 0 | 1 | `parallel_kak_tak_i` («как среди профессионалов, так и у…») |
| 08 | gigachat-help-listicle | 0 | 0 | — структурный AI-шаблон, regex-ом не ловится |

**Сравнение:** до Phase 2C было `hard=3, warn=0` (1 файл из 8 фолил). Стало `hard=4, warn=11` (7 из 8).

## Известные пробелы

- **Sample 08** — шаблонная структура «**Имя** — описание / ### Возможности / ### Недостатки» под каждой моделью. Это структурный AI-pattern, не лексический. Regex-ом не ловится; нужен structural-checker (анализ повторяющихся блоков заголовок-список-заголовок-список).
- **Opinion-жанр** — `unsourced_percentage` фолит на риторических цифрах вроде «90% того, что показывают» в авторских колонках. Это формально WARN, не блокирует, но шум возможен. Mitigation на будущее: добавить `--mode=opinion` с whitelist для риторических процентов.
- **Ласковые AI-маркеры**, не покрытые ни TOML, ни regex: «Да-да» (фейк-разговорный тон), «единая нейронная сеть» (redundant qualifier), «представляет собой связку из». Кандидаты на Phase 2D.

## Стратификация по жанрам

| # | Жанр | Источник |
|---|---|---|
| 01 | seo-listicle | vc.ru |
| 02 | corporate-blog | habr.com (StudyAI) |
| 03 | corporate-blog (PR) | sostav.ru |
| 04 | seo-landing | lpmotor.ru |
| 05 | marketing-landing | yagla.ru |
| 06 | educational | skillbox.ru |
| 07 | news/listicle | it-world.ru |
| 08 | help-docs/educational | giga.chat |

Тематика всех образцов — обзоры русскоязычных нейросетей (актуальная SEO-ниша 2026 года). Для других тематик добавляйте новые подпапки с возрастающим NN.

## Добавление нового образца

1. Возьми следующий незанятый номер NN.
2. Создай папку `NN-<short-slug>/`.
3. Найди реальную страницу с AI-Slop-признаками. Скопируй verbatim-фрагмент 300-1000 символов.
4. Запиши `source.md` по шаблону (см. существующие файлы).
5. Прогони `ru_lint.py check` — должны быть находки. Зафиксируй их в `markers_observed`.
6. Не редактируй текст. Если хочется добавить эталон — клади `expected.md` рядом по схеме seed-corpus.
