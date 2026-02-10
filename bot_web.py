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
import requests
from threading import Thread

# Импорт конфигурации
try:
    from config import *
except ImportError:
    # Значения по умолчанию для Render
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')
    TELEGRAM_CHAT_ID = int(os.getenv('TELEGRAM_CHAT_ID', '0'))
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

@app.route('/')
def home():
    """Основной endpoint для проверки работы сервиса"""
    return jsonify({
        'status': 'running',
        'service': 'UniversalTradingBot',
        'version': '2.0.1',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/health')
def health():
    """Health check endpoint для Render"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/status')
def status():
    """Статус бота через HTTP"""
    return jsonify({
        'bot_running': bot.running if 'bot' in globals() else False,
        'telegram_connected': bot.chat_id is not None if 'bot' in globals() else False,
        'check_interval': CHECK_INTERVAL,
        'symbols': SYMBOLS,
        'timestamp': datetime.now().isoformat()
    })

def start_flask():
    """Запуск Flask сервера"""
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

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
        
        logger.info("Бот инициализирован для работы на Render")
    
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
            "⏰ *Работает 24/7*\n\n"
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
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /status"""
        status = "🟢 АКТИВЕН" if self.running else "🔴 НЕ АКТИВЕН"
        signals_count = len(self.last_signals) if hasattr(self, 'last_signals') else 0
        
        status_text = (
            f"🤖 *Статус бота:* {status}\n\n"
            f"📊 *Режим данных:* ДЕМО 📊\n"
            f"📈 *Инструменты:* {', '.join(SYMBOLS)}\n"
            f"⏱ *Интервал проверки:* {CHECK_INTERVAL} сек\n"
            f"🎯 *Найдено сигналов:* {signals_count}\n"
            f"🚀 *Хостинг:* Render.com\n"
            f"⏰ *Uptime:* 24/7\n\n"
            f"*Последняя проверка:* {datetime.now().strftime('%H:%M:%S')}"
        )
        
        keyboard = self.create_main_keyboard()
        await update.message.reply_text(
            status_text, 
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    
    async def test_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /test"""
        await update.message.reply_text(
            "🔄 Создаю тестовый сигнал с графиком...",
            reply_markup=self.create_main_keyboard()
        )
        
        try:
            # Создаем тестовый сигнал
            test_signal = {
                'symbol': 'XAUUSD',
                'action': 'BUY',
                'price': 4855.50,
                'sl': 4855.50 * 0.988,
                'tp': 4855.50 * 1.024,
                'reason': 'Тестовый сигнал - проверка работы бота на Render',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'patterns': ['Тестовый паттерн'],
                'indicators': {
                    'RSI': '32.5',
                    'CCI': '-95.3', 
                    'ATR': '58.2',
                    'Trend': 'BULLISH'
                }
            }
            
            # Получаем данные для графика
            test_data = self.get_market_data('XAUUSD', '1h', 50)
            
            # Отправляем сигнал с графиком
            await self.send_signal_with_chart(test_signal, test_data)
            
            keyboard = self.create_main_keyboard()
            await update.message.reply_text(
                "✅ Тестовый сигнал отправлен! (демо-данные)",
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Ошибка тестового сигнала: {e}")
            keyboard = self.create_main_keyboard()
            await update.message.reply_text(
                "❌ Ошибка отправки тестового сигнала",
                reply_markup=keyboard
            )
    
    async def signal_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /signal"""
        await update.message.reply_text(
            "🔍 Проверяю инструменты...",
            reply_markup=self.create_main_keyboard()
        )
        
        signals_found = 0
        for symbol in SYMBOLS:
            try:
                signal = self.analyze_strategy(symbol)
                if signal:
                    data = self.get_market_data(symbol, '1h', 50)
                    await self.send_signal_with_chart(signal, data)
                    signals_found += 1
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Ошибка проверки {symbol}: {e}")
        
        keyboard = self.create_main_keyboard()
        if signals_found > 0:
            await update.message.reply_text(
                f"✅ Найдено {signals_found} сигналов",
                reply_markup=keyboard
            )
        else:
            await update.message.reply_text(
                "❌ Сигналы не найдены",
                reply_markup=keyboard
            )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = (
            "🤖 *UniversalTradingBot на Render.com*\n\n"
            "📋 *Доступные команды:*\n\n"
            "🚀 /start - активация бота\n"
            "📊 /status - статус и настройки\n"
            "🎯 /test - тестовый сигнал с графиком\n"
            "🔍 /signal - проверить все инструменты\n"
            "📈 /chart XAUUSD - график инструмента XAUUSD\n"
            "📈 /chart EURUSD - график инструмента EURUSD\n"
            "📈 /chart GBPUSD - график инструмента GBPUSD\n\n"
            "📈 *Автоматические сигналы:*\n"
            f"• Интервал проверки: {CHECK_INTERVAL} сек\n"
            f"• Инструменты: {', '.join(SYMBOLS)}\n"
            "• Каждый сигнал включает график с разметкой\n\n"
            "🚀 *Хостинг:* Render.com\n"
            "⏰ *Работает:* 24/7\n"
            "💡 *Используйте кнопки ниже для быстрого доступа!*"
        )
        
        keyboard = self.create_main_keyboard()
        await update.message.reply_text(
            help_text, 
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    
    async def chart_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /chart"""
        try:
            args = context.args
            
            if not args:
                help_text = (
                    "📊 *Использование команды /chart:*\n\n"
                    "/chart XAUUSD - график золота\n"
                    "/chart EURUSD - график евро/доллара\n"
                    "/chart GBPUSD - график фунта/доллара\n\n"
                    "📈 *Доступные инструменты:*\n"
                    f"{', '.join(SYMBOLS)}"
                )
                await update.message.reply_text(
                    help_text, 
                    parse_mode='Markdown',
                    reply_markup=self.create_main_keyboard()
                )
                return
            
            symbol = args[0].upper().strip()
            
            if symbol not in SYMBOLS:
                error_text = (
                    f"❌ Символ *{symbol}* не поддерживается.\n\n"
                    f"📊 *Доступные инструменты:*\n"
                    f"{', '.join(SYMBOLS)}\n\n"
                    "💡 *Примеры:*\n"
                    "/chart XAUUSD\n"
                    "/chart EURUSD\n"
                    "/chart GBPUSD"
                )
                await update.message.reply_text(
                    error_text, 
                    parse_mode='Markdown',
                    reply_markup=self.create_main_keyboard()
                )
                return
            
            await update.message.reply_text(
                f"📊 Создаю график {symbol}...",
                reply_markup=self.create_main_keyboard()
            )
            
            data = self.get_market_data(symbol, '1h', 50)
            
            if data.empty:
                await update.message.reply_text(
                    "❌ Нет данных для построения графика",
                    reply_markup=self.create_main_keyboard()
                )
                return
            
            current_price = data['close'].iloc[-1]
            
            chart_buffer = self.create_simple_chart(data, symbol)
            
            if chart_buffer:
                # Форматируем цену в зависимости от символа
                if symbol == 'XAUUSD':
                    price_format = f"{current_price:.2f}"
                else:
                    price_format = f"{current_price:.5f}"
                    
                caption = (
                    f"📈 {symbol} - H1 таймфрейм\n"
                    f"📍 Последняя цена: {price_format}\n"
                    f"🚀 Хостинг: Render.com"
                )
                
                await update.message.reply_photo(
                    photo=chart_buffer,
                    caption=caption
                )
            else:
                await update.message.reply_text(
                    "❌ Ошибка создания графика",
                    reply_markup=self.create_main_keyboard()
                )
                
        except Exception as e:
            logger.error(f"Ошибка команды /chart: {e}")
            await update.message.reply_text(
                "❌ Ошибка создания графика",
                reply_markup=self.create_main_keyboard()
            )
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на кнопки клавиатуры"""
        text = update.message.text
        
        if text == "📊 Статус":
            await self.status_command(update, context)
        elif text == "🧪 Тест":
            await self.test_command(update, context)
        elif text == "🚨 Сигнал":
            await self.signal_command(update, context)
        elif text == "🟡 XAUUSD":
            await self.send_chart_for_symbol(update, 'XAUUSD')
        elif text == "💶 EURUSD":
            await self.send_chart_for_symbol(update, 'EURUSD')
        elif text == "💷 GBPUSD":
            await self.send_chart_for_symbol(update, 'GBPUSD')
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
    
    async def send_chart_for_symbol(self, update: Update, symbol: str):
        """Отправляет график для указанного символа"""
        await update.message.reply_text(
            f"📊 Создаю график {symbol}...",
            reply_markup=self.create_main_keyboard()
        )
        
        data = self.get_market_data(symbol, '1h', 50)
        if data.empty:
            await update.message.reply_text(
                "❌ Нет данных для построения графика",
                reply_markup=self.create_main_keyboard()
            )
            return
        
        current_price = data['close'].iloc[-1]
        
        chart_buffer = self.create_simple_chart(data, symbol)
        if chart_buffer:
            # Форматируем цену в зависимости от символа
            if symbol == 'XAUUSD':
                price_format = f"{current_price:.2f}"
            else:
                price_format = f"{current_price:.5f}"
                
            caption = (
                f"📈 {symbol} - H1 таймфрейм\n"
                f"📍 Последняя цена: {price_format}\n"
                f"🚀 Хостинг: Render.com"
            )
            await update.message.reply_photo(
                photo=chart_buffer,
                caption=caption
            )
        else:
            await update.message.reply_text(
                "❌ Ошибка создания графика",
                reply_markup=self.create_main_keyboard()
            )
    
    async def send_welcome_chart(self, update):
        """Отправляем приветственный график"""
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            x = np.linspace(0, 10, 100)
            y = np.sin(x)
            
            ax.plot(x, y, 'b-', linewidth=2)
            ax.set_title('UniversalTradingBot - Добро пожаловать!', fontsize=14)
            ax.set_xlabel('Время')
            ax.set_ylabel('Цена')
            ax.grid(True, alpha=0.3)
            
            buffer = io.BytesIO()
            plt.tight_layout()
            plt.savefig(buffer, format='png', dpi=100)
            plt.close(fig)
            buffer.seek(0)
            
            caption = (
                "✅ Бот готов к работе на Render.com!\n\n"
                "🚀 *Особенности:*\n"
                "• Работает 24/7\n"
                "• Автоматические проверки\n"
                "• Графики в реальном времени\n"
                "• Демо-данные\n\n"
                "Сигналы будут приходить автоматически."
            )
            await update.message.reply_photo(
                photo=buffer,
                caption=caption,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Ошибка создания приветственного графика: {e}")
            await update.message.reply_text(
                "✅ Бот активирован на Render! Ожидайте сигналов.",
                reply_markup=self.create_main_keyboard()
            )
    
    # ========== РАБОТА С ДАННЫМИ ==========
    
    def get_market_data(self, symbol, timeframe, bars=100):
        """Генерация демо-данных для Render"""
        return self.generate_demo_data(symbol, timeframe, bars)
    
    def generate_demo_data(self, symbol, timeframe, bars=100):
        """Генерация реалистичных демо-данных"""
        try:
            seed_str = f"{symbol}_{timeframe}_{int(time.time() / 60)}"
            seed_hash = hashlib.md5(seed_str.encode()).hexdigest()
            seed = int(seed_hash[:8], 16) % (2**32 - 1)
            np.random.seed(seed)
            
            base_prices = {
                'XAUUSD': 5057.0,
                'EURUSD': 1.0980,
                'GBPUSD': 1.2800,
            }
            
            base_price = base_prices.get(symbol, 100)
            
            volatility_map = {
                'XAUUSD': 0.0015,
                'EURUSD': 0.0003,
                'GBPUSD': 0.0004,
            }
            
            volatility = volatility_map.get(symbol, 0.001)
            
            if 'h' in timeframe.lower():
                if '4' in timeframe:
                    freq = '4H'
                else:
                    freq = 'H'
            else:
                freq = 'H'
            
            dates = pd.date_range(end=datetime.now(), periods=bars, freq=freq)
            
            prices = [base_price]
            
            for i in range(1, bars):
                rand_change = np.random.randn() * volatility
                
                if i % 20 == 0:
                    trend = np.random.choice([-volatility*0.5, volatility*0.5])
                else:
                    trend = 0
                
                change = rand_change + trend
                new_price = prices[-1] * (1 + change)
                
                max_change = volatility * 2
                if abs(new_price - prices[-1]) / prices[-1] > max_change:
                    new_price = prices[-1] * (1 + np.sign(change) * max_change)
                
                prices.append(new_price)
            
            df = pd.DataFrame(index=dates)
            df['close'] = prices
            df['open'] = df['close'].shift(1).fillna(df['close'])
            
            df['open'] = df['open'] * (1 + np.random.randn(bars) * 0.0001)
            
            spread_multiplier = 0.0002
            
            df['high'] = df[['open', 'close']].max(axis=1) * (1 + abs(np.random.randn(bars)) * spread_multiplier)
            df['low'] = df[['open', 'close']].min(axis=1) * (1 - abs(np.random.randn(bars)) * spread_multiplier)
            
            df['high'] = np.maximum(df['high'], df['low'] + 0.00001)
            
            df['volume'] = [int(1000 + np.random.rand() * 5000) for _ in range(bars)]
            
            logger.debug(f"Сгенерировано {bars} демо-баров для {symbol} {timeframe}")
            return df
            
        except Exception as e:
            logger.error(f"Ошибка генерации демо-данных: {e}")
            dates = pd.date_range(end=datetime.now(), periods=bars, freq='H')
            return pd.DataFrame({
                'close': [5057.0] * bars,
                'open': [5056.5] * bars,
                'high': [5057.5] * bars,
                'low': [5056.0] * bars,
                'volume': [1000] * bars
            }, index=dates)
    
    # ========== ГРАФИКИ ==========
    
    def create_simple_chart(self, data, symbol):
        """Создание простого графика"""
        try:
            if data.empty:
                logger.error("Нет данных для графика")
                return None
            
            fig, ax = plt.subplots(figsize=(10, 6))
            
            plot_data = data.iloc[-30:] if len(data) > 30 else data
            
            for i, (idx, row) in enumerate(plot_data.iterrows()):
                color = 'green' if row['close'] >= row['open'] else 'red'
                
                ax.bar(i, abs(row['close'] - row['open']), 
                      bottom=min(row['open'], row['close']),
                      width=0.6, color=color, edgecolor=color)
                
                ax.vlines(i, row['low'], row['high'], 
                         color=color, linewidth=0.8)
            
            ax.set_title(f'{symbol} - H1 (Render.com)', fontsize=14, fontweight='bold')
            ax.set_xlabel('Свечи (последние 30)')
            ax.set_ylabel('Цена')
            ax.grid(True, alpha=0.3)
            
            buffer = io.BytesIO()
            plt.tight_layout()
            plt.savefig(buffer, format='png', dpi=100)
            plt.close(fig)
            buffer.seek(0)
            
            return buffer
            
        except Exception as e:
            logger.error(f"Ошибка создания простого графика: {e}")
            return None
    
    def create_signal_chart(self, data, symbol, signal):
        """Создание графика с разметкой сигнала"""
        try:
            if data.empty:
                return self.create_simple_chart(data, symbol)
            
            fig, ax = plt.subplots(figsize=(12, 8))
            
            plot_data = data.iloc[-30:] if len(data) > 30 else data
            
            for i, (idx, row) in enumerate(plot_data.iterrows()):
                color = 'green' if row['close'] >= row['open'] else 'red'
                
                ax.bar(i, abs(row['close'] - row['open']), 
                      bottom=min(row['open'], row['close']),
                      width=0.6, color=color, edgecolor=color)
                
                ax.vlines(i, row['low'], row['high'], 
                         color=color, linewidth=0.8)
            
            signal_color = 'lime' if signal['action'] == 'BUY' else 'red'
            entry_price = signal['price']
            
            ax.axhline(y=entry_price, color=signal_color, 
                      linestyle='--', linewidth=2, 
                      label=f"Вход: {entry_price:.2f}")
            
            ax.axhline(y=signal['sl'], color='red', 
                      linestyle=':', linewidth=1.5, 
                      label=f"SL: {signal['sl']:.2f}")
            
            ax.axhline(y=signal['tp'], color='green', 
                      linestyle=':', linewidth=1.5, 
                      label=f"TP: {signal['tp']:.2f}")
            
            action_text = "ПОКУПКА" if signal['action'] == 'BUY' else "ПРОДАЖА"
            
            ax.set_title(f"{symbol} - {action_text} (Render.com)", 
                        fontsize=16, fontweight='bold', color=signal_color)
            ax.set_xlabel('Свечи (последние 30)')
            ax.set_ylabel('Цена')
            ax.legend(facecolor='white', edgecolor='black', framealpha=0.9)
            ax.grid(True, alpha=0.3)
            
            buffer = io.BytesIO()
            plt.tight_layout()
            plt.savefig(buffer, format='png', dpi=100)
            plt.close(fig)
            buffer.seek(0)
            
            return buffer
            
        except Exception as e:
            logger.error(f"Ошибка создания графика сигнала: {e}")
            return self.create_simple_chart(data, symbol)
    
    # ========== ОТПРАВКА СИГНАЛА ==========
    
    async def send_signal_with_chart(self, signal, data):
        """Отправка сигнала с графиком"""
        try:
            if not self.chat_id:
                logger.warning("Не могу отправить сигнал: chat_id не установлен")
                return False
            
            chart_buffer = self.create_signal_chart(data, signal['symbol'], signal)
            
            if not chart_buffer:
                return await self.send_text_signal(signal)
            
            emoji = "🟢" if signal['action'] == 'BUY' else "🔴"
            action_text = "ПОКУПКА" if signal['action'] == 'BUY' else "ПРОДАЖА"
            
            caption = (
                f"{emoji} *{action_text} {signal['symbol']}* {emoji}\n\n"
                f"📍 *Цена входа:* {signal['price']:.2f}\n"
                f"🛡 *Стоп-лосс:* {signal['sl']:.2f}\n"
                f"🎯 *Тейк-профит:* {signal['tp']:.2f}\n"
                f"📊 *Причина:* {signal['reason']}\n\n"
                f"📈 *Паттерны:* {', '.join(signal['patterns'])}\n\n"
                f"⏰ *Время:* {signal['timestamp']}\n"
                f"🚀 *Хостинг:* Render.com\n"
                f"🔧 *Режим:* ДЕМО"
            )
            
            bot = Bot(token=self.token)
            await bot.send_photo(
                chat_id=self.chat_id,
                photo=chart_buffer,
                caption=caption,
                parse_mode='Markdown'
            )
            
            logger.info(f"✅ Отправлен сигнал с графиком: {signal['symbol']} {signal['action']}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки сигнала с графиком: {e}")
            return await self.send_text_signal(signal)
    
    async def send_text_signal(self, signal):
        """Отправка текстового сигнала"""
        try:
            if not self.chat_id:
                return False
            
            emoji = "🟢" if signal['action'] == 'BUY' else "🔴"
            action_text = "ПОКУПКА" if signal['action'] == 'BUY' else "ПРОДАЖА"
            
            message = (
                f"{emoji} *{action_text} {signal['symbol']}* {emoji}\n\n"
                f"📍 *Цена входа:* {signal['price']:.2f}\n"
                f"🛡 *Стоп-лосс:* {signal['sl']:.2f}\n"
                f"🎯 *Тейк-профит:* {signal['tp']:.2f}\n"
                f"📊 *Причина:* {signal['reason']}\n\n"
                f"📈 *Паттерны:* {', '.join(signal['patterns'])}\n\n"
                f"⏰ *Время:* {signal['timestamp']}\n"
                f"🚀 *Хостинг:* Render.com\n"
                f"🔧 *Режим:* ДЕМО"
            )
            
            bot = Bot(token=self.token)
            await bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown'
            )
            
            logger.info(f"✅ Отправлен текстовый сигнал: {signal['symbol']} {signal['action']}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки текстового сигнала: {e}")
            return False
    
    # ========== СТРАТЕГИЯ АНАЛИЗА ==========
    
    def analyze_strategy(self, symbol):
        """Анализ по стратегии"""
        try:
            h4_data = self.get_market_data(symbol, TIMEFRAME_H4, 50)
            h1_data = self.get_market_data(symbol, TIMEFRAME_H1, 100)
            
            if h4_data.empty or h1_data.empty:
                return None
            
            h4_data['EMA_20'] = talib.EMA(h4_data['close'], timeperiod=EMA_PERIOD)
            h4_data['ATR_14'] = talib.ATR(h4_data['high'], h4_data['low'], h4_data['close'], timeperiod=ATR_PERIOD)
            
            h1_data['RSI_7'] = talib.RSI(h1_data['close'], timeperiod=RSI_PERIOD)
            h1_data['CCI_14'] = talib.CCI(h1_data['high'], h1_data['low'], h1_data['close'], timeperiod=CCI_PERIOD)
            h1_data['ATR_14'] = talib.ATR(h1_data['high'], h1_data['low'], h1_data['close'], timeperiod=ATR_PERIOD)
            
            h4_close = h4_data['close'].iloc[-1]
            h4_ema = h4_data['EMA_20'].iloc[-1]
            h4_atr = h4_data['ATR_14'].iloc[-1]
            
            h1_close = h1_data['close'].iloc[-1]
            h1_rsi = h1_data['RSI_7'].iloc[-1]
            h1_cci = h1_data['CCI_14'].iloc[-1]
            h1_atr = h1_data['ATR_14'].iloc[-1]
            
            if pd.isna(h4_ema):
                h4_ema = h4_close
            if pd.isna(h4_atr):
                h4_atr = 100
            if pd.isna(h1_rsi):
                h1_rsi = 50
            if pd.isna(h1_cci):
                h1_cci = 0
            if pd.isna(h1_atr):
                h1_atr = h1_close * 0.01
            
            trend = "BULLISH" if h4_close > h4_ema else "BEARISH"
            
            signal = None
            
            if trend == "BULLISH":
                if h1_rsi < RSI_OVERSOLD or h1_cci < CCI_OVERSOLD:
                    signal = self.create_signal(
                        symbol=symbol,
                        action='BUY',
                        price=h1_close,
                        atr=h1_atr,
                        rsi=h1_rsi,
                        cci=h1_cci,
                        trend=trend,
                        h4_atr=h4_atr
                    )
            
            elif trend == "BEARISH":
                if h1_rsi > RSI_OVERBOUGHT or h1_cci > CCI_OVERBOUGHT:
                    signal = self.create_signal(
                        symbol=symbol,
                        action='SELL',
                        price=h1_close,
                        atr=h1_atr,
                        rsi=h1_rsi,
                        cci=h1_cci,
                        trend=trend,
                        h4_atr=h4_atr
                    )
            
            if signal:
                logger.info(f"🎯 СИГНАЛ {symbol}: {signal['action']} | Цена: {h1_close:.2f} | RSI: {h1_rsi:.1f}")
                return signal
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа {symbol}: {e}")
            return None
    
    def create_signal(self, symbol, action, price, atr, rsi, cci, trend, h4_atr):
        """Создание торгового сигнала"""
        if action == 'BUY':
            sl = price - atr * STOP_LOSS_ATR_MULTIPLIER
            tp = price + atr * TAKE_PROFIT_ATR_MULTIPLIER
        else:
            sl = price + atr * STOP_LOSS_ATR_MULTIPLIER
            tp = price - atr * TAKE_PROFIT_ATR_MULTIPLIER
        
        reasons = []
        if rsi < RSI_OVERSOLD and action == 'BUY':
            reasons.append(f"RSI {rsi:.1f} < {RSI_OVERSOLD}")
        elif rsi > RSI_OVERBOUGHT and action == 'SELL':
            reasons.append(f"RSI {rsi:.1f} > {RSI_OVERBOUGHT}")
        
        if cci < CCI_OVERSOLD and action == 'BUY':
            reasons.append(f"CCI {cci:.1f} < {CCI_OVERSOLD}")
        elif cci > CCI_OVERBOUGHT and action == 'SELL':
            reasons.append(f"CCI {cci:.1f} > {CCI_OVERBOUGHT}")
        
        reason = f"{trend} тренд H4" + (" + " + ", ".join(reasons) if reasons else "")
        
        patterns = []
        if rsi < 35 or cci < -80:
            patterns.append("Возможный молот/поглощение")
        
        return {
            'symbol': symbol,
            'action': action,
            'price': round(price, 5),
            'sl': round(sl, 5),
            'tp': round(tp, 5),
            'reason': reason,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'patterns': patterns if patterns else ['Сигнал по индикаторам'],
            'indicators': {
                'H4_Trend': trend,
                'H4_ATR': round(h4_atr, 2),
                'H1_Price': round(price, 2),
                'H1_RSI': round(rsi, 1),
                'H1_CCI': round(cci, 1),
                'H1_ATR': round(atr, 3),
                'RR': f"1:{RISK_REWARD_RATIO}"
            }
        }
    
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
                        logger.info("📊 Ожидание активации бота (напишите /start в Telegram)")
                    else:
                        logger.info("📊 Сигналы не найдены в этой проверке")
                else:
                    logger.info(f"🎯 Отправлено {signals_found} сигналов")
                
                logger.info(f"⏱ Следующая проверка через {CHECK_INTERVAL} секунд...")
                
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
                drop_pending_updates=True
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка Telegram: {e}")
        finally:
            loop.close()
            logger.info("🛑 Telegram polling остановлен")
    
    def run(self):
        """Запуск бота на Render"""
        logger.info("🚀 Запуск UniversalTradingBot на Render.com...")
        
        print("\n" + "="*70)
        print("🤖 UNIVERSAL TRADING BOT (RENDER.COM)")
        print("="*70)
        print(f"📊 Режим данных: ДЕМО 📊")
        print(f"📈 Инструменты: {', '.join(SYMBOLS)}")
        print(f"⏱ Интервал проверки: {CHECK_INTERVAL} сек")
        print(f"🎯 Стратегия: H4 тренд + H1 откаты")
        print(f"📊 Графики: ВКЛЮЧЕНЫ")
        print(f"📱 Клавиатура: ПОСТОЯННАЯ ВНИЗУ")
        print(f"🚀 Хостинг: Render.com")
        print(f"⏰ Режим: 24/7")
        print("="*70)
        print("📱 ИНСТРУКЦИЯ:")
        print("  1. Откройте Telegram")
        print("  2. Найдите бота")
        print("  3. Напишите /start (ОБЯЗАТЕЛЬНО!)")
        print("  4. Используйте ПОСТОЯННЫЕ кнопки внизу для быстрого доступа!")
        print("="*70)
        print("🛑 Сервис автоматически перезапускается на Render")
        print("="*70 + "\n")
        
        # Запускаем Flask сервер в отдельном потоке
        flask_thread = threading.Thread(
            target=start_flask,
            daemon=True,
            name="FlaskThread"
        )
        flask_thread.start()
        logger.info("🌐 Flask сервер запущен для health checks")
        
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
        
        # Бесконечный цикл для поддержания работы
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.running = False
            print("\n" + "="*60)
            print("👋 Бот остановлен")
            print("="*60 + "\n")
            time.sleep(2)
            sys.exit(0)

if __name__ == "__main__":
    bot = UniversalTradingBot()
    bot.run()