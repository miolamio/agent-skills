# Agent Skills by @miolamio

A collection of agent skills for Russian text processing, translation, and automation tools.

Compatible with [Claude Code](https://claude.com/claude-code), [Cursor](https://cursor.com), [Gemini CLI](https://github.com/google-gemini/gemini-cli), [Codex](https://github.com/openai/codex), and other tools supporting the [Agent Skills](https://agentskills.io) standard.

---

## Installation

### Option 1: Plugin Marketplace (Claude Code)

```bash
/plugin marketplace add miolamio/agent-skills
```

Then install individual skills:

```bash
/plugin install ru-editor@miolamio-agent-skills
/plugin install en-ru-translator-adv@miolamio-agent-skills
/plugin install ru-textovod@miolamio-agent-skills
/plugin install ascii-art-beautifier@miolamio-agent-skills
/plugin install telegram-cli@miolamio-agent-skills
```

### Option 2: Universal Installer

```bash
npx skills-installer install @miolamio/agent-skills/ru-editor
```

### Option 3: Manual

Clone and copy the skill you need:

```bash
git clone https://github.com/miolamio/agent-skills.git
```

For all projects (personal scope):

```bash
cp -r agent-skills/skills/ru-editor ~/.claude/skills/
```

For a specific project:

```bash
cp -r agent-skills/skills/ru-editor /path/to/project/.claude/skills/
```

Claude Code picks up new skills automatically -- no restart needed.

### Updating

Plugin marketplace:

```bash
/plugin marketplace update miolamio-agent-skills
claude plugin update ru-editor@miolamio-agent-skills
```

Manual: `git pull` and copy again.

---

## Skills

### en-ru-translator-adv `v3.3.0`

Professional English-to-Russian translator with a three-step agentic workflow: translate, reflect, refine. The result reads as if originally written in Russian.

**Features:**
- Technical documentation, marketing materials, articles, UI strings, educational content
- [Informational style](https://bureau.ru/projects/book-pishi-sokrashchay/) by Maxim Ilyahov
- Cleans up calques, bureaucratese, stop words, and machine translation markers
- Consistent glossary management
- Russian typography: guillemets, em dashes, lists, letter "yo"

**Triggers:** "translate to Russian", "EN-RU", "переведи на русский"

---

### ru-editor `v2.1.0`

Russian text editor. Transforms AI-generated or bureaucratic text into natural, idiomatic Russian. Three-step workflow: edit (15 operations), self-check (16 checks), final polish.

**Features:**
- Removes AI markers: ChatGPT-isms, repetitive structure, synonym triples
- Cleans stop words, empty evaluations, bureaucratese, nominalizations
- Replaces pretentious words with simple ones
- Fixes typography: guillemets, em dashes, lists, letter "yo"

**Triggers:** "отредактируй", "причеши текст", "убери ИИ-шность", "инфостиль"

---

### ru-textovod `v1.0.0`

Russian spelling, punctuation, and grammar checker via [Textovod.com](https://textovod.com) API.

**Features:**
- Neural autocorrection (grammar + spelling + punctuation in one pass)
- Separate spelling check with suggestions
- Separate punctuation check
- Verbose and quick output modes

**Requires:** `TEXTOVOD_USER_ID`, `TEXTOVOD_API_KEY`, `TEXTOVOD_API2_TOKEN` environment variables.

**Triggers:** "проверь текст", "проверь орфографию", "автокоррекция"

---

### ascii-art-beautifier `v1.2.0`

Beautifies and generates ASCII art diagrams in markdown files. Uses Unicode box-drawing characters, validates alignment, symmetry, and padding.

**Features:**
- Beautify mode: fixes existing ASCII blocks in a file
- Generate mode: creates new diagrams from text descriptions
- Python validator (`validate_ascii_art.py`) for automated checks

**Triggers:** "beautify ascii", "fix ascii art", "align ascii", "выровняй разметку"

---

### telegram-cli `v1.0.0`

Telegram client for Claude Code. Send and read messages, search chats, download media, manage contacts -- all from the terminal.

**Requires:** `npm install -g @miolamio/tg-cli`

**Features:**
- Messages: read, send, search, forward, reactions, polls
- Chats: list, info, members, forum topics
- Media: download and upload files
- Output modes: `--json`, `--toon` (saves 30-40% tokens), `--human`

**Triggers:** "send telegram message", "read telegram", "tg"

---

## Author

Anthony Vdovitchenko ([@aiwizards](https://t.me/aiwizards))

## License

MIT
