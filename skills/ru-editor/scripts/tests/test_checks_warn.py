"""Tests for WARN checks (Task 10) — heuristic patterns informed by grounding."""
import unittest
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

from ru_lint import Document, run_checks  # noqa: E402


def lint_check(text: str, check_name: str | None = None):
    findings = run_checks(Document(text=text), source=None, mode="check")
    if check_name:
        findings = [f for f in findings if f.check == check_name]
    return findings


def lint_diff(orig: str, edited: str, check_name: str | None = None):
    findings = run_checks(Document(text=edited), source=Document(text=orig), mode="diff")
    if check_name:
        findings = [f for f in findings if f.check == check_name]
    return findings


# ---------------------------------------------------------------------------
# Group A — 7 plan-spec WARN checks
# ---------------------------------------------------------------------------


class TestRepeatedSentenceOpeners(unittest.TestCase):
    def test_three_in_a_row_same_opener_warns(self):
        text = "Мы запустили продукт. Мы наняли команду. Мы выросли."
        f = lint_check(text, "repeated_sentence_openers")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].severity, "WARN")

    def test_two_in_a_row_no_warn(self):
        text = "Мы запустили продукт. Мы наняли команду. Команда сильная."
        f = lint_check(text, "repeated_sentence_openers")
        self.assertEqual(f, [])

    def test_list_bullet_dash_not_an_opener(self):
        # Phase 2H: bullets «-» / «*» / «+» are stripped before extracting opener.
        # Otherwise dense lists fire on every 3+ items.
        text = "- Первый пункт.\n- Второй пункт.\n- Третий пункт.\n"
        f = lint_check(text, "repeated_sentence_openers")
        self.assertEqual(f, [])

    def test_numbered_list_marker_not_an_opener(self):
        text = "1. Первый.\n2. Второй.\n3. Третий.\n"
        f = lint_check(text, "repeated_sentence_openers")
        self.assertEqual(f, [])

    def test_repeated_word_in_list_items_still_warns(self):
        # If actual first word after the bullet repeats — we DO want to warn.
        text = "- Используйте API. - Используйте кэш. - Используйте webhook."
        f = lint_check(text, "repeated_sentence_openers")
        self.assertEqual(len(f), 1)


class TestXANeYPileup(unittest.TestCase):
    def test_three_in_proximity_warns(self):
        text = (
            "Скорость, а не громоздкость. Простота, а не сложность. Гибкость, а не жёсткость."
        )
        f = lint_check(text, "x_a_ne_y_pileup")
        self.assertEqual(len(f), 1)

    def test_two_in_proximity_no_warn(self):
        text = "Скорость, а не громоздкость. Простота, а не сложность."
        f = lint_check(text, "x_a_ne_y_pileup")
        self.assertEqual(f, [])


class TestEtoInDefinitions(unittest.TestCase):
    def test_three_definitions_with_eto_warn(self):
        text = (
            "Проект — это план. Команда — это люди. Успех — это результат."
        )
        f = lint_check(text, "eto_in_definitions")
        self.assertEqual(len(f), 1)

    def test_two_definitions_no_warn(self):
        text = "Проект — это план. Команда — это люди."
        f = lint_check(text, "eto_in_definitions")
        self.assertEqual(f, [])


class TestWordRepetitionInSentence(unittest.TestCase):
    def test_three_in_one_sentence_warns(self):
        text = "Система обрабатывает данные системы из системы."
        f = lint_check(text, "word_repetition_in_sentence")
        self.assertEqual(len(f), 1)

    def test_stopword_repetition_does_not_fire(self):
        # Stopwords like «и», «в», «не» — common, do not trigger.
        text = "В системе и в коде и в данных всё работает."
        f = lint_check(text, "word_repetition_in_sentence")
        self.assertEqual(f, [])


class TestSynonymClusterDrift(unittest.TestCase):
    def test_three_synonyms_from_one_cluster_warn(self):
        text = (
            "Наш продукт быстрый. Это решение надёжное. Платформа удобна для всех."
        )
        # product_drift cluster: продукт, решение, платформа — 3 members in proximity.
        f = lint_check(text, "synonym_cluster_drift")
        self.assertEqual(len(f), 1)

    def test_two_synonyms_no_warn(self):
        text = "Наш продукт быстрый. Решение надёжное."
        f = lint_check(text, "synonym_cluster_drift")
        self.assertEqual(f, [])


class TestMixedListPunctuation(unittest.TestCase):
    def test_mixed_terminal_punctuation_warns(self):
        text = "- Первый.\n- Второй;\n- Третий\n"
        f = lint_check(text, "mixed_list_punctuation")
        self.assertEqual(len(f), 1)

    def test_consistent_list_no_warn(self):
        text = "- Первый.\n- Второй.\n- Третий.\n"
        f = lint_check(text, "mixed_list_punctuation")
        self.assertEqual(f, [])


class TestLengthRatioViolation(unittest.TestCase):
    def test_within_tolerance_ok(self):
        f = lint_diff("a" * 1000, "a" * 1100, "length_ratio_violation")
        self.assertEqual(f, [])

    def test_too_short_warns(self):
        f = lint_diff("a" * 1000, "a" * 700, "length_ratio_violation")
        self.assertEqual(len(f), 1)

    def test_too_long_warns(self):
        f = lint_diff("a" * 1000, "a" * 1300, "length_ratio_violation")
        self.assertEqual(len(f), 1)


# ---------------------------------------------------------------------------
# Group B — 4 grounding-informed checks
# ---------------------------------------------------------------------------


class TestNoWarnMarkers(unittest.TestCase):
    def test_warn_marker_fires(self):
        # "не упустите шанс" is in TOML warn_markers.
        f = lint_check("Не упустите шанс присоединиться к нам.", "no_warn_markers")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].severity, "WARN")

    def test_clean_text_no_fire(self):
        f = lint_check("Обычное предложение без шаблонов.", "no_warn_markers")
        self.assertEqual(f, [])


class TestArrowsAsBullets(unittest.TestCase):
    def test_arrow_bullet_fires(self):
        text = "Преимущества:\n→ Скорость\n→ Простота\n"
        f = lint_check(text, "arrows_as_bullets")
        self.assertEqual(len(f), 2)
        self.assertEqual(f[0].severity, "WARN")

    def test_dash_bullet_no_fire(self):
        text = "Преимущества:\n- Скорость\n- Простота\n"
        f = lint_check(text, "arrows_as_bullets")
        self.assertEqual(f, [])


class TestCheckmarkAsBullet(unittest.TestCase):
    def test_checkmark_fires(self):
        text = "Релиз:\n✅ Скорость\n✅ Простота\n"
        f = lint_check(text, "checkmark_as_bullet")
        self.assertEqual(len(f), 1)

    def test_no_checkmark_no_fire(self):
        text = "Релиз:\n- Скорость\n- Простота\n"
        f = lint_check(text, "checkmark_as_bullet")
        self.assertEqual(f, [])


class TestIntensifierBurst(unittest.TestCase):
    def test_three_intensifiers_warn(self):
        text = "Мы полностью переосмыслили интерфейс. Совершенно новый дизайн. Принципиально иной подход."
        f = lint_check(text, "intensifier_burst")
        self.assertEqual(len(f), 1)

    def test_one_intensifier_no_warn(self):
        text = "Мы полностью переосмыслили интерфейс. Хороший дизайн. Удобный подход."
        f = lint_check(text, "intensifier_burst")
        self.assertEqual(f, [])


class TestNotOnlyButAlso(unittest.TestCase):
    """Phase 2C: «не только X, но и Y» construction."""

    def test_simple_construction_warns(self):
        text = "ИИ нужен не только для генерации текста, но и для создания видео."
        f = lint_check(text, "not_only_but_also")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].severity, "WARN")

    def test_yagla_style_warns(self):
        text = "Искусственный интеллект теперь не только для умных разговоров и беспилотных машин, но и для рекламы."
        f = lint_check(text, "not_only_but_also")
        self.assertEqual(len(f), 1)

    def test_two_constructions_warn_twice(self):
        text = (
            "Не только сегодня, но и завтра. И не только здесь, но и там."
        )
        f = lint_check(text, "not_only_but_also")
        self.assertEqual(len(f), 2)

    def test_no_construction_no_warn(self):
        text = "ИИ нужен для генерации текста и для создания видео."
        f = lint_check(text, "not_only_but_also")
        self.assertEqual(f, [])

    def test_too_far_apart_no_warn(self):
        # «не только» and «но и» separated by >120 chars — not the same construction.
        far = "x " * 80
        text = f"Не только это {far}но и другое."
        f = lint_check(text, "not_only_but_also")
        self.assertEqual(f, [])

    def test_sentence_boundary_no_warn(self):
        # Period between «не только» and «но и» — separate sentences.
        text = "Не только это важно. Это критично, но и другое тоже."
        f = lint_check(text, "not_only_but_also")
        self.assertEqual(f, [])


class TestParallelKakTakI(unittest.TestCase):
    """Phase 2C: «как X, так и Y» construction."""

    def test_simple_warns(self):
        text = "Это полезно как для разработчиков, так и для дизайнеров."
        f = lint_check(text, "parallel_kak_tak_i")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].severity, "WARN")

    def test_kak_sredi_warns(self):
        text = "Инструменты популярны как среди профессионалов, так и у широкой аудитории."
        f = lint_check(text, "parallel_kak_tak_i")
        self.assertEqual(len(f), 1)

    def test_no_construction_no_warn(self):
        text = "Это работает как часы. Так получилось."
        f = lint_check(text, "parallel_kak_tak_i")
        self.assertEqual(f, [])


class TestBoldInlineHeaderInList(unittest.TestCase):
    """Phase 2C: list items with **Bold**: opening — typical AI markdown."""

    def test_bold_with_colon_warns(self):
        text = "- **Скорость**: всё быстро\n- **Простота**: всё понятно\n"
        f = lint_check(text, "bold_inline_header_in_list")
        self.assertEqual(len(f), 2)
        self.assertEqual(f[0].severity, "WARN")

    def test_bold_with_em_dash_warns(self):
        text = "* **Имя** — описание\n"
        f = lint_check(text, "bold_inline_header_in_list")
        self.assertEqual(len(f), 1)

    def test_plain_list_no_warn(self):
        text = "- Скорость\n- Простота\n- Удобство\n"
        f = lint_check(text, "bold_inline_header_in_list")
        self.assertEqual(f, [])

    def test_bold_without_colon_no_warn(self):
        # «- **Скорость** всё быстро» — bold но без двоеточия/тире.
        text = "- **Скорость** всё быстро\n"
        f = lint_check(text, "bold_inline_header_in_list")
        self.assertEqual(f, [])

    def test_bold_in_prose_no_warn(self):
        # Bold вне списка не считается.
        text = "Это **жирный** текст в обычном абзаце.\n"
        f = lint_check(text, "bold_inline_header_in_list")
        self.assertEqual(f, [])

    def test_latin_product_name_whitelisted(self):
        # Phase 2H: «- **StudyAI** — описание» — product-name listing, not AI-Slop.
        text = "- **StudyAI** — российский сервис\n- **UseGPT** — платформа\n"
        f = lint_check(text, "bold_inline_header_in_list")
        self.assertEqual(f, [])

    def test_camelcase_with_digits_whitelisted(self):
        text = "- **Web2App** — новая механика\n- **ChatGPT-4** — модель\n"
        f = lint_check(text, "bold_inline_header_in_list")
        self.assertEqual(f, [])

    def test_cyrillic_bold_still_fires(self):
        # Кириллический bold-заголовок — AI-маркдаун-шаблон, fires.
        text = "- **Скорость** — всё быстро\n- **Простота** — всё понятно\n"
        f = lint_check(text, "bold_inline_header_in_list")
        self.assertEqual(len(f), 2)

    def test_multiword_latin_still_fires(self):
        text = "- **Easy Setup**: всё просто\n- **Fast API**: быстро\n"
        f = lint_check(text, "bold_inline_header_in_list")
        self.assertEqual(len(f), 2)


class TestFillerParagraphOpener(unittest.TestCase):
    """Phase 2C: filler/transitional paragraph openers."""

    def test_na_samom_dele_warns(self):
        text = "Первый абзац.\n\nНа самом деле второй абзац о другом."
        f = lint_check(text, "filler_paragraph_opener")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].severity, "WARN")

    def test_krome_togo_warns(self):
        text = "Первый абзац.\n\nКроме того, есть ещё один аспект."
        f = lint_check(text, "filler_paragraph_opener")
        self.assertEqual(len(f), 1)

    def test_bolee_togo_warns(self):
        text = "Первый абзац.\n\nБолее того, ситуация изменилась."
        f = lint_check(text, "filler_paragraph_opener")
        self.assertEqual(len(f), 1)

    def test_first_paragraph_warns(self):
        # Фраза в начале документа — тоже зачин параграфа.
        text = "На самом деле всё иначе."
        f = lint_check(text, "filler_paragraph_opener")
        self.assertEqual(len(f), 1)

    def test_phrase_in_middle_no_warn(self):
        # Та же фраза в середине абзаца — допустимо.
        text = "Один аспект. Кроме того, есть второй аспект."
        f = lint_check(text, "filler_paragraph_opener")
        self.assertEqual(f, [])


class TestUnsourcedPercentage(unittest.TestCase):
    """Phase 2C: percentage in prose without nearby source citation."""

    def test_unsourced_percentage_warns(self):
        text = "Более 70% пользователей выбирают наш продукт каждый день."
        f = lint_check(text, "unsourced_percentage")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].severity, "WARN")

    def test_with_url_no_warn(self):
        text = "По данным https://example.com/report 70% пользователей выбирают это."
        f = lint_check(text, "unsourced_percentage")
        self.assertEqual(f, [])

    def test_with_citation_marker_no_warn(self):
        text = "Согласно исследованию VTsIOM, 70% респондентов поддерживают идею."
        f = lint_check(text, "unsourced_percentage")
        self.assertEqual(f, [])

    def test_financial_discount_no_warn(self):
        # «скидка 30%» — точная цифра в финансовом контексте, не риторика.
        text = "До 1 марта действует скидка 30% на годовую подписку."
        f = lint_check(text, "unsourced_percentage")
        self.assertEqual(f, [])

    def test_ab_experiment_result_no_warn(self):
        # Цифра из A/B-эксперимента — легитимный case-study, не fake stat.
        text = "После A/B-эксперимента доход кампаний вырос на 26%."
        f = lint_check(text, "unsourced_percentage")
        self.assertEqual(f, [])

    def test_no_percentage_no_warn(self):
        text = "Большинство пользователей выбирают наш продукт."
        f = lint_check(text, "unsourced_percentage")
        self.assertEqual(f, [])


class TestRepeatedHeadingTemplate(unittest.TestCase):
    """Phase 2D: 2+ headings start with the same marketing-template prefix."""

    def test_vozmozhnosti_repeated_warns(self):
        text = (
            "### Возможности и преимущества YandexGPT\n\n"
            "Текст.\n\n"
            "### Возможности и преимущества Kandinsky 3.1\n\n"
            "Текст.\n"
        )
        f = lint_check(text, "repeated_heading_template")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].severity, "WARN")

    def test_nedostatki_repeated_warns(self):
        text = (
            "### Недостатки YandexGPT\n\n"
            "Текст.\n\n"
            "### Недостатки Kandinsky\n\n"
            "Текст.\n"
        )
        f = lint_check(text, "repeated_heading_template")
        self.assertEqual(len(f), 1)

    def test_two_template_groups_warn_twice(self):
        text = (
            "### Возможности и преимущества A\n"
            "### Недостатки A\n"
            "### Возможности и преимущества B\n"
            "### Недостатки B\n"
        )
        f = lint_check(text, "repeated_heading_template")
        # Two distinct template prefixes each with 2 hits.
        self.assertEqual(len(f), 2)

    def test_single_template_heading_no_warn(self):
        text = "### Возможности и преимущества YandexGPT\n\nТекст.\n"
        f = lint_check(text, "repeated_heading_template")
        self.assertEqual(f, [])

    def test_non_template_repeated_prefix_no_warn(self):
        # «Установка X» / «Установка Y» — обычные tech-заголовки, не шаблон.
        text = "## Установка зависимостей\nТекст.\n## Установка приложения\nТекст.\n"
        f = lint_check(text, "repeated_heading_template")
        self.assertEqual(f, [])


class TestUnsourcedPercentageOpinionWhitelist(unittest.TestCase):
    """Phase 2D: opinion-mode markers suppress unsourced_percentage."""

    def test_schitayu_no_warn(self):
        text = "Я считаю, что 90% того, что нам показывают, — маркетинг."
        f = lint_check(text, "unsourced_percentage")
        self.assertEqual(f, [])

    def test_dumayu_no_warn(self):
        text = "Думаю, 80% этих проектов закроется через год."
        f = lint_check(text, "unsourced_percentage")
        self.assertEqual(f, [])

    def test_po_moemu_no_warn(self):
        text = "По-моему, 70% всей шумихи — пустое."
        f = lint_check(text, "unsourced_percentage")
        self.assertEqual(f, [])

    def test_no_opinion_marker_still_warns(self):
        text = "70% пользователей в восторге от продукта."
        f = lint_check(text, "unsourced_percentage")
        self.assertEqual(len(f), 1)


# ---------------------------------------------------------------------------
# Phase 2G — soft-AI-Slop additions
# ---------------------------------------------------------------------------


class TestHedgingIntro(unittest.TestCase):
    """Phase 2G: sentence-level hedging openers."""

    def test_veroyatnee_vsego_warns(self):
        text = "Они полагаются на зарубежные решения. Вероятнее всего, это связано с распространенностью."
        f = lint_check(text, "hedging_intro")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].severity, "WARN")

    def test_skoree_vsego_warns(self):
        text = "Скорее всего, проект задержится на пару недель."
        f = lint_check(text, "hedging_intro")
        self.assertEqual(len(f), 1)

    def test_kak_pravilo_at_sentence_start_warns(self):
        text = "Команда уже знает план. Как правило, такие задачи занимают неделю."
        f = lint_check(text, "hedging_intro")
        self.assertEqual(len(f), 1)

    def test_kak_pravilo_mid_sentence_no_warn(self):
        # Mid-clause «как правило» — не зачин предложения.
        text = "Сотрудники как правило не делятся чувствительной информацией на собеседованиях."
        f = lint_check(text, "hedging_intro")
        self.assertEqual(f, [])

    def test_paragraph_start_warns(self):
        text = "Первый абзац.\n\nПо всей видимости, второй абзац о другом."
        f = lint_check(text, "hedging_intro")
        self.assertEqual(len(f), 1)

    def test_no_hedging_no_warn(self):
        text = "Команда выпустила релиз вовремя. Все довольны результатом."
        f = lint_check(text, "hedging_intro")
        self.assertEqual(f, [])

    def test_does_not_double_fire_with_filler_paragraph_opener(self):
        # «На самом деле» уже ловится filler_paragraph_opener.
        # hedging_intro НЕ должен срабатывать на эти фразы — disjoint sets.
        text = "Один абзац.\n\nНа самом деле всё иначе."
        f = lint_check(text, "hedging_intro")
        self.assertEqual(f, [])


class TestSweepingGeneralization(unittest.TestCase):
    """Phase 2G: «всё, что может понадобиться», «должны уметь все»."""

    def test_vse_chto_mozhet_warns(self):
        text = "Эти функции позволяют делать всё, что может понадобиться в работе."
        f = lint_check(text, "sweeping_generalization")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].severity, "WARN")

    def test_dolzhny_umet_vse_warns(self):
        text = "Это базовый навык, и применять его должны уметь все сотрудники."
        f = lint_check(text, "sweeping_generalization")
        self.assertEqual(len(f), 1)

    def test_vsem_nuzhno_znat_warns(self):
        text = "Базовые SQL-запросы — это то, что всем нужно знать в нашей команде."
        f = lint_check(text, "sweeping_generalization")
        self.assertEqual(len(f), 1)

    def test_specific_list_no_warn(self):
        text = "Эти функции делают конкретные задачи: объединяют ячейки, копируют данные."
        f = lint_check(text, "sweeping_generalization")
        self.assertEqual(f, [])


class TestBoldInProseWithEpithet(unittest.TestCase):
    """Phase 2G: bold mid-sentence with marketing epithet."""

    def test_odnim_iz_klyuchevykh_warns(self):
        text = (
            "Поиск работал по веб-целям и был **одним из ключевых перфоманс-каналов** "
            "проекта, поэтому смена стратегии могла создать риски."
        )
        f = lint_check(text, "bold_in_prose_with_epithet")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].severity, "WARN")

    def test_odin_iz_glavnykh_warns(self):
        text = "Это **один из главных факторов** успеха кампании."
        f = lint_check(text, "bold_in_prose_with_epithet")
        self.assertEqual(len(f), 1)

    def test_odna_iz_vedushchikh_warns(self):
        text = "Компания стала **одной из ведущих платформ** на рынке."
        f = lint_check(text, "bold_in_prose_with_epithet")
        self.assertEqual(len(f), 1)

    def test_plain_bold_no_warn(self):
        # Bold без эпитета «один из …» — допустим.
        text = "Используется **API REST** для интеграции."
        f = lint_check(text, "bold_in_prose_with_epithet")
        self.assertEqual(f, [])

    def test_list_item_bold_header_no_overlap(self):
        # bold_inline_header_in_list ловит «- **X**: …» — наш чек этот случай не дублирует.
        text = "- **Скорость**: всё быстро"
        f = lint_check(text, "bold_in_prose_with_epithet")
        self.assertEqual(f, [])


class TestPhase2GWarnMarkers(unittest.TestCase):
    """Phase 2G: new TOML phrases — evaluation-without-proof + corporate-research."""

    def test_znachitelno_uproshchayut_warns(self):
        text = "Эти функции значительно упрощают работу с данными."
        f = lint_check(text, "no_warn_markers")
        names = {x.match for x in f}
        self.assertIn("значительно упрощают", names)

    def test_kachestvennykh_ploshchadkakh_warns(self):
        text = "Размещения на качественных площадках дают результат."
        f = lint_check(text, "no_warn_markers")
        names = {x.match for x in f}
        self.assertIn("качественных площадках", names)

    def test_klyuchevye_dannye_i_insighty_warns(self):
        text = "Ниже — ключевые данные и инсайты для маркетологов."
        f = lint_check(text, "no_warn_markers")
        names = {x.match for x in f}
        self.assertIn("ключевые данные и инсайты", names)

    def test_strategicheskiy_kanal_warns(self):
        text = "Линкбилдинг закрепился как стратегический канал привлечения."
        f = lint_check(text, "no_warn_markers")
        names = {x.match for x in f}
        # Either «стратегический канал» or «закрепился как стратегический» (or both).
        self.assertTrue(
            "стратегический канал" in names
            or "закрепился как стратегический" in names
        )

    def test_pokazatel_zrelosti_rynka_warns(self):
        text = "Это показатель зрелости рынка."
        f = lint_check(text, "no_warn_markers")
        names = {x.match for x in f}
        self.assertIn("показатель зрелости рынка", names)


if __name__ == "__main__":
    unittest.main()
