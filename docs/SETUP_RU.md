# Установка Free v4 — пошагово

## 1. GitHub

Создай **Public** repository, например `nq-market-ai-agent`.

Почему Public: GitHub Free даёт бесплатное/неограниченное использование стандартных GitHub-hosted runners в public repositories. В private repository на GitHub Free есть месячный лимит минут, которого не хватит для каждых 5 минут.

## 2. Загрузка

Загрузи ВСЕ файлы архива с сохранением папки `.github/workflows`.

## 3. Telegram

В Telegram открой `@BotFather` → `/newbot` → создай бота.

Скопируй Bot Token.

Напиши своему новому боту `/start`.

Для Chat ID можно временно открыть в браузере:

`https://api.telegram.org/bot<TOKEN>/getUpdates`

Найди `message.chat.id`. После получения ID не публикуй этот URL и токен.

## 4. Secrets

GitHub → repository → Settings → Secrets and variables → Actions → New repository secret.

Создай:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Токены НЕ загружай в репозиторий.

## 5. Manual Test

Actions → Manual Test → Run workflow.

В Telegram должно прийти:

`NQ Market AI Free v4: Telegram connection test successful.`

## 6. Автоматическая работа

После успешного теста workflow `NQ Market Monitor` будет запускаться каждые 5 минут.

Не устанавливай self-hosted runner на свой компьютер.
