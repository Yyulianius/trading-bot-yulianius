#!/usr/bin/env python3
"""
REAL Trading Bot with MT5 Alpari - Version WITHOUT TA-Lib
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
warnings.filterwarnings('ignore')

# Flask
from flask import Flask, jsonify

# Telegram
from telegram import Bot, Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# Data Analysis
import pandas as pd
import numpy as np
import MetaTrader5 as mt5

# Charts
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image

# Configuration
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')
TELEGRAM_CHAT_ID = int(os.getenv('TELEGRAM_CHAT_ID', '1037258513'))
MT5_LOGIN = int(os.getenv('MT5_LOGIN', '52754246'))
MT5_PASSWORD = os.getenv('MT5_PASSWORD', '')
MT5_SERVER = os.getenv('MT5_SERVER', 'Alpari-MT5-Demo')

SYMBOLS = ['XAUUSD', 'XAGUSD', 'EURUSD', 'GBPUSD', 'NZDUSD', 'USDCAD', 'USDCHF', 'AUDUSD']
TIMEFRAMES = {
    'M15': mt5.TIMEFRAME_M15,
    'H1': mt5.TIMEFRAME_H1,
    'H4': mt5.TIMEFRAME_H4,
    'D1': mt5.TIMEFRAME_D1
}

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
        'service': 'MT5 Trading Bot Pro',
        'broker': 'Alpari-MT5-Demo',
        'symbols': SYMBOLS,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'mt5_connected': mt5_connected()}), 200

def mt5_connected():
    """Check MT5 connection"""
    try:
        return mt5.initialize(login=MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER)
    except:
        return False

def start_flask():
    """Start Flask server"""
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

class MT5DataFetcher:
    """MT5 Data Fetcher"""
    
    @staticmethod
    def fetch_data(symbol, timeframe='H1', bars=100):
        """Fetch real data from MT5"""
        try:
            if not mt5.initialize(login=MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER):
                logger.error(f"MT5 initialize failed for {symbol}")
                return None
            
            tf = TIMEFRAMES.get(timeframe, mt5.TIMEFRAME_H1)
            rates = mt5.copy_rates_from_pos(symbol, tf, 0, bars)
            mt5.shutdown()
            
            if rates is None or len(rates) == 0:
                logger.warning(f"No data for {symbol}")
                return None
            
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)
            
            # Rename columns to standard names
            df.rename(columns={
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'tick_volume': 'Volume'
            }, inplace=True)
            
            return df[['Open', 'High', 'Low', 'Close', 'Volume']]
            
        except Exception as e:
            logger.error(f"Error fetching {symbol}: {e}")
            return None
    
    @staticmethod
    def get_current_price(symbol):
        """Get current bid/ask price"""
        try:
            if not mt5.initialize(login=MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER):
                return None
            
            tick = mt5.symbol_info_tick(symbol)
            mt5.shutdown()
            
            if tick:
                return {
                    'bid': tick.bid,
                    'ask': tick.ask,
                    'spread': tick.ask - tick.bid
                }
            return None
        except:
            return None

class TechnicalAnalyzer:
    """Professional Technical Analysis WITHOUT TA-Lib"""
    
    @staticmethod
    def analyze_symbol(symbol):
        """Complete analysis for a symbol"""
        try:
            # Fetch data for different timeframes
            h1_data = MT5DataFetcher.fetch_data(symbol, 'H1', 100)
            h4_data = MT5DataFetcher.fetch_data(symbol, 'H4', 50)
            
            if h1_data is None or h4_data is None:
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
            
            # 4. Candlestick Patterns (без TA-Lib)
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
        """Determine trend direction WITHOUT TA-Lib"""
        if data.empty or len(data) < 20:
            return "Недостаточно данных"
        
        close = data['Close']
        
        # Calculate EMAs manually
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
        """RSI analysis WITHOUT TA-Lib"""
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
        """MACD analysis WITHOUT TA-Lib"""
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
        """Bollinger Bands analysis WITHOUT TA-Lib"""
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
        """Calculate Average True Range WITHOUT TA-Lib"""
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
        """Detect simple candlestick patterns WITHOUT TA-Lib"""
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
    """Generate trading charts WITHOUT mplfinance"""
    
    @staticmethod
    def create_candlestick_chart(data, symbol, signal=None, sr_levels=None):
        """Create professional candlestick chart WITHOUT mplfinance"""
        try:
            if data.empty or len(data) < 10:
                return None
            
            # Use last 30 candles
            plot_data = data.tail(30).copy()
            
            # Create figure
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), 
                                          gridspec_kw={'height_ratios': [3, 1]})
            
            # Plot candlesticks manually
            for i, (idx, row) in enumerate(plot_data.iterrows()):
                color = 'green' if row['Close'] >= row['Open'] else 'red'
                
                # Plot candle body
                ax1.bar(i, abs(row['Close'] - row['Open']), 
                       bottom=min(row['Open'], row['Close']),
                       width=0.6, color=color, edgecolor=color)
                
                # Plot wicks
                ax1.vlines(i, row['Low'], row['High'], 
                          color=color, linewidth=0.8)
            
            # Add title
            ax1.set_title(f'{symbol} - H1 | MT5 Alpari', fontsize=14, fontweight='bold')
            ax1.set_ylabel('Цена')
            ax1.grid(True, alpha=0.3)
            
            # Plot volume
            ax2.bar(range(len(plot_data)), plot_data['Volume'], color='blue', alpha=0.5)
            ax2.set_xlabel('Свечи (последние 30)')
            ax2.set_ylabel('Объём')
            ax2.grid(True, alpha=0.3)
            
            # Add signal markers if provided
            if signal and signal['action'] != 'HOLD':
                color = 'green' if signal['action'] == 'BUY' else 'red'
                ax1.axhline(y=signal['price'], color=color, linestyle='--', 
                           linewidth=2, alpha=0.7, label=f"Вход: {signal['price']:.5f}")
                
                if signal['sl'] > 0:
                    ax1.axhline(y=signal['sl'], color='red', linestyle=':', 
                               linewidth=1.5, alpha=0.5, label=f"SL: {signal['sl']:.5f}")
                
                if signal['tp'] > 0:
                    ax1.axhline(y=signal['tp'], color='green', linestyle=':', 
                               linewidth=1.5, alpha=0.5, label=f"TP: {signal['tp']:.5f}")
                
                ax1.legend()
            
            # Add support/resistance lines
            if sr_levels:
                for support in sr_levels.get('support', []):
                    if support:
                        ax1.axhline(y=support, color='blue', linestyle='--', 
                                   linewidth=1, alpha=0.3)
                
                for resistance in sr_levels.get('resistance', []):
                    if resistance:
                        ax1.axhline(y=resistance, color='orange', linestyle='--', 
                                   linewidth=1, alpha=0.3)
            
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

class RealTradingBot:
    """Main Trading Bot Class"""
    
    def __init__(self):
        self.token = TELEGRAM_TOKEN
        self.application = None
        self.running = False
        self.chat_id = TELEGRAM_CHAT_ID
        self.last_signals = {}
        
        # Test MT5 connection
        if mt5_connected():
            logger.info("✅ MT5 подключен успешно!")
        else:
            logger.warning("⚠️ MT5 не подключен. Проверьте логин/пароль.")
        
        logger.info("🤖 Real Trading Bot PRO инициализирован (без TA-Lib)")
    
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
        
        # Test MT5 connection
        mt5_status = "✅ ПОДКЛЮЧЕН" if mt5_connected() else "❌ НЕ ПОДКЛЮЧЕН"
        
        welcome = (
            f"🤖 *Real Trading Bot PRO*\n\n"
            f"📊 *Брокер:* MT5 Alpari-Demo\n"
            f"🔗 *Статус MT5:* {mt5_status}\n"
            f"📈 *Инструменты:* {len(SYMBOLS)} валютных пар\n"
            f"⏱ *Частота проверки:* {CHECK_INTERVAL} сек\n"
            f"🌐 *Хостинг:* Render.com\n\n"
            f"✅ *Реальные функции:*\n"
            f"• Живые котировки MT5\n"
            f"• Технический анализ (без TA-Lib)\n"
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
        mt5_status = "🟢 ONLINE" if mt5_connected() else "🔴 OFFLINE"
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Get server time from MT5 if connected
        if mt5_connected():
            try:
                mt5.initialize(login=MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER)
                server_time = mt5.symbol_info_tick('EURUSD').time
                mt5.shutdown()
                server_time_str = datetime.fromtimestamp(server_time).strftime('%H:%M:%S')
            except:
                server_time_str = "Нет данных"
        else:
            server_time_str = "Нет подключения"
        
        status_text = (
            f"🤖 *Статус системы*\n\n"
            f"🟢 *Бот:* Активен\n"
            f"📡 *MT5:* {mt5_status}\n"
            f"🕒 *Время сервера:* {server_time_str}\n"
            f"📊 *Инструменты:* {len(SYMBOLS)}\n"
            f"📈 *Анализ:* Manual (без TA-Lib)\n"
            f"⏱ *Интервал:* {CHECK_INTERVAL} сек\n"
            f"🌐 *Flask порт:* {PORT}\n"
            f"⏰ *Локальное время:* {current_time}"
        )
        
        await update.message.reply_text(
            status_text,
            parse_mode='Markdown',
            reply_markup=self.create_keyboard()
        )
    
    async def analysis_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /analysis"""
        if not mt5_connected():
            await update.message.reply_text(
                "❌ MT5 не подключен. Проверьте логин/пароль.",
                reply_markup=self.create_keyboard()
            )
            return
        
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
        if not mt5_connected():
            await update.message.reply_text(
                "❌ MT5 не подключен. Проверьте логин/пароль.",
                reply_markup=self.create_keyboard()
            )
            return
        
        await update.message.reply_text(
            "🔍 Ищу реальные торговые сигналы...",
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
                f"✅ Найдено {signals_found} реальных сигналов",
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
        
        if not mt5_connected():
            await update.message.reply_text(
                "❌ MT5 не подключен",
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
                chart = ChartGenerator.create_candlestick_chart(
                    analysis['data'], symbol,
                    analysis['trading_signal'],
                    analysis['support_resistance']
                )
                
                if chart:
                    caption = f"📊 {symbol} - H1 | MT5 Alpari"
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
        
        return summary
    
    async def send_real_signal_with_chart(self, analysis):
        """Send real trading signal with chart"""
        try:
            if not self.chat_id:
                return False
            
            symbol = analysis['symbol']
            signal = analysis['trading_signal']
            
            if signal['action'] == 'HOLD' or signal['confidence'] < 60:
                return False
            
            # Generate chart
            chart = ChartGenerator.create_candlestick_chart(
                analysis['data'], symbol,
                signal,
                analysis['support_resistance']
            )
            
            if not chart:
                return False
            
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
            message += f"📡 *Источник:* MT5 Alpari-Demo\n"
            message += f"🚀 *Бот:* Real Trading Bot PRO (без TA-Lib)"
            
            # Send to Telegram
            bot = Bot(token=self.token)
            
            # Send photo with caption
            await bot.send_photo(
                chat_id=self.chat_id,
                photo=chart,
                caption=message,
                parse_mode='Markdown'
            )
            
            logger.info(f"✅ Реальный сигнал отправлен: {symbol} {signal['action']} ({signal['confidence']}%)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки реального сигнала: {e}")
            return False
    
    async def send_test_signal(self, update):
        """Send test signal on start"""
        try:
            # Get XAUUSD data
            data = MT5DataFetcher.fetch_data('XAUUSD', 'H1', 20)
            if data is not None and not data.empty:
                current_price = data['Close'].iloc[-1]
                
                test_signal = {
                    'symbol': 'XAUUSD',
                    'action': 'BUY' if current_price > data['Close'].mean() else 'SELL',
                    'price': round(current_price, 5),
                    'sl': round(current_price * 0.995, 5),
                    'tp': round(current_price * 1.01, 5),
                    'confidence': 85,
                    'reason': ['Тестовый сигнал', 'Проверка связи MT5'],
                    'risk_level': 'LOW'
                }
                
                message = (
                    "🟡 *ТЕСТОВЫЙ СИГНАЛ*\n\n"
                    f"💰 *XAUUSD:* {current_price:.2f}\n"
                    f"📡 *MT5 статус:* {'✅ ПОДКЛЮЧЕН' if mt5_connected() else '❌ ОШИБКА'}\n"
                    f"🌐 *Бот:* Работает на Render.com\n\n"
                    f"✅ *Система готова к реальным сигналам!*"
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
            "🤖 *Real Trading Bot PRO - Команды*\n\n"
            "📋 *Основные команды:*\n"
            "/start - Активация и проверка MT5\n"
            "/status - Статус системы и MT5\n"
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
            "• Простые свечные паттерны\n"
            "• ATR для стоп-лоссов\n\n"
            "🚀 *Автоматически:*\n"
            f"• Проверка каждые {CHECK_INTERVAL} сек\n"
            "• Реальные сигналы при уверенности >60%\n"
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
        logger.info("🚀 Авто-цикл реального анализа запущен")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        check_counter = 0
        
        while self.running:
            try:
                check_counter += 1
                
                # Log every 10th check
                if check_counter % 10 == 0:
                    logger.info(f"🔍 Авто-проверка #{check_counter}")
                
                # Check MT5 connection
                if not mt5_connected():
                    logger.warning("⚠️ MT5 отключен, пропускаем проверку")
                    time.sleep(30)
                    continue
                
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
        logger.info("🚀 Запуск Real Trading Bot PRO на Render...")
        
        print("\n" + "="*70)
        print("🤖 REAL TRADING BOT PRO (MT5 ALPARI)")
        print("="*70)
        print(f"📊 Брокер: Alpari-MT5-Demo")
        print(f"📈 Инструменты: {len(SYMBOLS)}")
        print(f"⏱ Интервал: {CHECK_INTERVAL} сек")
        print(f"📡 MT5 Login: {MT5_LOGIN}")
        print(f"🌐 Flask порт: {PORT}")
        print(f"🚀 Хостинг: Render.com")
        print(f"📊 Анализ: БЕЗ TA-Lib (ручной расчёт)")
        print("="*70)
        print("📱 Инструкция:")
        print("  1. Напишите /start для проверки MT5")
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
        
        logger.info("✅ Real Trading Bot PRO успешно запущен!")
        logger.info("📡 Ожидание реальных сигналов с MT5...")
        
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
    bot = RealTradingBot()
    bot.run()