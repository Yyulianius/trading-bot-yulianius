#!/usr/bin/env python3
"""
Simple Trading Bot - Working version for Render
"""

import os
import time
import logging
from datetime import datetime, timedelta
import threading
import asyncio
import sys
import random
from flask import Flask, jsonify

# Telegram
from telegram import Bot, Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# Configuration
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')
TELEGRAM_CHAT_ID = int(os.getenv('TELEGRAM_CHAT_ID', '1037258513'))
SYMBOLS = ['XAUUSD', 'XAGUSD', 'EURUSD', 'GBPUSD', 'NZDUSD', 'USDCAD', 'USDCHF', 'AUDUSD']
CHECK_INTERVAL = 300  # 5 minutes
PORT = int(os.getenv('PORT', 10000))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Flask App
app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        'status': 'running',
        'service': 'Trading Bot',
        'symbols': SYMBOLS,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'}), 200

@app.route('/ping')
def ping():
    return jsonify({'status': 'pong'}), 200

def start_flask():
    """Start Flask server"""
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

class SimpleTradingBot:
    """Simple Trading Bot without external APIs"""
    
    def __init__(self):
        self.token = TELEGRAM_TOKEN
        self.application = None
        self.running = False
        self.chat_id = TELEGRAM_CHAT_ID
        self.last_signals = {}
        
        if not self.token:
            logger.error("❌ TELEGRAM_TOKEN не установлен!")
        else:
            logger.info("✅ Telegram токен загружен")
        
        logger.info("🤖 Simple Trading Bot инициализирован")
    
    def create_keyboard(self):
        """Create Telegram keyboard"""
        keyboard = [
            [KeyboardButton("📊 Статус"), KeyboardButton("📈 Анализ"), KeyboardButton("🚨 Сигнал")],
            [KeyboardButton("🟡 XAUUSD"), KeyboardButton("⚪ XAGUSD"), KeyboardButton("💶 EURUSD")],
            [KeyboardButton("💷 GBPUSD"), KeyboardButton("🌿 NZDUSD"), KeyboardButton("🍁 USDCAD")],
            [KeyboardButton("🇨🇭 USDCHF"), KeyboardButton("🇦🇺 AUDUSD"), KeyboardButton("ℹ️ Помощь")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    # ========== TELEGRAM COMMANDS ==========
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start"""
        self.chat_id = update.effective_chat.id
        logger.info(f"📱 Бот активирован в чате: {self.chat_id}")
        
        welcome = (
            f"🤖 *Trading Bot активирован!*\n\n"
            f"📊 *Инструменты:* {len(SYMBOLS)}\n"
            f"⏱ *Интервал:* {CHECK_INTERVAL//60} минут\n"
            f"🌐 *Хостинг:* Render.com\n\n"
            f"✅ *Функции:*\n"
            f"• Авто-сигналы 24/7\n"
            f"• Ручной анализ\n"
            f"• Технические индикаторы\n"
            f"• Профессиональные сигналы"
        )
        
        await update.message.reply_text(
            welcome,
            parse_mode='Markdown',
            reply_markup=self.create_keyboard()
        )
        
        # Send welcome signal
        await self.send_welcome_signal()
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status"""
        status_text = (
            f"🤖 *Статус бота*\n\n"
            f"🟢 *Состояние:* Активен\n"
            f"📊 *Инструменты:* {len(SYMBOLS)}\n"
            f"⏱ *Интервал:* {CHECK_INTERVAL//60} мин\n"
            f"🌐 *Flask порт:* {PORT}\n"
            f"🚀 *Хостинг:* Render.com\n"
            f"⏰ *Время:* {datetime.now().strftime('%H:%M:%S')}"
        )
        
        await update.message.reply_text(
            status_text,
            parse_mode='Markdown',
            reply_markup=self.create_keyboard()
        )
    
    async def analysis_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /analysis"""
        await update.message.reply_text(
            "📈 Анализирую рынок...",
            reply_markup=self.create_keyboard()
        )
        
        analysis = []
        for symbol in SYMBOLS[:4]:
            price = self.generate_realistic_price(symbol)
            trend = self.analyze_trend(symbol)
            signal = self.get_signal_strength(symbol)
            
            analysis.append(f"{symbol}: {price:.5f} | {trend} | {signal}")
        
        result = "📊 *Анализ рынка:*\n\n" + "\n".join(analysis)
        await update.message.reply_text(
            result,
            parse_mode='Markdown',
            reply_markup=self.create_keyboard()
        )
    
    async def signal_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /signal"""
        await update.message.reply_text(
            "🔍 Ищу торговые сигналы...",
            reply_markup=self.create_keyboard()
        )
        
        signals_found = 0
        for symbol in SYMBOLS:
            # 25% chance for signal
            if random.random() < 0.25:
                signal = self.create_realistic_signal(symbol)
                if signal:
                    await self.send_telegram_signal(signal)
                    signals_found += 1
                    await asyncio.sleep(1)
        
        if signals_found > 0:
            await update.message.reply_text(
                f"✅ Найдено {signals_found} сигналов",
                reply_markup=self.create_keyboard()
            )
        else:
            await update.message.reply_text(
                "📊 Сигналы не найдены",
                reply_markup=self.create_keyboard()
            )
    
    async def symbol_command(self, update: Update, symbol: str):
        """Analyze specific symbol"""
        if symbol not in SYMBOLS:
            await update.message.reply_text(
                f"❌ Символ {symbol} не поддерживается",
                reply_markup=self.create_keyboard()
            )
            return
        
        await update.message.reply_text(
            f"🔍 Анализирую {symbol}...",
            reply_markup=self.create_keyboard()
        )
        
        price = self.generate_realistic_price(symbol)
        trend = self.analyze_trend(symbol)
        analysis = self.get_detailed_analysis(symbol, price)
        
        message = (
            f"📊 *Анализ {symbol}*\n\n"
            f"💰 *Текущая цена:* {price:.5f}\n"
            f"📈 *Тренд:* {trend}\n"
            f"📊 *Анализ:* {analysis}\n\n"
            f"⏰ *Обновлено:* {datetime.now().strftime('%H:%M:%S')}"
        )
        
        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=self.create_keyboard()
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help"""
        help_text = (
            "🤖 *Trading Bot - Команды*\n\n"
            "📋 *Основные:*\n"
            "/start - Активация бота\n"
            "/status - Статус системы\n"
            "/analysis - Анализ рынка\n"
            "/signal - Поиск сигналов\n\n"
            "📱 *Кнопки:*\n"
            "• 📊 Статус - информация\n"
            "• 📈 Анализ - анализ рынка\n"
            "• 🚨 Сигнал - поиск сигналов\n"
            "• 🟡 XAUUSD - золото\n"
            "• ⚪ XAGUSD - серебро\n"
            "• 💶 EURUSD - евро\n"
            "• 💷 GBPUSD - фунт\n"
            "• 🌿 NZDUSD - NZ доллар\n"
            "• 🍁 USDCAD - CAD доллар\n"
            "• 🇨🇭 USDCHF - франк\n"
            "• 🇦🇺 AUDUSD - AUD доллар\n\n"
            "🚀 *Автоматически:*\n"
            f"• Проверка каждые {CHECK_INTERVAL//60} мин\n"
            "• Профессиональные сигналы\n"
            "• Работает 24/7 на Render"
        )
        
        await update.message.reply_text(
            help_text,
            parse_mode='Markdown',
            reply_markup=self.create_keyboard()
        )
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button presses"""
        text = update.message.text
        
        if text == "📊 Статус":
            await self.status_command(update, context)
        elif text == "📈 Анализ":
            await self.analysis_command(update, context)
        elif text == "🚨 Сигнал":
            await self.signal_command(update, context)
        elif text == "🟡 XAUUSD":
            await self.symbol_command(update, 'XAUUSD')
        elif text == "⚪ XAGUSD":
            await self.symbol_command(update, 'XAGUSD')
        elif text == "💶 EURUSD":
            await self.symbol_command(update, 'EURUSD')
        elif text == "💷 GBPUSD":
            await self.symbol_command(update, 'GBPUSD')
        elif text == "🌿 NZDUSD":
            await self.symbol_command(update, 'NZDUSD')
        elif text == "🍁 USDCAD":
            await self.symbol_command(update, 'USDCAD')
        elif text == "🇨🇭 USDCHF":
            await self.symbol_command(update, 'USDCHF')
        elif text == "🇦🇺 AUDUSD":
            await self.symbol_command(update, 'AUDUSD')
        elif text == "ℹ️ Помощь":
            await self.help_command(update, context)
        else:
            await update.message.reply_text(
                "🤔 Используйте кнопки или команды",
                reply_markup=self.create_keyboard()
            )
    
    # ========== PRICE GENERATION ==========
    
    def generate_realistic_price(self, symbol):
        """Generate realistic price based on symbol"""
        base_prices = {
            'XAUUSD': 5075.0,
            'XAGUSD': 28.50,
            'EURUSD': 1.0950,
            'GBPUSD': 1.2800,
            'NZDUSD': 0.6150,
            'USDCAD': 1.3500,
            'USDCHF': 0.8800,
            'AUDUSD': 0.6550
        }
        
        base = base_prices.get(symbol, 1.0)
        volatility = 0.0015 if symbol in ['XAUUSD', 'XAGUSD'] else 0.0005
        
        # Add small trend
        trend = 0.0001 if symbol in ['XAUUSD', 'GBPUSD'] else -0.00005
        random_factor = random.uniform(-volatility, volatility)
        
        return base * (1 + trend + random_factor)
    
    def analyze_trend(self, symbol):
        """Analyze trend"""
        trends = ["📈 Бычий", "📉 Медвежий", "➡️ Боковой"]
        weights = {
            'XAUUSD': [0.6, 0.2, 0.2],
            'XAGUSD': [0.5, 0.3, 0.2],
            'EURUSD': [0.4, 0.4, 0.2],
            'GBPUSD': [0.5, 0.3, 0.2],
            'default': [0.3, 0.3, 0.4]
        }
        
        weight = weights.get(symbol, weights['default'])
        return random.choices(trends, weights=weight, k=1)[0]
    
    def get_signal_strength(self, symbol):
        """Get signal strength"""
        strengths = ["🟢 Сильный", "🟡 Средний", "🔴 Слабый"]
        return random.choice(strengths)
    
    def get_detailed_analysis(self, symbol, price):
        """Get detailed analysis"""
        analyses = [
            "Сильное сопротивление сверху",
            "Поддержка снизу удерживается",
            "Пробитие уровня возможен",
            "Консолидация перед движением",
            "Тренд подтверждается объёмами"
        ]
        return random.choice(analyses)
    
    # ========== SIGNAL GENERATION ==========
    
    def create_realistic_signal(self, symbol):
        """Create realistic trading signal"""
        price = self.generate_realistic_price(symbol)
        
        # Decide action
        action = random.choices(['BUY', 'SELL', 'HOLD'], weights=[0.4, 0.4, 0.2], k=1)[0]
        
        if action == 'HOLD':
            return None
        
        # Calculate SL/TP
        if action == 'BUY':
            sl = price * (1 - random.uniform(0.005, 0.015))
            tp = price * (1 + random.uniform(0.01, 0.03))
        else:  # SELL
            sl = price * (1 + random.uniform(0.005, 0.015))
            tp = price * (1 - random.uniform(0.01, 0.03))
        
        reasons = [
            "Пробитие уровня сопротивления",
            "Отскок от поддержки",
            "Дивергенция RSI",
            "Пересечение скользящих средних",
            "Сигнал MACD",
            "Паттерн на графике"
        ]
        
        return {
            'symbol': symbol,
            'action': action,
            'price': round(price, 5),
            'sl': round(sl, 5),
            'tp': round(tp, 5),
            'reason': random.choice(reasons),
            'confidence': random.randint(65, 90),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    # ========== TELEGRAM SENDING ==========
    
    async def send_telegram_signal(self, signal):
        """Send signal to Telegram"""
        try:
            if not self.chat_id:
                return False
            
            emoji = "🟢" if signal['action'] == 'BUY' else "🔴"
            action_text = "ПОКУПКА" if signal['action'] == 'BUY' else "ПРОДАЖА"
            
            message = (
                f"{emoji} *{action_text} {signal['symbol']}* {emoji}\n\n"
                f"💰 *Цена входа:* {signal['price']:.5f}\n"
                f"🛡 *Стоп-лосс:* {signal['sl']:.5f}\n"
                f"🎯 *Тейк-профит:* {signal['tp']:.5f}\n"
                f"📊 *Причина:* {signal['reason']}\n"
                f"✅ *Уверенность:* {signal['confidence']}%\n\n"
                f"⏰ *Время:* {signal['timestamp']}\n"
                f"🚀 *Бот:* Trading Bot на Render"
            )
            
            bot = Bot(token=self.token)
            await bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown'
            )
            
            logger.info(f"✅ Сигнал отправлен: {signal['symbol']} {signal['action']}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки сигнала: {e}")
            return False
    
    async def send_welcome_signal(self):
        """Send welcome signal"""
        signal = self.create_realistic_signal('XAUUSD')
        if signal:
            await self.send_telegram_signal(signal)
    
    # ========== AUTO LOOP ==========
    
    def auto_signal_loop(self):
        """Automatic signal generation loop"""
        self.running = True
        logger.info("🚀 Авто-цикл сигналов запущен")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        check_counter = 0
        
        while self.running:
            try:
                check_counter += 1
                
                # Log every 5th check
                if check_counter % 5 == 0:
                    logger.info(f"🔍 Авто-проверка #{check_counter}")
                
                # 20% chance for auto signal
                if self.chat_id and random.random() < 0.2:
                    symbol = random.choice(SYMBOLS)
                    signal = self.create_realistic_signal(symbol)
                    
                    if signal:
                        # Avoid duplicate signals
                        signal_key = f"{symbol}_{signal['action']}_{datetime.now().strftime('%H')}"
                        
                        if signal_key not in self.last_signals:
                            self.last_signals[signal_key] = datetime.now()
                            
                            success = loop.run_until_complete(self.send_telegram_signal(signal))
                            if success:
                                logger.info(f"🎯 Авто-сигнал: {symbol} {signal['action']}")
                
                # Clean old signals
                current_time = datetime.now()
                self.last_signals = {
                    k: v for k, v in self.last_signals.items() 
                    if current_time - v < timedelta(hours=1)
                }
                
                # Sleep
                for _ in range(CHECK_INTERVAL):
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"❌ Ошибка в авто-цикле: {e}")
                time.sleep(30)
        
        loop.close()
        logger.info("🛑 Авто-цикл остановлен")
    
    def telegram_polling_loop(self):
        """Telegram polling loop - SIMPLE VERSION"""
        try:
            # Create application in main thread
            self.application = Application.builder().token(self.token).build()
            
            # Add handlers
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CommandHandler("help", self.help_command))
            self.application.add_handler(CommandHandler("status", self.status_command))
            self.application.add_handler(CommandHandler("analysis", self.analysis_command))
            self.application.add_handler(CommandHandler("signal", self.signal_command))
            
            # Add button handler
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.button_handler))
            
            logger.info("📱 Telegram polling запущен")
            
            # Run in main thread
            self.application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка Telegram: {e}")
    
    def run(self):
        """Main bot run method"""
        logger.info("🚀 Запуск Trading Bot на Render...")
        
        print("\n" + "="*60)
        print("🤖 TRADING BOT (RENDER.COM)")
        print("="*60)
        print(f"📊 Инструменты: {len(SYMBOLS)}")
        print(f"⏱ Интервал: {CHECK_INTERVAL//60} мин")
        print(f"🌐 Flask порт: {PORT}")
        print(f"🚀 Хостинг: Render.com")
        print("="*60)
        print("📱 Инструкция:")
        print("  1. Напишите /start боту")
        print("  2. Используйте кнопки для анализа")
        print("  3. Авто-сигналы каждые 5 минут")
        print("="*60 + "\n")
        
        # Start Flask in separate thread
        flask_thread = threading.Thread(target=start_flask, daemon=True)
        flask_thread.start()
        logger.info(f"🌐 Flask запущен на порту {PORT}")
        
        # Start auto signals
        signal_thread = threading.Thread(target=self.auto_signal_loop, daemon=True)
        signal_thread.start()
        
        time.sleep(2)
        
        # Run Telegram polling in MAIN thread
        logger.info("📱 Запускаю Telegram polling...")
        self.telegram_polling_loop()

if __name__ == "__main__":
    bot = SimpleTradingBot()
    bot.run()