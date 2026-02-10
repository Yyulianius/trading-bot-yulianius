#!/usr/bin/env python3
"""
REAL Trading Bot with Yahoo Finance - Version WITHOUT MT5
"""

import os
import time
import logging
from datetime import datetime, timedelta
import threading
import asyncio
import sys
import io
import warnings
import yfinance as yf
warnings.filterwarnings('ignore')

# Flask
from flask import Flask, jsonify

# Telegram
from telegram import Bot, Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# Data Analysis
import pandas as pd
import numpy as np

# Charts
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image

# Configuration
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')
TELEGRAM_CHAT_ID = int(os.getenv('TELEGRAM_CHAT_ID', '1037258513'))

# Символы для Yahoo Finance (другие тикеры)
SYMBOLS_MAP = {
    'XAUUSD': 'GC=F',      # Gold Futures
    'XAGUSD': 'SI=F',      # Silver Futures  
    'EURUSD': 'EURUSD=X',  # EUR/USD
    'GBPUSD': 'GBPUSD=X',  # GBP/USD
    'NZDUSD': 'NZDUSD=X',  # NZD/USD
    'USDCAD': 'CAD=X',     # USD/CAD
    'USDCHF': 'CHF=X',     # USD/CHF
    'AUDUSD': 'AUDUSD=X'   # AUD/USD
}

SYMBOLS = list(SYMBOLS_MAP.keys())
CHECK_INTERVAL = 60  # 1 minute
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
        'service': 'Trading Bot Pro (Yahoo Finance)',
        'data_source': 'Yahoo Finance',
        'symbols': SYMBOLS,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'}), 200

def start_flask():
    """Start Flask server"""
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

class YahooDataFetcher:
    """Yahoo Finance Data Fetcher"""
    
    @staticmethod
    def fetch_data(symbol, interval='1h', period='5d'):
        """Fetch real data from Yahoo Finance"""
        try:
            yahoo_symbol = SYMBOLS_MAP.get(symbol)
            if not yahoo_symbol:
                logger.error(f"No Yahoo symbol for {symbol}")
                return None
            
            # Download data
            ticker = yf.Ticker(yahoo_symbol)
            
            # Map interval
            interval_map = {
                '1h': '1h',
                'H1': '1h',
                'H4': '4h',
                '4h': '4h',
                'D1': '1d',
                '1d': '1d'
            }
            
            yf_interval = interval_map.get(interval, '1h')
            yf_period = '5d' if yf_interval in ['1h', '4h'] else '1mo'
            
            df = ticker.history(interval=yf_interval, period=yf_period)
            
            if df.empty:
                logger.warning(f"No data for {symbol} ({yahoo_symbol})")
                return None
            
            # Rename columns to match our format
            df.rename(columns={
                'Open': 'Open',
                'High': 'High',
                'Low': 'Low',
                'Close': 'Close',
                'Volume': 'Volume'
            }, inplace=True)
            
            logger.info(f"✅ Данные загружены: {symbol} ({yahoo_symbol}) - {len(df)} баров")
            return df[['Open', 'High', 'Low', 'Close', 'Volume']]
            
        except Exception as e:
            logger.error(f"Error fetching {symbol}: {e}")
            return None
    
    @staticmethod
    def get_current_price(symbol):
        """Get current price"""
        try:
            yahoo_symbol = SYMBOLS_MAP.get(symbol)
            if not yahoo_symbol:
                return None
            
            ticker = yf.Ticker(yahoo_symbol)
            hist = ticker.history(period='1d', interval='1m')
            
            if not hist.empty:
                return {
                    'price': hist['Close'].iloc[-1],
                    'timestamp': datetime.now().strftime('%H:%M:%S')
                }
            return None
        except:
            return None

class TechnicalAnalyzer:
    """Professional Technical Analysis"""
    
    @staticmethod
    def analyze_symbol(symbol):
        """Complete analysis for a symbol"""
        try:
            # Fetch data for different timeframes
            h1_data = YahooDataFetcher.fetch_data(symbol, '1h', '5d')
            h4_data = YahooDataFetcher.fetch_data(symbol, '4h', '10d')
            
            if h1_data is None or h4_data is None or h1_data.empty or h4_data.empty:
                logger.warning(f"Недостаточно данных для {symbol}")
                return None
            
            # Calculate all indicators
            signals = []
            
            # 1. Trend Analysis (H4)
            h4_trend = TechnicalAnalyzer.analyze_trend(h4_data)
            signals.append(f"H4 Тренд: {h4_trend}")
            
            # 2. Momentum Indicators (H1)
            rsi_signal = TechnicalAnalyzer.analyze_rsi(h1_data)
            if rsi_signal:
                signals.append(f"RSI: {rsi_signal}")
            
            macd_signal = TechnicalAnalyzer.analyze_macd(h1_data)
            if macd_signal:
                signals.append(f"MACD: {macd_signal}")
            
            # 3. Volatility
            bb_signal = TechnicalAnalyzer.analyze_bollinger(h1_data)
            if bb_signal:
                signals.append(f"Bollinger: {bb_signal}")
            
            atr_value = TechnicalAnalyzer.calculate_atr(h1_data)
            signals.append(f"ATR: {atr_value:.4f}")
            
            # 4. Candlestick Patterns
            patterns = TechnicalAnalyzer.detect_patterns_simple(h1_data)
            if patterns:
                signals.append(f"Паттерны: {', '.join(patterns)}")
            
            # 5. Support/Resistance
            sr_levels = TechnicalAnalyzer.find_support_resistance(h1_data)
            
            # 6. Generate trading signal
            trading_signal = TechnicalAnalyzer.generate_trading_signal(
                symbol, h1_data, h4_trend, rsi_signal, macd_signal, 
                bb_signal, patterns, sr_levels
            )
            
            return {
                'symbol': symbol,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'signals': signals,
                'trading_signal': trading_signal,
                'current_price': h1_data['Close'].iloc[-1] if not h1_data.empty else 0,
                'support_resistance': sr_levels,
                'data': h1_data
            }
            
        except Exception as e:
            logger.error(f"Analysis error for {symbol}: {e}")
            return None
    
    @staticmethod
    def analyze_trend(data):
        """Determine trend direction"""
        if data.empty or len(data) < 20:
            return "Недостаточно данных"
        
        close = data['Close']
        
        # Calculate EMAs
        ema_20 = close.ewm(span=20, adjust=False).mean()
        ema_50 = close.ewm(span=50, adjust=False).mean()
        
        current_price = close.iloc[-1]
        ema20_val = ema_20.iloc[-1]
        ema50_val = ema_50.iloc[-1]
        
        # Trend logic
        if current_price > ema20_val > ema50_val:
            return "📈 Сильный бычий"
        elif current_price > ema20_val and ema20_val > ema50_val:
            return "📈 Бычий"
        elif current_price < ema20_val < ema50_val:
            return "📉 Сильный медвежий"
        elif current_price < ema20_val and ema20_val < ema50_val:
            return "📉 Медвежий"
        else:
            return "➡️ Боковой"
    
    @staticmethod
    def analyze_rsi(data, period=14):
        """RSI analysis"""
        if len(data) < period + 1:
            return None
        
        close = data['Close']
        
        # Manual RSI calculation
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        # Avoid division by zero
        loss = loss.replace(0, 0.000001)
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        if pd.isna(rsi.iloc[-1]):
            return None
        
        rsi_value = rsi.iloc[-1]
        
        if rsi_value < 30:
            return f"ПЕРЕПРОДАНО ({rsi_value:.1f})"
        elif rsi_value > 70:
            return f"ПЕРЕКУПЛЕНО ({rsi_value:.1f})"
        elif 30 <= rsi_value <= 40:
            return f"Возможна покупка ({rsi_value:.1f})"
        elif 60 <= rsi_value <= 70:
            return f"Возможна продажа ({rsi_value:.1f})"
        else:
            return f"Нейтрально ({rsi_value:.1f})"
    
    @staticmethod
    def analyze_macd(data):
        """MACD analysis"""
        if len(data) < 35:
            return None
        
        close = data['Close']
        
        # Manual MACD calculation
        ema_12 = close.ewm(span=12, adjust=False).mean()
        ema_26 = close.ewm(span=26, adjust=False).mean()
        macd_line = ema_12 - ema_26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        histogram = macd_line - signal_line
        
        macd_val = macd_line.iloc[-1]
        signal_val = signal_line.iloc[-1]
        hist_val = histogram.iloc[-1]
        
        if macd_val > signal_val and hist_val > 0:
            return "БЫЧИЙ"
        elif macd_val < signal_val and hist_val < 0:
            return "МЕДВЕЖИЙ"
        else:
            return "НЕТ СИГНАЛА"
    
    @staticmethod
    def analyze_bollinger(data, period=20):
        """Bollinger Bands analysis"""
        if len(data) < period:
            return None
        
        close = data['Close']
        
        # Manual Bollinger Bands
        sma = close.rolling(window=period).mean()
        std = close.rolling(window=period).std()
        
        upper_band = sma + (std * 2)
        lower_band = sma - (std * 2)
        
        current_price = close.iloc[-1]
        upper_val = upper_band.iloc[-1]
        lower_val = lower_band.iloc[-1]
        
        if current_price >= upper_val:
            return "ВЕРХНЯЯ ГРАНИЦА"
        elif current_price <= lower_val:
            return "НИЖНЯЯ ГРАНИЦА"
        else:
            return "ВНУТРИ КАНАЛА"
    
    @staticmethod
    def calculate_atr(data, period=14):
        """Calculate Average True Range"""
        if len(data) < period:
            return 0
        
        high = data['High']
        low = data['Low']
        close = data['Close']
        
        # Calculate True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr.iloc[-1] if not pd.isna(atr.iloc[-1]) else 0
    
    @staticmethod
    def detect_patterns_simple(data):
        """Detect simple candlestick patterns"""
        if len(data) < 3:
            return []
        
        patterns = []
        
        try:
            # Get last 3 candles
            last_3 = data.tail(3)
            
            # Check for patterns
            opens = last_3['Open'].values
            closes = last_3['Close'].values
            highs = last_3['High'].values
            lows = last_3['Low'].values
            
            # Hammer pattern
            if TechnicalAnalyzer.is_hammer(opens[-1], closes[-1], highs[-1], lows[-1]):
                patterns.append("Молот")
            
            # Engulfing pattern
            if len(opens) >= 2:
                if TechnicalAnalyzer.is_bullish_engulfing(opens[-2], closes[-2], opens[-1], closes[-1]):
                    patterns.append("Бычье поглощение")
                elif TechnicalAnalyzer.is_bearish_engulfing(opens[-2], closes[-2], opens[-1], closes[-1]):
                    patterns.append("Медвежье поглощение")
            
            # Doji pattern
            if TechnicalAnalyzer.is_doji(opens[-1], closes[-1], highs[-1], lows[-1]):
                patterns.append("Доджи")
                
        except Exception as e:
            logger.error(f"Pattern detection error: {e}")
        
        return patterns
    
    @staticmethod
    def is_hammer(open_price, close, high, low):
        """Check for hammer pattern"""
        body = abs(close - open_price)
        lower_shadow = min(open_price, close) - low
        upper_shadow = high - max(open_price, close)
        
        return (lower_shadow > body * 2 and upper_shadow < body * 0.1)
    
    @staticmethod
    def is_bullish_engulfing(open1, close1, open2, close2):
        """Check for bullish engulfing"""
        return (close1 < open1 and  # First candle is bearish
                close2 > open2 and  # Second candle is bullish
                open2 < close1 and  # Open below previous close
                close2 > open1)     # Close above previous open
    
    @staticmethod
    def is_bearish_engulfing(open1, close1, open2, close2):
        """Check for bearish engulfing"""
        return (close1 > open1 and  # First candle is bullish
                close2 < open2 and  # Second candle is bearish
                open2 > close1 and  # Open above previous close
                close2 < open1)     # Close below previous open
    
    @staticmethod
    def is_doji(open_price, close, high, low):
        """Check for doji pattern"""
        body = abs(close - open_price)
        total_range = high - low
        
        return (body <= total_range * 0.1)  # Small body relative to range
    
    @staticmethod
    def find_support_resistance(data, window=20):
        """Find support and resistance levels"""
        if len(data) < window:
            return {'support': [], 'resistance': []}
        
        high = data['High']
        low = data['Low']
        
        # Simple pivot points
        recent_highs = high.rolling(window=window).max().dropna()
        recent_lows = low.rolling(window=window).min().dropna()
        
        support_levels = recent_lows.unique().tolist()
        resistance_levels = recent_highs.unique().tolist()
        
        # Get current price
        current_price = data['Close'].iloc[-1]
        
        # Find nearest levels
        nearest_support = max([s for s in support_levels if s < current_price], default=None)
        nearest_resistance = min([r for r in resistance_levels if r > current_price], default=None)
        
        return {
            'support': [nearest_support] if nearest_support else [],
            'resistance': [nearest_resistance] if nearest_resistance else []
        }
    
    @staticmethod
    def generate_trading_signal(symbol, data, trend, rsi_signal, macd_signal, 
                                bb_signal, patterns, sr_levels):
        """Generate trading decision"""
        if data.empty:
            return None
        
        current_price = data['Close'].iloc[-1]
        signal = {
            'symbol': symbol,
            'price': round(current_price, 5),
            'action': 'HOLD',
            'confidence': 0,
            'reason': [],
            'risk_level': 'MEDIUM'
        }
        
        reasons = []
        confidence_points = 0
        
        # 1. Trend analysis (30 points max)
        if "бычий" in trend.lower():
            confidence_points += 20
            reasons.append("Восходящий тренд")
        elif "медвежий" in trend.lower():
            confidence_points -= 20
            reasons.append("Нисходящий тренд")
        
        # 2. RSI signals (20 points)
        if rsi_signal:
            if "ПЕРЕПРОДАНО" in rsi_signal or "покупка" in rsi_signal:
                confidence_points += 15
                reasons.append("Перепроданность RSI")
            elif "ПЕРЕКУПЛЕНО" in rsi_signal or "продажа" in rsi_signal:
                confidence_points -= 15
                reasons.append("Перекупленность RSI")
        
        # 3. MACD signals (20 points)
        if macd_signal == "БЫЧИЙ":
            confidence_points += 15
            reasons.append("Бычий MACD")
        elif macd_signal == "МЕДВЕЖИЙ":
            confidence_points -= 15
            reasons.append("Медвежий MACD")
        
        # 4. Bollinger Bands (15 points)
        if bb_signal == "НИЖНЯЯ ГРАНИЦА":
            confidence_points += 10
            reasons.append("Нижняя граница BB")
        elif bb_signal == "ВЕРХНЯЯ ГРАНИЦА":
            confidence_points -= 10
            reasons.append("Верхняя граница BB")
        
        # 5. Candlestick patterns (15 points)
        bullish_patterns = ["Молот", "Бычье поглощение"]
        bearish_patterns = ["Медвежье поглощение", "Доджи"]
        
        for pattern in patterns:
            if pattern in bullish_patterns:
                confidence_points += 10
                reasons.append(f"Паттерн {pattern}")
            elif pattern in bearish_patterns:
                confidence_points -= 10
                reasons.append(f"Паттерн {pattern}")
        
        # 6. Support/Resistance (20 points)
        current_price = data['Close'].iloc[-1]
        support_levels = sr_levels.get('support', [])
        resistance_levels = sr_levels.get('resistance', [])
        
        # Check if price near support
        for support in support_levels:
            if support and abs(current_price - support) / support < 0.002:  # 0.2%
                confidence_points += 15
                reasons.append(f"Поддержка {support:.5f}")
                break
        
        # Check if price near resistance
        for resistance in resistance_levels:
            if resistance and abs(current_price - resistance) / resistance < 0.002:  # 0.2%
                confidence_points -= 15
                reasons.append(f"Сопротивление {resistance:.5f}")
                break
        
        # Determine action based on total points
        signal['confidence'] = min(100, max(0, 50 + confidence_points))
        
        if confidence_points >= 30:
            signal['action'] = 'BUY'
            signal['risk_level'] = 'LOW' if confidence_points >= 50 else 'MEDIUM'
        elif confidence_points <= -30:
            signal['action'] = 'SELL'
            signal['risk_level'] = 'LOW' if confidence_points <= -50 else 'MEDIUM'
        
        signal['reason'] = reasons
        
        # Calculate stop loss and take profit
        atr_value = TechnicalAnalyzer.calculate_atr(data)
        if signal['action'] == 'BUY':
            signal['sl'] = round(current_price - atr_value * 1.5, 5)
            signal['tp'] = round(current_price + atr_value * 2.5, 5)
        elif signal['action'] == 'SELL':
            signal['sl'] = round(current_price + atr_value * 1.5, 5)
            signal['tp'] = round(current_price - atr_value * 2.5, 5)
        else:
            signal['sl'] = 0
            signal['tp'] = 0
        
        return signal

class ChartGenerator:
    """Generate trading charts"""
    
    @staticmethod
    def create_price_chart(data, symbol, signal=None, sr_levels=None):
        """Create price chart"""
        try:
            if data.empty or len(data) < 10:
                return None
            
            # Use last 30 candles
            plot_data = data.tail(30).copy()
            
            # Create figure
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # Plot price line
            ax.plot(plot_data.index, plot_data['Close'], 
                   linewidth=2, color='blue', label='Цена закрытия')
            
            # Plot moving averages
            ax.plot(plot_data.index, plot_data['Close'].rolling(20).mean(),
                   linewidth=1, color='orange', linestyle='--', label='SMA(20)')
            
            # Add title
            ax.set_title(f'{symbol} | Yahoo Finance', fontsize=14, fontweight='bold')
            ax.set_ylabel('Цена')
            ax.grid(True, alpha=0.3)
            ax.legend()
            
            # Add signal markers if provided
            if signal and signal['action'] != 'HOLD':
                color = 'green' if signal['action'] == 'BUY' else 'red'
                ax.axhline(y=signal['price'], color=color, linestyle='--', 
                          linewidth=2, alpha=0.7, label=f"Вход: {signal['price']:.5f}")
                
                if signal['sl'] > 0:
                    ax.axhline(y=signal['sl'], color='red', linestyle=':', 
                              linewidth=1.5, alpha=0.5, label=f"SL: {signal['sl']:.5f}")
                
                if signal['tp'] > 0:
                    ax.axhline(y=signal['tp'], color='green', linestyle=':', 
                              linewidth=1.5, alpha=0.5, label=f"TP: {signal['tp']:.5f}")
            
            # Add support/resistance lines
            if sr_levels:
                for support in sr_levels.get('support', []):
                    if support:
                        ax.axhline(y=support, color='blue', linestyle='--', 
                                  linewidth=1, alpha=0.3, label='Поддержка')
                
                for resistance in sr_levels.get('resistance', []):
                    if resistance:
                        ax.axhline(y=resistance, color='orange', linestyle='--', 
                                  linewidth=1, alpha=0.3, label='Сопротивление')
            
            plt.tight_layout()
            
            # Save to buffer
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            plt.close(fig)
            buf.seek(0)
            
            return buf
            
        except Exception as e:
            logger.error(f"Chart creation error: {e}")
            return None

class TradingBot:
    """Main Trading Bot Class"""
    
    def __init__(self):
        self.token = TELEGRAM_TOKEN
        self.application = None
        self.running = False
        self.chat_id = TELEGRAM_CHAT_ID
        self.last_signals = {}
        
        logger.info("🤖 Trading Bot PRO инициализирован (Yahoo Finance)")
    
    def create_keyboard(self):
        """Create Telegram keyboard"""
        keyboard = [
            [KeyboardButton("📊 Статус"), KeyboardButton("📈 Анализ"), KeyboardButton("🚨 Сигнал")],
            [KeyboardButton("🟡 XAUUSD"), KeyboardButton("⚪ XAGUSD"), KeyboardButton("💶 EURUSD")],
            [KeyboardButton("💷 GBPUSD"), KeyboardButton("🌿 NZDUSD"), KeyboardButton("🍁 USDCAD")],
            [KeyboardButton("🇨🇭 USDCHF"), KeyboardButton("🇦🇺 AUDUSD"), KeyboardButton("ℹ️ Помощь")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)
    
    # ========== TELEGRAM COMMANDS ==========
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start"""
        self.chat_id = update.effective_chat.id
        logger.info(f"📱 Бот активирован в чате: {self.chat_id}")
        
        welcome = (
            f"🤖 *Trading Bot PRO*\n\n"
            f"📊 *Источник данных:* Yahoo Finance\n"
            f"📈 *Инструменты:* {len(SYMBOLS)} валютных пар\n"
            f"⏱ *Частота проверки:* {CHECK_INTERVAL} сек\n"
            f"🌐 *Хостинг:* Render.com\n\n"
            f"✅ *Функции:*\n"
            f"• Реальные котировки Yahoo Finance\n"
            f"• Технический анализ (RSI, MACD, BB)\n"
            f"• Графики с точками входа\n"
            f"• Паттерны и уровни S/R\n"
            f"• Авто-сигналы 24/7"
        )
        
        await update.message.reply_text(
            welcome,
            parse_mode='Markdown',
            reply_markup=self.create_keyboard()
        )
        
        # Send test signal
        await self.send_test_signal(update)
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status"""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Test data fetch
        test_data = YahooDataFetcher.fetch_data('XAUUSD', '1h', '1d')
        data_status = "✅ Данные доступны" if test_data is not None and not test_data.empty else "⚠️ Проверьте подключение"
        
        status_text = (
            f"🤖 *Статус системы*\n\n"
            f"🟢 *Бот:* Активен\n"
            f"📡 *Источник:* Yahoo Finance\n"
            f"📊 *Данные:* {data_status}\n"
            f"📈 *Инструменты:* {len(SYMBOLS)}\n"
            f"📊 *Анализ:* RSI, MACD, Bollinger Bands\n"
            f"⏱ *Интервал:* {CHECK_INTERVAL} сек\n"
            f"🌐 *Flask порт:* {PORT}\n"
            f"⏰ *Время:* {current_time}"
        )
        
        await update.message.reply_text(
            status_text,
            parse_mode='Markdown',
            reply_markup=self.create_keyboard()
        )
    
    async def analysis_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /analysis"""
        await update.message.reply_text(
            "📈 Анализирую все инструменты...",
            reply_markup=self.create_keyboard()
        )
        
        analysis_results = []
        for symbol in SYMBOLS[:4]:  # First 4 for speed
            try:
                analysis = TechnicalAnalyzer.analyze_symbol(symbol)
                if analysis:
                    price = analysis['current_price']
                    trend = next((s for s in analysis['signals'] if 'Тренд' in s), 'Нет данных')
                    
                    analysis_results.append(
                        f"{symbol}: {price:.5f} | {trend}"
                    )
            except Exception as e:
                logger.error(f"Ошибка анализа {symbol}: {e}")
        
        if analysis_results:
            result = "📊 *Текущий анализ (H1/H4):*\n\n" + "\n".join(analysis_results)
            await update.message.reply_text(
                result,
                parse_mode='Markdown',
                reply_markup=self.create_keyboard()
            )
        else:
            await update.message.reply_text(
                "❌ Ошибка получения данных",
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
            try:
                analysis = TechnicalAnalyzer.analyze_symbol(symbol)
                if analysis and analysis['trading_signal']:
                    signal = analysis['trading_signal']
                    
                    if signal['action'] != 'HOLD' and signal['confidence'] > 60:
                        # Send signal with chart
                        await self.send_real_signal_with_chart(analysis)
                        signals_found += 1
                        await asyncio.sleep(1)  # Rate limiting
                        
            except Exception as e:
                logger.error(f"Ошибка сигнала {symbol}: {e}")
        
        if signals_found > 0:
            await update.message.reply_text(
                f"✅ Найдено {signals_found} сигналов",
                reply_markup=self.create_keyboard()
            )
        else:
            await update.message.reply_text(
                "📊 Сигналы не найдены (низкая уверенность)",
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
        
        try:
            analysis = TechnicalAnalyzer.analyze_symbol(symbol)
            if analysis:
                # Send analysis summary
                summary = self.format_analysis_summary(analysis)
                await update.message.reply_text(
                    summary,
                    parse_mode='Markdown',
                    reply_markup=self.create_keyboard()
                )
                
                # Send chart
                chart = ChartGenerator.create_price_chart(
                    analysis['data'], symbol,
                    analysis['trading_signal'],
                    analysis['support_resistance']
                )
                
                if chart:
                    caption = f"📊 {symbol} | Yahoo Finance"
                    await update.message.reply_photo(
                        photo=chart,
                        caption=caption
                    )
            else:
                await update.message.reply_text(
                    f"❌ Нет данных для {symbol}",
                    reply_markup=self.create_keyboard()
                )
                
        except Exception as e:
            logger.error(f"Ошибка анализа {symbol}: {e}")
            await update.message.reply_text(
                f"❌ Ошибка анализа {symbol}",
                reply_markup=self.create_keyboard()
            )
    
    def format_analysis_summary(self, analysis):
        """Format analysis results for Telegram"""
        symbol = analysis['symbol']
        price = analysis['current_price']
        signal = analysis['trading_signal']
        
        summary = f"📊 *Анализ {symbol}*\n\n"
        summary += f"💰 *Текущая цена:* {price:.5f}\n\n"
        
        summary += "📈 *Сигналы:*\n"
        for sig in analysis['signals'][:5]:  # First 5 signals
            summary += f"• {sig}\n"
        
        if signal and signal['action'] != 'HOLD':
            summary += f"\n🎯 *Торговый сигнал:*\n"
            summary += f"• Действие: {signal['action']}\n"
            summary += f"• Уверенность: {signal['confidence']}%\n"
            summary += f"• Цена входа: {signal['price']:.5f}\n"
            if signal['sl'] > 0:
                summary += f"• Стоп-лосс: {signal['sl']:.5f}\n"
            if signal['tp'] > 0:
                summary += f"• Тейк-профит: {signal['tp']:.5f}\n"
            
            summary += f"• Причины: {', '.join(signal['reason'][:3])}\n"
        
        summary += f"\n⏰ *Время анализа:* {analysis['timestamp']}"
        summary += f"\n📡 *Источник:* Yahoo Finance"
        
        return summary
    
    async def send_real_signal_with_chart(self, analysis):
        """Send trading signal with chart"""
        try:
            if not self.chat_id:
                return False
            
            symbol = analysis['symbol']
            signal = analysis['trading_signal']
            
            if signal['action'] == 'HOLD' or signal['confidence'] < 60:
                return False
            
            # Generate chart
            chart = ChartGenerator.create_price_chart(
                analysis['data'], symbol,
                signal,
                analysis['support_resistance']
            )
            
            if not chart:
                # Send text only if chart fails
                return await self.send_text_signal(analysis)
            
            # Prepare signal message
            emoji = "🟢" if signal['action'] == 'BUY' else "🔴"
            action_text = "ПОКУПКА" if signal['action'] == 'BUY' else "ПРОДАЖА"
            
            message = (
                f"{emoji} *{action_text} {symbol}* {emoji}\n\n"
                f"💰 *Цена входа:* {signal['price']:.5f}\n"
                f"🛡 *Стоп-лосс:* {signal['sl']:.5f}\n"
                f"🎯 *Тейк-профит:* {signal['tp']:.5f}\n"
                f"✅ *Уверенность:* {signal['confidence']}%\n"
                f"📊 *Уровень риска:* {signal['risk_level']}\n\n"
                f"📈 *Основные причины:*\n"
            )
            
            # Add top 3 reasons
            for i, reason in enumerate(signal['reason'][:3], 1):
                message += f"{i}. {reason}\n"
            
            message += f"\n⏰ *Время:* {analysis['timestamp']}\n"
            message += f"📡 *Источник:* Yahoo Finance\n"
            message += f"🚀 *Бот:* Trading Bot PRO"
            
            # Send to Telegram
            bot = Bot(token=self.token)
            
            # Send photo with caption
            await bot.send_photo(
                chat_id=self.chat_id,
                photo=chart,
                caption=message,
                parse_mode='Markdown'
            )
            
            logger.info(f"✅ Сигнал отправлен: {symbol} {signal['action']} ({signal['confidence']}%)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки сигнала с графиком: {e}")
            return await self.send_text_signal(analysis)
    
    async def send_text_signal(self, analysis):
        """Send text-only signal"""
        try:
            if not self.chat_id:
                return False
            
            symbol = analysis['symbol']
            signal = analysis['trading_signal']
            
            emoji = "🟢" if signal['action'] == 'BUY' else "🔴"
            action_text = "ПОКУПКА" if signal['action'] == 'BUY' else "ПРОДАЖА"
            
            message = (
                f"{emoji} *{action_text} {symbol}* {emoji}\n\n"
                f"💰 *Цена входа:* {signal['price']:.5f}\n"
                f"🛡 *Стоп-лосс:* {signal['sl']:.5f}\n"
                f"🎯 *Тейк-профит:* {signal['tp']:.5f}\n"
                f"✅ *Уверенность:* {signal['confidence']}%\n"
                f"📊 *Причины:* {', '.join(signal['reason'][:3])}\n\n"
                f"⏰ *Время:* {analysis['timestamp']}\n"
                f"📡 *Источник:* Yahoo Finance"
            )
            
            bot = Bot(token=self.token)
            await bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown'
            )
            
            logger.info(f"✅ Текстовый сигнал отправлен: {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки текстового сигнала: {e}")
            return False
    
    async def send_test_signal(self, update):
        """Send test signal on start"""
        try:
            # Get XAUUSD data
            data = YahooDataFetcher.fetch_data('XAUUSD', '1h', '1d')
            if data is not None and not data.empty:
                current_price = data['Close'].iloc[-1]
                
                message = (
                    "🟡 *ТЕСТОВЫЙ СИГНАЛ*\n\n"
                    f"💰 *XAUUSD (Gold):* {current_price:.2f}\n"
                    f"📡 *Источник:* Yahoo Finance\n"
                    f"🌐 *Бот:* Работает на Render.com\n\n"
                    f"✅ *Система готова к реальным сигналам!*\n"
                    f"Используйте кнопку '🚨 Сигнал' для поиска"
                )
                
                await update.message.reply_text(
                    message,
                    parse_mode='Markdown',
                    reply_markup=self.create_keyboard()
                )
                
        except Exception as e:
            logger.error(f"Ошибка тестового сигнала: {e}")
    
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
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help"""
        help_text = (
            "🤖 *Trading Bot PRO - Команды*\n\n"
            "📋 *Основные команды:*\n"
            "/start - Активация бота\n"
            "/status - Статус системы\n"
            "/analysis - Анализ всех инструментов\n"
            "/signal - Поиск торговых сигналов\n\n"
            "📱 *Кнопки быстрого анализа:*\n"
            "• 🟡 XAUUSD - золото\n"
            "• ⚪ XAGUSD - серебро\n"
            "• 💶 EURUSD - евро/доллар\n"
            "• 💷 GBPUSD - фунт/доллар\n"
            "• 🌿 NZDUSD - новозеландский доллар\n"
            "• 🍁 USDCAD - канадский доллар\n"
            "• 🇨🇭 USDCHF - швейцарский франк\n"
            "• 🇦🇺 AUDUSD - австралийский доллар\n\n"
            "📊 *Анализ включает:*\n"
            "• Тренд H1/H4 (EMA)\n"
            "• RSI, MACD, Bollinger Bands\n"
            "• Уровни поддержки/сопротивления\n"
            "• Свечные паттерны\n"
            "• ATR для стоп-лоссов\n\n"
            "🚀 *Автоматически:*\n"
            f"• Проверка каждые {CHECK_INTERVAL} сек\n"
            "• Сигналы при уверенности >60%\n"
            "• Графики с точками входа"
        )
        
        await update.message.reply_text(
            help_text,
            parse_mode='Markdown',
            reply_markup=self.create_keyboard()
        )
    
    # ========== AUTO ANALYSIS LOOP ==========
    
    def auto_analysis_loop(self):
        """Automatic real-time analysis loop"""
        self.running = True
        logger.info("🚀 Авто-цикл анализа запущен")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        check_counter = 0
        
        while self.running:
            try:
                check_counter += 1
                
                # Log every 10th check
                if check_counter % 10 == 0:
                    logger.info(f"🔍 Авто-проверка #{check_counter}")
                
                # Analyze each symbol
                signals_sent = 0
                for symbol in SYMBOLS:
                    try:
                        analysis = TechnicalAnalyzer.analyze_symbol(symbol)
                        if analysis and analysis['trading_signal']:
                            signal = analysis['trading_signal']
                            
                            # Check signal conditions
                            if signal['action'] != 'HOLD' and signal['confidence'] > 70:
                                # Avoid duplicate signals (same symbol + action within 1 hour)
                                signal_key = f"{symbol}_{signal['action']}_{datetime.now().strftime('%H')}"
                                
                                if signal_key not in self.last_signals:
                                    self.last_signals[signal_key] = datetime.now()
                                    
                                    # Send signal
                                    success = loop.run_until_complete(
                                        self.send_real_signal_with_chart(analysis)
                                    )
                                    
                                    if success:
                                        signals_sent += 1
                                        time.sleep(2)  # Rate limiting
                                        
                    except Exception as e:
                        logger.error(f"Ошибка авто-анализа {symbol}: {e}")
                
                # Clean old signals (older than 1 hour)
                current_time = datetime.now()
                self.last_signals = {
                    k: v for k, v in self.last_signals.items() 
                    if current_time - v < timedelta(hours=1)
                }
                
                # Sleep until next check
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
        """Telegram polling loop"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            self.application = Application.builder().token(self.token).build()
            
            # Add command handlers
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CommandHandler("help", self.help_command))
            self.application.add_handler(CommandHandler("status", self.status_command))
            self.application.add_handler(CommandHandler("analysis", self.analysis_command))
            self.application.add_handler(CommandHandler("signal", self.signal_command))
            
            # Add button handler
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.button_handler))
            
            logger.info("📱 Telegram polling запущен")
            
            # Start polling
            self.application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
                close_loop=False
            )
            
        except Exception as e:
            logger.error(f"❌ Критическая ошибка Telegram: {e}")
            # Try to restart after 30 seconds
            time.sleep(30)
            self.telegram_polling_loop()
    
    def run(self):
        """Main bot run method"""
        logger.info("🚀 Запуск Trading Bot PRO на Render...")
        
        print("\n" + "="*70)
        print("🤖 TRADING BOT PRO (YAHOO FINANCE)")
        print("="*70)
        print(f"📊 Источник: Yahoo Finance")
        print(f"📈 Инструменты: {len(SYMBOLS)}")
        print(f"⏱ Интервал: {CHECK_INTERVAL} сек")
        print(f"🌐 Flask порт: {PORT}")
        print(f"🚀 Хостинг: Render.com")
        print("="*70)
        print("📱 Инструкция:")
        print("  1. Напишите /start для активации")
        print("  2. Используйте кнопки для анализа")
        print("  3. Авто-сигналы при уверенности >70%")
        print("  4. Графики с точками входа")
        print("="*70 + "\n")
        
        # Start Flask
        flask_thread = threading.Thread(target=start_flask, daemon=True)
        flask_thread.start()
        logger.info(f"🌐 Flask запущен на порту {PORT}")
        
        # Start Telegram
        tg_thread = threading.Thread(target=self.telegram_polling_loop, daemon=True)
        tg_thread.start()
        
        time.sleep(3)
        
        # Start auto-analysis
        analysis_thread = threading.Thread(target=self.auto_analysis_loop, daemon=True)
        analysis_thread.start()
        
        logger.info("✅ Trading Bot PRO успешно запущен!")
        logger.info("📡 Ожидание сигналов с Yahoo Finance...")
        
        # Main loop
        try:
            while True:
                time.sleep(10)
                # Check if Flask is still running
                if not flask_thread.is_alive():
                    logger.warning("⚠️ Flask thread упал, перезапускаем...")
                    flask_thread = threading.Thread(target=start_flask, daemon=True)
                    flask_thread.start()
                    time.sleep(2)
                    
        except KeyboardInterrupt:
            self.running = False
            print("\n👋 Бот остановлен\n")
            sys.exit(0)

if __name__ == "__main__":
    bot = TradingBot()
    bot.run()