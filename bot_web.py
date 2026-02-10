#!/usr/bin/env python3
"""
UniversalTradingBot - Упрощённая версия для Render без проблемных зависимостей
"""

import os
import time
import logging
import random
from datetime import datetime
from flask import Flask, jsonify
from telegram import Bot, Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import threading
import asyncio
import sys
import json

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Конфигурация
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '1037258513')
SYMBOLS = ['XAUUSD', 'EURUSD', 'GBPUSD']
CHECK_INTERVAL = 300  # 5 минут
PORT = int(os.getenv('PORT', 10000))

# Flask приложение
app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        'status': 'running',
        'service': 'UniversalTradingBot',
        'version': '2.0.1-simple',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'python': sys.version.split()[0]
    }), 200

@app.route('/ping')
def ping():
    return jsonify({'status': 'pong'}), 200

def start_flask():
    """Запуск Flask сервера"""
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

class UniversalTradingBot:
    def __init__(self):
        self.token = TELEGRAM_TOKEN
        self.application = None
        self.running = False
        self.chat_id = int(TELEGRAM_CHAT_ID) if TELEGRAM_CHAT_ID else None
        
        if not self.token:
            logger.error("❌ TELEGRAM_TOKEN не установлен!")
        else:
            logger.info("✅ Telegram токен загружен")
        
        logger.info("🤖 Бот инициализирован (упрощённая версия)")
    
    def create_main_keyboard(self):
        """Создаёт клавиатуру"""
        keyboard = [
            [KeyboardButton("📊 Статус"), KeyboardButton("🧪 Тест"), KeyboardButton("🚨 Сигнал")],
            [KeyboardButton("🟡 XAUUSD"), KeyboardButton("💶 EURUSD"), KeyboardButton("💷 GBPUSD")],
            [KeyboardButton("ℹ️ Помощь"), KeyboardButton("🔄 Обновить")]
        ]
        return ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            is_persistent=True
        )
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        self.chat_id = update.effective_chat.id
        logger.info(f"Бот активирован в чате: {self.chat_id}")
        
        welcome_text = (
            "🤖 *UniversalTradingBot активирован!*\n\n"
            "🚀 *Версия:* Упрощённая (без pandas/TA-Lib)\n"
            "📊 *Инструменты:* XAUUSD, EURUSD, GBPUSD\n"
            "⏱ *Интервал проверки:* 5 минут\n"
            "🌐 *Хостинг:* Render.com\n"
            "✅ *Flask keep-alive:* Включён\n\n"
            "📱 *Используйте кнопки ниже:*"
        )
        
        keyboard = self.create_main_keyboard()
        await update.message.reply_text(
            welcome_text, 
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /status"""
        status_text = (
            "🤖 *Статус бота:* 🟢 АКТИВЕН\n\n"
            f"📊 *Инструменты:* {', '.join(SYMBOLS)}\n"
            f"⏱ *Интервал проверки:* {CHECK_INTERVAL} сек\n"
            f"🌐 *Flask порт:* {PORT}\n"
            f"🚀 *Хостинг:* Render.com\n"
            f"⏰ *Последняя проверка:* {datetime.now().strftime('%H:%M:%S')}"
        )
        
        keyboard = self.create_main_keyboard()
        await update.message.reply_text(
            status_text, 
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    
    async def test_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /test"""
        keyboard = self.create_main_keyboard()
        
        test_signal = {
            'symbol': 'XAUUSD',
            'action': 'BUY',
            'price': round(random.uniform(5050, 5100), 2),
            'sl': round(random.uniform(5000, 5040), 2),
            'tp': round(random.uniform(5150, 5200), 2),
            'reason': 'Тестовый сигнал - бот работает на Render!',
            'timestamp': datetime.now().strftime('%H:%M:%S')
        }
        
        emoji = "🟢" if test_signal['action'] == 'BUY' else "🔴"
        action_text = "ПОКУПКА" if test_signal['action'] == 'BUY' else "ПРОДАЖА"
        
        message = (
            f"{emoji} *{action_text} {test_signal['symbol']}* {emoji}\n\n"
            f"📍 *Цена входа:* {test_signal['price']:.2f}\n"
            f"🛡 *Стоп-лосс:* {test_signal['sl']:.2f}\n"
            f"🎯 *Тейк-профит:* {test_signal['tp']:.2f}\n"
            f"📊 *Причина:* {test_signal['reason']}\n\n"
            f"⏰ *Время:* {test_signal['timestamp']}\n"
            f"🚀 *Хостинг:* Render.com\n"
            f"🔧 *Режим:* ТЕСТ (без TA-Lib)"
        )
        
        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = (
            "🤖 *UniversalTradingBot на Render.com*\n\n"
            "📋 *Доступные команды:*\n\n"
            "🚀 /start - активация бота\n"
            "📊 /status - статус системы\n"
            "🎯 /test - тестовый сигнал\n"
            "🔍 /signal - проверить все инструменты\n\n"
            "📱 *Кнопки быстрого доступа:*\n"
            "• 📊 Статус - информация о боте\n"
            "• 🧪 Тест - тестовый сигнал\n"
            "• 🚨 Сигнал - проверка всех инструментов\n"
            "• 🟡 XAUUSD - быстрый доступ к золоту\n"
            "• 💶 EURUSD - быстрый доступ к евро\n"
            "• 💷 GBPUSD - быстрый доступ к фунту\n\n"
            "🌐 *Health check:*\n"
            "https://ваш-сервис.onrender.com/health"
        )
        
        keyboard = self.create_main_keyboard()
        await update.message.reply_text(
            help_text, 
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    
    async def signal_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /signal"""
        keyboard = self.create_main_keyboard()
        await update.message.reply_text(
            "🔍 Проверяю инструменты...",
            reply_markup=keyboard
        )
        
        signals_found = 0
        for symbol in SYMBOLS:
            try:
                # Генерация случайного сигнала для демо
                if random.random() > 0.5:  # 50% шанс на сигнал
                    action = random.choice(['BUY', 'SELL'])
                    price = random.uniform(5000, 5100) if symbol == 'XAUUSD' else random.uniform(1.05, 1.15)
                    
                    signal = {
                        'symbol': symbol,
                        'action': action,
                        'price': round(price, 2),
                        'sl': round(price * 0.99, 2),
                        'tp': round(price * 1.02, 2),
                        'reason': 'Демо-сигнал от Render бота',
                        'timestamp': datetime.now().strftime('%H:%M:%S')
                    }
                    
                    emoji = "🟢" if action == 'BUY' else "🔴"
                    action_text = "ПОКУПКА" if action == 'BUY' else "ПРОДАЖА"
                    
                    message = (
                        f"{emoji} *{action_text} {symbol}* {emoji}\n"
                        f"📍 *Цена:* {signal['price']:.2f}\n"
                        f"📊 *Причина:* {signal['reason']}\n"
                        f"⏰ *Время:* {signal['timestamp']}"
                    )
                    
                    bot = Bot(token=self.token)
                    await bot.send_message(
                        chat_id=self.chat_id,
                        text=message,
                        parse_mode='Markdown'
                    )
                    
                    signals_found += 1
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"Ошибка проверки {symbol}: {e}")
        
        if signals_found > 0:
            await update.message.reply_text(
                f"✅ Найдено {signals_found} демо-сигналов",
                reply_markup=keyboard
            )
        else:
            await update.message.reply_text(
                "📊 Сигналы не найдены в этой проверке",
                reply_markup=keyboard
            )
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на кнопки"""
        text = update.message.text
        
        if text == "📊 Статус":
            await self.status_command(update, context)
        elif text == "🧪 Тест":
            await self.test_command(update, context)
        elif text == "🚨 Сигнал":
            await self.signal_command(update, context)
        elif text == "🟡 XAUUSD":
            await update.message.reply_text(
                "🟡 XAUUSD (золото)\n"
                "💎 Демо-цена: 5075.50\n"
                "📊 Статус: НЕТ СИГНАЛА\n"
                "⏰ Следующая проверка: через 5 мин",
                reply_markup=self.create_main_keyboard()
            )
        elif text == "💶 EURUSD":
            await update.message.reply_text(
                "💶 EURUSD (евро/доллар)\n"
                "💎 Демо-цена: 1.09550\n"
                "📊 Статус: НЕТ СИГНАЛА\n"
                "⏰ Следующая проверка: через 5 мин",
                reply_markup=self.create_main_keyboard()
            )
        elif text == "💷 GBPUSD":
            await update.message.reply_text(
                "💷 GBPUSD (фунт/доллар)\n"
                "💎 Демо-цена: 1.28050\n"
                "📊 Статус: НЕТ СИГНАЛА\n"
                "⏰ Следующая проверка: через 5 мин",
                reply_markup=self.create_main_keyboard()
            )
        elif text == "ℹ️ Помощь":
            await self.help_command(update, context)
        elif text == "🔄 Обновить":
            keyboard = self.create_main_keyboard()
            await update.message.reply_text(
                "✅ Интерфейс обновлен!",
                reply_markup=keyboard
            )
        else:
            await update.message.reply_text(
                "🤔 Используйте кнопки меню или команды",
                reply_markup=self.create_main_keyboard()
            )
    
    def analysis_loop(self):
        """Цикл анализа (упрощённый)"""
        self.running = True
        logger.info("🚀 Цикл анализа запущен")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        check_counter = 0
        
        while self.running:
            try:
                check_counter += 1
                if check_counter % 10 == 0:
                    logger.info(f"🔍 Проверка #{check_counter}")
                
                if self.chat_id and random.random() > 0.8:  # 20% шанс на сигнал
                    symbol = random.choice(SYMBOLS)
                    action = random.choice(['BUY', 'SELL'])
                    
                    signal = {
                        'symbol': symbol,
                        'action': action,
                        'price': round(random.uniform(5000, 5100), 2) if symbol == 'XAUUSD' else round(random.uniform(1.05, 1.15), 5),
                        'reason': 'Автоматический демо-сигнал',
                        'timestamp': datetime.now().strftime('%H:%M:%S')
                    }
                    
                    emoji = "🟢" if action == 'BUY' else "🔴"
                    action_text = "ПОКУПКА" if action == 'BUY' else "ПРОДАЖА"
                    
                    message = (
                        f"{emoji} *{action_text} {signal['symbol']}* {emoji}\n\n"
                        f"📍 *Цена входа:* {signal['price']:.2f}\n"
                        f"📊 *Причина:* {signal['reason']}\n\n"
                        f"⏰ *Время:* {signal['timestamp']}\n"
                        f"🚀 *Хостинг:* Render.com\n"
                        f"🔧 *Режим:* АВТО-ДЕМО"
                    )
                    
                    bot = Bot(token=self.token)
                    loop.run_until_complete(
                        bot.send_message(
                            chat_id=self.chat_id,
                            text=message,
                            parse_mode='Markdown'
                        )
                    )
                    
                    logger.info(f"🎯 Отправлен автоматический сигнал: {symbol} {action}")
                
                # Спим до следующей проверки
                sleep_counter = 0
                while sleep_counter < CHECK_INTERVAL and self.running:
                    time.sleep(1)
                    sleep_counter += 1
                    
            except Exception as e:
                logger.error(f"❌ Ошибка в цикле анализа: {e}")
                time.sleep(30)
        
        loop.close()
        logger.info("🛑 Цикл анализа остановлен")
    
    def telegram_polling_loop(self):
        """Запуск Telegram polling"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            self.application = Application.builder().token(self.token).build()
            
            # Регистрируем команды
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CommandHandler("help", self.help_command))
            self.application.add_handler(CommandHandler("status", self.status_command))
            self.application.add_handler(CommandHandler("test", self.test_command))
            self.application.add_handler(CommandHandler("signal", self.signal_command))
            
            # Регистрируем обработчик кнопок
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.button_handler))
            
            logger.info("📱 Telegram polling запущен")
            self.application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка Telegram: {e}")
        finally:
            loop.close()
            logger.info("🛑 Telegram polling остановлен")
    
    def run(self):
        """Запуск бота"""
        logger.info("🚀 Запуск UniversalTradingBot на Render.com...")
        
        print("\n" + "="*60)
        print("🤖 UNIVERSAL TRADING BOT (RENDER.COM)")
        print("="*60)
        print(f"📊 Режим: УПРОЩЁННЫЙ (без pandas/TA-Lib)")
        print(f"📈 Инструменты: {', '.join(SYMBOLS)}")
        print(f"⏱ Интервал: {CHECK_INTERVAL} сек")
        print(f"🌐 Flask порт: {PORT}")
        print(f"🚀 Хостинг: Render.com")
        print("="*60)
        print("📱 ИНСТРУКЦИЯ:")
        print("  1. Напишите боту /start")
        print("  2. Используйте кнопки внизу")
        print("  3. Авто-сигналы каждые 5 минут")
        print("="*60 + "\n")
        
        # Запускаем Flask сервер
        flask_thread = threading.Thread(
            target=start_flask,
            daemon=True,
            name="FlaskThread"
        )
        flask_thread.start()
        logger.info(f"🌐 Flask сервер запущен на порту {PORT}")
        
        # Запускаем Telegram бота
        tg_thread = threading.Thread(
            target=self.telegram_polling_loop,
            daemon=True,
            name="TelegramThread"
        )
        tg_thread.start()
        
        time.sleep(2)
        
        # Запускаем анализ
        analysis_thread = threading.Thread(
            target=self.analysis_loop,
            daemon=True,
            name="AnalysisThread"
        )
        analysis_thread.start()
        
        logger.info("✅ Бот успешно запущен!")
        
        # Бесконечный цикл
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.running = False
            print("\n👋 Бот остановлен\n")
            sys.exit(0)

if __name__ == "__main__":
    bot = UniversalTradingBot()
    bot.run()