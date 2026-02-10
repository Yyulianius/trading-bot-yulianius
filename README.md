# UniversalTradingBot для Render.com

Упрощённая версия Telegram торгового бота для Render.com.

## Особенности
- Работает на Render.com 24/7
- Flask health checks для предотвращения простоя
- Автоматические демо-сигналы
- Постоянная клавиатура в Telegram
- Поддержка XAUUSD, EURUSD, GBPUSD

## Установка на Render
1. Подключите этот репозиторий к Render
2. Добавьте переменные окружения:
   - `TELEGRAM_TOKEN` - токен вашего бота
   - `TELEGRAM_CHAT_ID` - ваш chat ID (1037258513)
3. Нажмите Deploy

## Команды Telegram
- `/start` - активация бота
- `/status` - статус системы
- `/test` - тестовый сигнал
- `/signal` - проверка всех инструментов