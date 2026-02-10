#!/usr/bin/env python3
"""
UniversalTradingBot - Версия для деплоя на Render.com с поддержкой Web Service
"""

import os
import time
import logging
from datetime import datetime
import talib
import numpy as np
import pandas as pd
from telegram import Bot, Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import threading
import asyncio
import sys
import random
import hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io

# Для работы как Web Service
from flask import Flask, jsonify
from apscheduler.schedulers.background import BackgroundScheduler

# Импорт конфигурации
try:
    from config import *
except ImportError:
    # Значения по умолчанию для Render
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '0')
    USE_MT5 = False
    USE_DEMO_DATA = True
    TEST_MODE = True
    SYMBOLS = ['XAUUSD', 'EURUSD', 'GBPUSD']
    CHECK_INTERVAL = 300  # 5 минут
    TIMEFRAME_H4 = '4h'
    TIMEFRAME_H1 = '1h'
    EMA_PERIOD = 20
    RSI_PERIOD = 7
    CCI_PERIOD = 14
    ATR_PERIOD = 14
    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70
    CCI_OVERSOLD = -100
    CCI_OVERBOUGHT = 100
    ATR_MIN = 50
    ATR_MAX = 200
    STOP_LOSS_ATR_MULTIPLIER = 1.5
    TAKE_PROFIT_ATR_MULTIPLIER = 2.5
    RISK_REWARD_RATIO = 2.0

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Flask приложение для health checks
app = Flask(__name__)
scheduler = BackgroundScheduler()

# Глобальные переменные для статуса
bot_instance = None
flask_port = int(os.getenv('PORT', 10000))

@app.route('/')
def home():
    """Основной endpoint для проверки работы сервиса"""
    bot_status = "running" if bot_instance and bot_instance.running else "stopped"
    return jsonify({
        'status': 'running',
        'service': 'UniversalTradingBot',
        'version': '2.0.1',
        'bot_status': bot_status,
        'timestamp': datetime.now().isoformat(),
        'endpoints': {
            'health': '/health',
            'status': '/status',
            'ping': '/ping',
            'metrics': '/metrics'
        }
    })

@app.route('/health')
def health():
    """Health check endpoint для Render"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'flask_port': flask_port,
        'python_version': sys.version.split()[0]
    }), 200

@app.route('/status')
def status():
    """Статус бота через HTTP"""
    if bot_instance:
        return jsonify({
            'bot_running': bot_instance.running,
            'telegram_connected': bot_instance.chat_id is not None,
            'check_interval': CHECK_INTERVAL,
            'symbols': SYMBOLS,
            'flask_active': True,
            'timestamp': datetime.now().isoformat()
        })
    return jsonify({
        'bot_running': False,
        'message': 'Bot instance not initialized',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/ping')
def ping():
    """Ping endpoint для поддержания активности"""
    return jsonify({
        'status': 'pong',
        'timestamp': datetime.now().isoformat()
    }), 200

@app.route('/metrics')
def metrics():
    """Метрики системы"""
    import psutil
    return jsonify({
        'cpu_percent': psutil.cpu_percent(),
        'memory_percent': psutil.virtual_memory().percent,
        'disk_usage': psutil.disk_usage('/').percent,
        'timestamp': datetime.now().isoformat()
    })

def keep_alive_ping():
    """Функция для самопинга (вызывается по расписанию)"""
    try:
        if bot_instance and bot_instance.chat_id:
            # Отправляем статус в лог каждые 10 минут
            logger.info(f"✅ Сервис активен. Проверки продолжаются...")
    except Exception as e:
        logger.warning(f"Ошибка в keep_alive_ping: {e}")

def start_scheduler():
    """Запуск планировщика для самопинга"""
    try:
        # Самопинг каждые 5 минут для поддержания активности
        scheduler.add_job(keep_alive_ping, 'interval', minutes=5)
        scheduler.start()
        logger.info("⏰ Планировщик запущен (самопинг каждые 5 минут)")
    except Exception as e:
        logger.error(f"❌ Ошибка запуска планировщика: {e}")

def start_flask():
    """Запуск Flask сервера с обработкой ошибок"""
    try:
        logger.info(f"🌐 Flask сервер запускается на порту {flask_port}...")
        # Отключаем логгирование Flask, чтобы не засорять логи
        import logging as flask_logging
        flask_log = flask_logging.getLogger('werkzeug')
        flask_log.setLevel(flask_logging.WARNING)
        
        app.run(
            host='0.0.0.0',
            port=flask_port,
            debug=False,
            use_reloader=False,
            threaded=True
        )
    except Exception as e:
        logger.error(f"❌ Ошибка запуска Flask: {e}")

class UniversalTradingBot:
    def __init__(self):
        self.token = TELEGRAM_TOKEN
        self.application = None
        self.running = False
        self.chat_id = TELEGRAM_CHAT_ID
        
        # Загружаем chat_id из переменной окружения
        env_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        if env_chat_id and env_chat_id.isdigit():
            self.chat_id = int(env_chat_id)
            logger.info(f"Загружен chat_id из переменной окружения: {self.chat_id}")
        
        # Проверяем токен
        if not self.token:
            logger.error("❌ TELEGRAM_TOKEN не установлен!")
            logger.info("Установите переменную окружения TELEGRAM_TOKEN на Render")
        else:
            logger.info("✅ Telegram токен загружен")
        
        logger.info("🤖 Бот инициализирован для работы на Render")
    
    def create_main_keyboard(self):
        """Создает ПОСТОЯННУЮ клавиатуру внизу экрана"""
        keyboard = [
            [KeyboardButton("📊 Статус"), KeyboardButton("🧪 Тест"), KeyboardButton("🚨 Сигнал")],
            [KeyboardButton("🟡 XAUUSD"), KeyboardButton("💶 EURUSD"), KeyboardButton("💷 GBPUSD")],
            [KeyboardButton("ℹ️ Помощь"), KeyboardButton("🔄 Обновить")]
        ]
        return ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            is_persistent=True,
            input_field_placeholder="Выберите действие или введите команду..."
        )
    
    # ========== TELEGRAM КОМАНДЫ ==========
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        self.chat_id = update.effective_chat.id
        logger.info(f"Бот активирован в чате: {self.chat_id}")
        
        welcome_text = (
            "🤖 *UniversalTradingBot активирован!*\n\n"
            "📊 *Режим:* ДЕМО (тестовые данные)\n\n"
            "📊 *Стратегия:*\n"
            "• Тренд: H4 (цена vs EMA20)\n"
            "• Откаты: H1 (RSI 7, CCI 14)\n"
            "• Фильтр: ATR 50-200\n"
            "• Паттерны: молот, поглощение\n\n"
            "🚀 *Развернут на Render.com*\n"
            "⏰ *Работает 24/7 (Flask keep-alive)*\n\n"
            "📱 *Используйте кнопки ниже:*"
        )
        
        keyboard = self.create_main_keyboard()
        await update.message.reply_text(
            welcome_text, 
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
        # Отправляем приветственный график
        await self.send_welcome_chart(update)
    
    # ... (остальные команды остаются без изменений) ...

    # ========== ЦИКЛ АНАЛИЗА ==========
    
    def analysis_loop(self):
        """Основной цикл анализа"""
        self.running = True
        logger.info("🚀 Цикл анализа запущен на Render")
        
        self.last_signals = {}
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        check_counter = 0
        
        while self.running:
            try:
                check_counter += 1
                current_time = datetime.now().strftime('%H:%M:%S')
                
                # Логируем каждые 10 проверок, чтобы не засорять логи
                if check_counter % 10 == 0:
                    logger.info(f"🔍 Проверка #{check_counter} ({current_time})")
                
                signals_found = 0
                for symbol in SYMBOLS:
                    signal = self.analyze_strategy(symbol)
                    if signal and self.chat_id:
                        signal_key = f"{symbol}_{signal['action']}"
                        current_timestamp = time.time()
                        
                        if signal_key in self.last_signals:
                            time_diff = current_timestamp - self.last_signals[signal_key]
                            if time_diff < 600:
                                continue
                        
                        self.last_signals[signal_key] = current_timestamp
                        
                        data = self.get_market_data(symbol, '1h', 50)
                        
                        success = loop.run_until_complete(
                            self.send_signal_with_chart(signal, data)
                        )
                        
                        if success:
                            signals_found += 1
                            time.sleep(2)
                
                if signals_found == 0:
                    if not self.chat_id:
                        if check_counter % 20 == 0:  # Реже логируем
                            logger.info("📊 Ожидание активации бота (напишите /start в Telegram)")
                    else:
                        # Не логируем каждую проверку без сигналов
                        pass
                else:
                    logger.info(f"🎯 Отправлено {signals_found} сигналов")
                
                # Спим без логирования, чтобы не засорять логи
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
            self.application.add_handler(CommandHandler("chart", self.chart_command))
            
            # Регистрируем обработчик кнопок клавиатуры
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.button_handler))
            
            logger.info("📱 Telegram polling запущен на Render")
            self.application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
                close_loop=False  # Не закрываем loop, чтобы можно было перезапустить
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка Telegram: {e}")
            # Пытаемся переподключиться через 30 секунд
            time.sleep(30)
            self.telegram_polling_loop()
        finally:
            loop.close()
            logger.info("🛑 Telegram polling остановлен")
    
    def run(self):
        """Запуск бота на Render"""
        global bot_instance
        bot_instance = self
        
        logger.info("🚀 Запуск UniversalTradingBot на Render.com...")
        
        print("\n" + "="*70)
        print("🤖 UNIVERSAL TRADING BOT (RENDER.COM)")
        print("="*70)
        print(f"📊 Режим данных: ДЕМО 📊")
        print(f"📈 Инструменты: {', '.join(SYMBOLS)}")
        print(f"⏱ Интервал проверки: {CHECK_INTERVAL} сек")
        print(f"🌐 Flask порт: {flask_port}")
        print(f"🎯 Стратегия: H4 тренд + H1 откаты")
        print(f"📊 Графики: ВКЛЮЧЕНЫ")
        print(f"📱 Клавиатура: ПОСТОЯННАЯ ВНИЗУ")
        print(f"🚀 Хостинг: Render.com")
        print(f"⏰ Режим: 24/7 с Flask keep-alive")
        print("="*70)
        print("📱 ИНСТРУКЦИЯ:")
        print("  1. Откройте Telegram")
        print("  2. Найдите бота")
        print("  3. Напишите /start (ОБЯЗАТЕЛЬНО!)")
        print("  4. Используйте ПОСТОЯННЫЕ кнопки внизу для быстрого доступа!")
        print("="*70)
        print("🌐 Health check: https://your-service.onrender.com/health")
        print("🛑 Сервис автоматически перезапускается на Render")
        print("="*70 + "\n")
        
        # Запускаем планировщик для самопинга
        start_scheduler()
        
        # Запускаем Flask сервер в отдельном потоке
        flask_thread = threading.Thread(
            target=start_flask,
            daemon=True,
            name="FlaskThread"
        )
        flask_thread.start()
        logger.info("✅ Flask сервер запущен для health checks")
        
        # Ждем немного для запуска Flask
        time.sleep(2)
        
        # Запускаем Telegram бота
        tg_thread = threading.Thread(
            target=self.telegram_polling_loop,
            daemon=True,
            name="TelegramThread"
        )
        tg_thread.start()
        
        time.sleep(3)
        
        # Запускаем анализ
        analysis_thread = threading.Thread(
            target=self.analysis_loop,
            daemon=True,
            name="AnalysisThread"
        )
        analysis_thread.start()
        
        logger.info("✅ Бот успешно запущен на Render!")
        logger.info(f"🌐 Health check доступен по порту {flask_port}")
        logger.info("⏰ Самопинг каждые 5 минут для поддержания активности")
        
        # Бесконечный цикл для поддержания работы
        try:
            while True:
                time.sleep(10)
                # Периодически проверяем состояние потоков
                if not flask_thread.is_alive():
                    logger.warning("⚠️ Flask thread остановлен, пытаемся перезапустить...")
                    flask_thread = threading.Thread(
                        target=start_flask,
                        daemon=True,
                        name="FlaskThread"
                    )
                    flask_thread.start()
                    time.sleep(2)
                    
        except KeyboardInterrupt:
            self.running = False
            scheduler.shutdown()
            print("\n" + "="*60)
            print("👋 Бот остановлен")
            print("="*60 + "\n")
            time.sleep(2)
            sys.exit(0)

if __name__ == "__main__":
    bot = UniversalTradingBot()
    bot.run()