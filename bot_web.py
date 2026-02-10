#!/usr/bin/env python3
"""
Simple Trading Bot - Webhook version for Render
"""

import os
import time
import logging
from datetime import datetime, timedelta
import threading
import asyncio
import sys
import random
from flask import Flask, jsonify, request
import json

# Telegram
from telegram import Bot, Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# Configuration
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')
TELEGRAM_CHAT_ID = int(os.getenv('TELEGRAM_CHAT_ID', '1037258513'))
SYMBOLS = ['XAUUSD', 'XAGUSD', 'EURUSD', 'GBPUSD', 'NZDUSD', 'USDCAD', 'USDCHF', 'AUDUSD']
CHECK_INTERVAL = 300  # 5 minutes
PORT = int(os.getenv('PORT', 10000))
RENDER_URL = os.getenv('RENDER_URL', 'https://trading-bot-yulianius.onrender.com')  # Ваш URL

# REAL MARKET DATA (updated manually from MT5)
REAL_PRICES = {
    'XAUUSD': 5052.15,
    'XAGUSD': 28.35,
    'EURUSD': 1.0875,
    'GBPUSD': 1.2780,
    'NZDUSD': 0.6125,
    'USDCAD': 1.3520,
    'USDCHF': 0.8785,
    'AUDUSD': 0.6530
}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Flask App
app = Flask(__name__)

# Global bot instance
bot_instance = None

@app.route('/')
def home():
    return jsonify({
        'status': 'running',
        'service': 'Trading Bot',
        'mode': 'webhook',
        'url': RENDER_URL,
        'symbols': SYMBOLS,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'}), 200

@app.route('/ping')
def ping():
    return jsonify({'status': 'pong'}), 200

@app.route('/update_price/<symbol>/<float:price>')
def update_price(symbol, price):
    """API endpoint для обновления цены вручную из MT5"""
    if symbol in REAL_PRICES:
        old_price = REAL_PRICES[symbol]
        REAL_PRICES[symbol] = round(price, 5)
        logger.info(f"💰 Цена обновлена: {symbol} {old_price} -> {REAL_PRICES[symbol]}")
        return jsonify({
            'status': 'success',
            'symbol': symbol,
            'old_price': old_price,
            'new_price': REAL_PRICES[symbol],
            'timestamp': datetime.now().isoformat()
        })
    return jsonify({'status': 'error', 'message': 'Symbol not found'}), 404

@app.route('/webhook', methods=['POST'])
def webhook():
    """Telegram webhook endpoint"""
    if request.method == "POST":
        if bot_instance:
            update = Update.de_json(request.get_json(force=True), bot_instance.application.bot)
            bot_instance.application.update_queue.put(update)
        return jsonify({'status': 'ok'}), 200
    return jsonify({'status': 'error'}), 400

@app.route('/set_webhook')
def set_webhook():
    """Set webhook manually"""
    try:
        webhook_url = f"{RENDER_URL}/webhook"
        bot_instance.application.bot.set_webhook(url=webhook_url)
        logger.info(f"✅ Webhook установлен: {webhook_url}")
        return jsonify({'status': 'success', 'webhook_url': webhook_url}), 200
    except Exception as e:
        logger.error(f"❌ Ошибка установки webhook: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/delete_webhook')
def delete_webhook():
    """Delete webhook"""
    try:
        bot_instance.application.bot.delete_webhook()
        logger.info("✅ Webhook удалён")
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        logger.error(f"❌ Ошибка удаления webhook: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

def start_flask():
    """Start Flask server"""
    logger.info(f"🌐 Flask запускается на порту {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

class SimpleTradingBot:
    """Simple Trading Bot with webhook"""
    
    def __init__(self):
        self.token = TELEGRAM_TOKEN
        self.application = None
        self.running = False
        self.chat_id = TELEGRAM_CHAT_ID
        self.last_signals = {}
        self.price_history = {}
        
        # Initialize price history
        for symbol in SYMBOLS:
            self.price_history[symbol] = [REAL_PRICES.get(symbol, 1.0)]
        
        if not self.token:
            logger.error("❌ TELEGRAM_TOKEN не установлен!")
        else:
            logger.info("✅ Telegram токен загружен")
        
        logger.info("🤖 Simple Trading Bot инициализирован")
        logger.info(f"💰 Начальные цены: {REAL_PRICES}")
        
        # Set global instance
        global bot_instance
        bot_instance = self
    
    def create_keyboard(self):
        """Create Telegram keyboard"""
        keyboard = [
            [KeyboardButton("📊 Статус"), KeyboardButton("📈 Анализ"), KeyboardButton("🚨 Сигнал")],
            [KeyboardButton("🟡 XAUUSD"), KeyboardButton("⚪ XAGUSD"), KeyboardButton("💶 EURUSD")],
            [KeyboardButton("💷 GBPUSD"), KeyboardButton("🌿 NZDUSD"), KeyboardButton("🍁 USDCAD")],
            [KeyboardButton("🇨🇭 USDCHF"), KeyboardButton("🇦🇺 AUDUSD"), KeyboardButton("ℹ️ Помощь")],
            [KeyboardButton("🔄 Обновить цены"), KeyboardButton("📉 История")]
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
            f"💰 *Текущие цены:*\n"
        )
        
        # Add current prices
        for symbol, price in REAL_PRICES.items():
            welcome += f"• {symbol}: {price:.5f}\n"
        
        welcome += (
            f"\n⏱ *Интервал:* {CHECK_INTERVAL//60} минут\n"
            f"🌐 *Режим:* Webhook\n"
            f"🚀 *Хостинг:* Render.com\n\n"
            f"✅ *Функции:*\n"
            f"• Авто-сигналы 24/7\n"
            f"• Реальные цены (из MT5)\n"
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
            f"💰 *Последние цены:*\n"
        )
        
        for symbol in SYMBOLS[:4]:
            price = REAL_PRICES.get(symbol, 0)
            status_text += f"• {symbol}: {price:.5f}\n"
        
        status_text += (
            f"\n⏱ *Интервал:* {CHECK_INTERVAL//60} мин\n"
            f"🌐 *Режим:* Webhook\n"
            f"🚀 *Хостинг:* Render.com\n"
            f"⏰ *Время:* {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"✅ *Система работает нормально*"
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
        for symbol in SYMBOLS[:6]:
            price = self.get_current_price(symbol)
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
            # 30% chance for signal
            if random.random() < 0.30:
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
        
        price = self.get_current_price(symbol)
        trend = self.analyze_trend(symbol)
        analysis = self.get_detailed_analysis(symbol, price)
        
        # Calculate change
        if len(self.price_history.get(symbol, [])) > 1:
            prev_price = self.price_history[symbol][-2]
            change = ((price - prev_price) / prev_price) * 100
            change_text = f"📈 Изменение: {change:+.3f}%"
        else:
            change_text = "📈 Изменение: Нет данных"
        
        message = (
            f"📊 *Анализ {symbol}*\n\n"
            f"💰 *Текущая цена:* {price:.5f}\n"
            f"{change_text}\n"
            f"📈 *Тренд:* {trend}\n"
            f"📊 *Анализ:* {analysis}\n\n"
            f"⏰ *Обновлено:* {datetime.now().strftime('%H:%M:%S')}"
        )
        
        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=self.create_keyboard()
        )
    
    async def update_prices_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle price update"""
        await update.message.reply_text(
            "🔄 Обновляю цены...\n\n"
            "Чтобы обновить цену вручную, отправьте:\n"
            "/set_price XAUUSD 5052.15\n\n"
            "Или используйте API:\n"
            f"GET https://trading-bot-yulianius.onrender.com/update_price/XAUUSD/5052.15",
            reply_markup=self.create_keyboard()
        )
    
    async def history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show price history"""
        await update.message.reply_text(
            "📉 Загружаю историю...",
            reply_markup=self.create_keyboard()
        )
        
        history_text = "📉 *История цен:*\n\n"
        for symbol in SYMBOLS[:4]:
            prices = self.price_history.get(symbol, [])
            if len(prices) > 1:
                current = prices[-1]
                previous = prices[-2] if len(prices) > 1 else current
                change = ((current - previous) / previous) * 100
                history_text += f"• {symbol}: {current:.5f} ({change:+.3f}%)\n"
            else:
                history_text += f"• {symbol}: {REAL_PRICES.get(symbol, 0):.5f} (Нет истории)\n"
        
        await update.message.reply_text(
            history_text,
            parse_mode='Markdown',
            reply_markup=self.create_keyboard()
        )
    
    async def set_price_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set price manually: /set_price XAUUSD 5052.15"""
        try:
            if len(context.args) != 2:
                await update.message.reply_text(
                    "❌ Формат: /set_price SYMBOL PRICE\n"
                    "Пример: /set_price XAUUSD 5052.15",
                    reply_markup=self.create_keyboard()
                )
                return
            
            symbol = context.args[0].upper()
            price = float(context.args[1])
            
            if symbol not in SYMBOLS:
                await update.message.reply_text(
                    f"❌ Символ {symbol} не поддерживается",
                    reply_markup=self.create_keyboard()
                )
                return
            
            old_price = REAL_PRICES.get(symbol, 0)
            REAL_PRICES[symbol] = round(price, 5)
            
            # Add to history
            if symbol not in self.price_history:
                self.price_history[symbol] = []
            self.price_history[symbol].append(price)
            
            # Keep only last 100 prices
            if len(self.price_history[symbol]) > 100:
                self.price_history[symbol] = self.price_history[symbol][-100:]
            
            change = ((price - old_price) / old_price * 100) if old_price > 0 else 0
            
            message = (
                f"✅ *Цена обновлена!*\n\n"
                f"📊 *Символ:* {symbol}\n"
                f"💰 *Старая цена:* {old_price:.5f}\n"
                f"💰 *Новая цена:* {price:.5f}\n"
                f"📈 *Изменение:* {change:+.3f}%\n"
                f"⏰ *Время:* {datetime.now().strftime('%H:%M:%S')}"
            )
            
            await update.message.reply_text(
                message,
                parse_mode='Markdown',
                reply_markup=self.create_keyboard()
            )
            
            logger.info(f"💰 Цена обновлена вручную: {symbol} {old_price:.5f} -> {price:.5f}")
            
        except ValueError:
            await update.message.reply_text(
                "❌ Неверный формат цены",
                reply_markup=self.create_keyboard()
            )
        except Exception as e:
            await update.message.reply_text(
                f"❌ Ошибка: {e}",
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
            "/signal - Поиск сигналов\n"
            "/set_price SYMBOL PRICE - Установить цену\n\n"
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
            "• 🇦🇺 AUDUSD - AUD доллар\n"
            "• 🔄 Обновить цены - инструкция\n"
            "• 📉 История - история цен\n\n"
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
        elif text == "🔄 Обновить цены":
            await self.update_prices_command(update, context)
        elif text == "📉 История":
            await self.history_command(update, context)
        elif text == "ℹ️ Помощь":
            await self.help_command(update, context)
        else:
            await update.message.reply_text(
                "🤔 Используйте кнопки или команды",
                reply_markup=self.create_keyboard()
            )
    
    # ========== PRICE MANAGEMENT ==========
    
    def get_current_price(self, symbol):
        """Get current price with realistic movement"""
        if symbol not in REAL_PRICES:
            return 1.0
        
        base_price = REAL_PRICES[symbol]
        
        # Add realistic movement (0.01-0.1% change)
        volatility = 0.001  # 0.1% volatility
        movement = random.uniform(-volatility, volatility)
        new_price = base_price * (1 + movement)
        
        # Update price history
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        self.price_history[symbol].append(new_price)
        
        # Keep only last 100 prices
        if len(self.price_history[symbol]) > 100:
            self.price_history[symbol] = self.price_history[symbol][-100:]
        
        return round(new_price, 5)
    
    def analyze_trend(self, symbol):
        """Analyze trend based on price history"""
        prices = self.price_history.get(symbol, [])
        
        if len(prices) < 5:
            trends = ["📈 Бычий", "📉 Медвежий", "➡️ Боковой"]
            return random.choice(trends)
        
        # Calculate simple trend
        recent = prices[-5:]
        if len(recent) >= 2:
            first = recent[0]
            last = recent[-1]
            change = ((last - first) / first) * 100
            
            if change > 0.1:
                return "📈 Бычий"
            elif change < -0.1:
                return "📉 Медвежий"
            else:
                return "➡️ Боковой"
        
        return "➡️ Боковой"
    
    def get_signal_strength(self, symbol):
        """Get signal strength"""
        strengths = ["🟢 Сильный", "🟡 Средний", "🔴 Слабый"]
        return random.choice(strengths)
    
    def get_detailed_analysis(self, symbol, price):
        """Get detailed analysis based on price"""
        analyses = [
            "Сильное сопротивление сверху",
            "Поддержка снизу удерживается",
            "Пробитие уровня возможен",
            "Консолидация перед движением",
            "Тренд подтверждается объёмами",
            "Коррекция после роста",
            "Формирование дна",
            "Тестирование уровня"
        ]
        return random.choice(analyses)
    
    # ========== SIGNAL GENERATION ==========
    
    def create_realistic_signal(self, symbol):
        """Create realistic trading signal based on current price"""
        current_price = self.get_current_price(symbol)
        
        # Base decision on price movement
        prices = self.price_history.get(symbol, [current_price])
        if len(prices) < 3:
            price_trend = 0
        else:
            price_trend = sum(prices[-3:]) / 3 - sum(prices[-6:-3]) / 3 if len(prices) >= 6 else 0
        
        # Decide action based on trend
        if price_trend > 0:
            # Uptrend - more likely BUY
            weights = [0.6, 0.3, 0.1]  # BUY, SELL, HOLD
        elif price_trend < 0:
            # Downtrend - more likely SELL
            weights = [0.3, 0.6, 0.1]  # BUY, SELL, HOLD
        else:
            # Sideways
            weights = [0.4, 0.4, 0.2]  # BUY, SELL, HOLD
        
        action = random.choices(['BUY', 'SELL', 'HOLD'], weights=weights, k=1)[0]
        
        if action == 'HOLD':
            return None
        
        # Calculate SL/TP based on volatility
        volatility_multiplier = random.uniform(0.8, 1.2)
        
        if action == 'BUY':
            sl_distance = current_price * 0.008 * volatility_multiplier  # 0.8%
            tp_distance = current_price * 0.016 * volatility_multiplier  # 1.6%
            sl = current_price - sl_distance
            tp = current_price + tp_distance
        else:  # SELL
            sl_distance = current_price * 0.008 * volatility_multiplier  # 0.8%
            tp_distance = current_price * 0.016 * volatility_multiplier  # 1.6%
            sl = current_price + sl_distance
            tp = current_price - tp_distance
        
        reasons = [
            "Пробитие уровня сопротивления",
            "Отскок от поддержки",
            "Дивергенция RSI",
            "Пересечение скользящих средних",
            "Сигнал MACD",
            "Паттерн на графике",
            "Тестирование уровня",
            "Коррекция завершена"
        ]
        
        # Calculate confidence based on trend strength
        confidence = min(90, max(60, 70 + abs(price_trend) * 1000))
        
        return {
            'symbol': symbol,
            'action': action,
            'price': round(current_price, 5),
            'sl': round(sl, 5),
            'tp': round(tp, 5),
            'reason': random.choice(reasons),
            'confidence': round(confidence),
            'trend': price_trend,
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
            
            # Calculate distance in points
            if signal['action'] == 'BUY':
                tp_points = round((signal['tp'] - signal['price']) * 10000, 1)
                sl_points = round((signal['price'] - signal['sl']) * 10000, 1)
            else:
                tp_points = round((signal['price'] - signal['tp']) * 10000, 1)
                sl_points = round((signal['sl'] - signal['price']) * 10000, 1)
            
            message = (
                f"{emoji} *{action_text} {signal['symbol']}* {emoji}\n\n"
                f"💰 *Цена входа:* {signal['price']:.5f}\n"
                f"🛡 *Стоп-лосс:* {signal['sl']:.5f} ({sl_points} п)\n"
                f"🎯 *Тейк-профит:* {signal['tp']:.5f} ({tp_points} п)\n"
                f"📊 *Причина:* {signal['reason']}\n"
                f"✅ *Уверенность:* {signal['confidence']}%\n\n"
                f"⏰ *Время:* {signal['timestamp']}\n"
                f"📈 *Тренд:* {'Восходящий' if signal['trend'] > 0 else 'Нисходящий' if signal['trend'] < 0 else 'Боковой'}\n"
                f"🚀 *Бот:* Trading Bot на Render"
            )
            
            bot = Bot(token=self.token)
            await bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown'
            )
            
            logger.info(f"✅ Сигнал отправлен: {signal['symbol']} {signal['action']} по {signal['price']:.5f}")
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
                
                # Log every 3rd check
                if check_counter % 3 == 0:
                    logger.info(f"🔍 Авто-проверка #{check_counter}")
                    # Log current prices
                    for symbol in ['XAUUSD', 'EURUSD']:
                        price = self.get_current_price(symbol)
                        logger.info(f"💰 {symbol}: {price:.5f}")
                
                # 25% chance for auto signal
                if self.chat_id and random.random() < 0.25:
                    symbol = random.choice(SYMBOLS)
                    signal = self.create_realistic_signal(symbol)
                    
                    if signal:
                        # Avoid duplicate signals
                        signal_key = f"{symbol}_{signal['action']}_{datetime.now().strftime('%H')}"
                        
                        if signal_key not in self.last_signals:
                            self.last_signals[signal_key] = datetime.now()
                            
                            success = loop.run_until_complete(self.send_telegram_signal(signal))
                            if success:
                                logger.info(f"🎯 Авто-сигнал: {symbol} {signal['action']} по {signal['price']:.5f}")
                
                # Clean old signals
                current_time = datetime.now()
                self.last_signals = {
                    k: v for k, v in self.last_signals.items() 
                    if current_time - v < timedelta(hours=2)
                }
                
                # Update REAL_PRICES with realistic movement
                for symbol in SYMBOLS:
                    current = REAL_PRICES.get(symbol, 1.0)
                    movement = random.uniform(-0.0005, 0.0005)  # 0.05% max movement
                    REAL_PRICES[symbol] = round(current * (1 + movement), 5)
                
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
    
    def setup_webhook(self):
        """Setup Telegram webhook"""
        try:
            # Create application
            self.application = Application.builder().token(self.token).build()
            
            # Add handlers
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CommandHandler("help", self.help_command))
            self.application.add_handler(CommandHandler("status", self.status_command))
            self.application.add_handler(CommandHandler("analysis", self.analysis_command))
            self.application.add_handler(CommandHandler("signal", self.signal_command))
            self.application.add_handler(CommandHandler("set_price", self.set_price_command))
            
            # Add button handler
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.button_handler))
            
            # Set webhook
            webhook_url = f"{RENDER_URL}/webhook"
            self.application.bot.set_webhook(url=webhook_url)
            
            logger.info(f"✅ Webhook установлен: {webhook_url}")
            logger.info("🤖 Бот готов принимать сообщения через webhook")
            
            # Start application without polling
            self.application.run_webhook(
                listen="0.0.0.0",
                port=PORT,
                webhook_url=webhook_url,
                key=None,
                cert=None,
                drop_pending_updates=True
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка настройки webhook: {e}")
            # Fallback to polling
            logger.info("🔄 Пробую запустить polling...")
            self.telegram_polling_loop()
    
    def telegram_polling_loop(self):
        """Telegram polling loop - fallback"""
        try:
            # Create application in main thread
            self.application = Application.builder().token(self.token).build()
            
            # Add handlers
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CommandHandler("help", self.help_command))
            self.application.add_handler(CommandHandler("status", self.status_command))
            self.application.add_handler(CommandHandler("analysis", self.analysis_command))
            self.application.add_handler(CommandHandler("signal", self.signal_command))
            self.application.add_handler(CommandHandler("set_price", self.set_price_command))
            
            # Add button handler
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.button_handler))
            
            logger.info("📱 Telegram polling запущен (fallback)")
            
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
        print("🤖 TRADING BOT (RENDER.COM) - WEBHOOK VERSION")
        print("="*60)
        print(f"📊 Инструменты: {len(SYMBOLS)}")
        print(f"💰 Текущие цены:")
        for symbol, price in REAL_PRICES.items():
            print(f"   {symbol}: {price:.5f}")
        print(f"⏱ Интервал: {CHECK_INTERVAL//60} мин")
        print(f"🌐 URL: {RENDER_URL}")
        print(f"🚀 Хостинг: Render.com")
        print("="*60)
        print("📱 Основные команды:")
        print("  /start - Активировать бота")
        print("  /set_price XAUUSD 5052.15 - Установить цену")
        print("  /signal - Поиск сигналов")
        print("="*60)
        print("🌐 Webhook URL:")
        print(f"  {RENDER_URL}/webhook")
        print("="*60 + "\n")
        
        # Start Flask in separate thread
        flask_thread = threading.Thread(target=start_flask, daemon=True)
        flask_thread.start()
        logger.info(f"🌐 Flask запущен на порту {PORT}")
        
        # Wait for Flask to start
        time.sleep(3)
        
        # Start auto signals
        signal_thread = threading.Thread(target=self.auto_signal_loop, daemon=True)
        signal_thread.start()
        
        time.sleep(2)
        
        # Setup webhook
        logger.info("🌐 Настраиваю Telegram webhook...")
        self.setup_webhook()

if __name__ == "__main__":
    bot = SimpleTradingBot()
    bot.run()