# Security policy

## Rules

1. Never commit Telegram bot tokens or other credentials.
2. Never use a self-hosted runner on a personal computer for this project.
3. Keep the repository free of personal data.
4. Use GitHub Actions Secrets for credentials.
5. Keep workflow permissions read-only unless a write permission is explicitly needed.
6. Do not add third-party Actions from unknown publishers without reviewing them.
7. The agent should only send messages to the configured Telegram chat.

## If a Telegram token leaks

Immediately revoke/regenerate the bot token with BotFather and replace the GitHub Secret.

## Threat model

GitHub-hosted runners are ephemeral VMs/containers managed by GitHub. The workflow does not have access to the user's PC or phone. The primary secret exposed to the workflow is the Telegram bot credential, so its permissions should remain limited to the bot.
