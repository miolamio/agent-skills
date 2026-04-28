# Как настроить CI/CD за 30 минут

В этом руководстве разберём настройку полноценного CI/CD-пайплайна с нуля.

## Что нам понадобится

Для прохождения этого туториала нужны минимальные знания:

- Базовое понимание Git и GitHub.
- Опыт работы с командной строкой.
- Установленный Node.js версии 18+.
- Аккаунт на GitHub (бесплатный подойдёт).

## Шаг 1: создаём репозиторий

Если у вас нет существующего проекта, создайте новый — это займёт минуту:

```bash
mkdir my-awesome-project
cd my-awesome-project
git init
```

## Шаг 2: GitHub Actions

GitHub Actions использует YAML-файлы в директории `.github/workflows/`. Создадим первый workflow:

```yaml
name: CI Pipeline
on:
  push:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm test
```

Это минимальная конфигурация. В production обычно добавляют больше шагов.

## Шаг 3: деплой

Автоматический деплой:

```yaml
deploy:
  needs: test
  runs-on: ubuntu-latest
  steps:
    - run: npx vercel --token ${{ secrets.VERCEL_TOKEN }}
```

Секреты нужно настроить в разделе Settings, подраздел Secrets.

## Готово

Вы настроили полноценный CI/CD-пайплайн. Дальше можно добавить:

- Покрытие тестами с Codecov.
- Сканирование безопасности с Snyk.
- Тесты производительности с Lighthouse CI.
- Канареечные релизы.
