"""
Advanced Trading Strategy with Multi-Indicator Confluence System
Requires 75% confidence score for high-accuracy signals
"""
import pandas as pd
import numpy as np
from ta.trend import EMAIndicator, ADXIndicator, MACD
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator, VolumeWeightedAveragePrice
from typing import Dict, Optional, Tuple
from datetime import datetime
from config import config
from logger import logger

class TradingStrategy:
    """Multi-indicator confluence trading strategy"""

    def __init__(self):
        self.weights = config.STRATEGY_WEIGHTS
        self.signal_threshold = config.SIGNAL_THRESHOLD
        self.last_signal = None
        self.last_signal_time = None

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators"""
        if df is None or len(df) < config.EMA_SLOW:
            return df

        df = df.copy()

        try:
            # Trend Indicators
            df['ema_20'] = EMAIndicator(df['close'], window=config.EMA_FAST).ema_indicator()
            df['ema_50'] = EMAIndicator(df['close'], window=config.EMA_MEDIUM).ema_indicator()
            df['ema_200'] = EMAIndicator(df['close'], window=config.EMA_SLOW).ema_indicator()

            # ADX for trend strength
            adx = ADXIndicator(df['high'], df['low'], df['close'], window=config.ADX_PERIOD)
            df['adx'] = adx.adx()
            df['adx_pos'] = adx.adx_pos()
            df['adx_neg'] = adx.adx_neg()

            # Supertrend
            df = self.calculate_supertrend(df)

            # Momentum Indicators
            df['rsi'] = RSIIndicator(df['close'], window=config.RSI_PERIOD).rsi()

            # MACD
            macd = MACD(df['close'],
                       window_fast=config.MACD_FAST,
                       window_slow=config.MACD_SLOW,
                       window_sign=config.MACD_SIGNAL)
            df['macd'] = macd.macd()
            df['macd_signal'] = macd.macd_signal()
            df['macd_histogram'] = macd.macd_diff()

            # Stochastic
            stoch = StochasticOscillator(df['high'], df['low'], df['close'],
                                        window=config.STOCH_K,
                                        smooth_window=config.STOCH_D)
            df['stoch_k'] = stoch.stoch()
            df['stoch_d'] = stoch.stoch_signal()

            # Volatility Indicators
            df['atr'] = AverageTrueRange(df['high'], df['low'], df['close'],
                                        window=config.ATR_PERIOD).average_true_range()

            bb = BollingerBands(df['close'], window=config.BB_PERIOD, window_dev=config.BB_STD)
            df['bb_upper'] = bb.bollinger_hband()
            df['bb_middle'] = bb.bollinger_mavg()
            df['bb_lower'] = bb.bollinger_lband()
            df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']

            # Volume Indicators
            df['obv'] = OnBalanceVolumeIndicator(df['close'], df['volume']).on_balance_volume()
            df['volume_sma'] = df['volume'].rolling(window=config.VOLUME_PERIOD).mean()

            # Support/Resistance
            df = self.calculate_pivot_points(df)

            logger.debug(f"Calculated {len(df.columns)} indicators")

        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")

        return df

    def calculate_supertrend(self, df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> pd.DataFrame:
        """Calculate Supertrend indicator"""
        df = df.copy()

        # Calculate ATR
        atr = AverageTrueRange(df['high'], df['low'], df['close'], window=period).average_true_range()

        # Calculate basic upper and lower bands
        hl_avg = (df['high'] + df['low']) / 2
        upper_band = hl_avg + (multiplier * atr)
        lower_band = hl_avg - (multiplier * atr)

        # Initialize supertrend
        supertrend = pd.Series(index=df.index, dtype=float)
        direction = pd.Series(index=df.index, dtype=int)

        for i in range(1, len(df)):
            if df['close'].iloc[i] > upper_band.iloc[i-1]:
                direction.iloc[i] = 1
            elif df['close'].iloc[i] < lower_band.iloc[i-1]:
                direction.iloc[i] = -1
            else:
                direction.iloc[i] = direction.iloc[i-1]

                if direction.iloc[i] == 1 and lower_band.iloc[i] < lower_band.iloc[i-1]:
                    lower_band.iloc[i] = lower_band.iloc[i-1]
                if direction.iloc[i] == -1 and upper_band.iloc[i] > upper_band.iloc[i-1]:
                    upper_band.iloc[i] = upper_band.iloc[i-1]

            supertrend.iloc[i] = lower_band.iloc[i] if direction.iloc[i] == 1 else upper_band.iloc[i]

        df['supertrend'] = supertrend
        df['supertrend_direction'] = direction

        return df

    def calculate_pivot_points(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate pivot points for support/resistance"""
        df = df.copy()

        # Standard pivot points
        df['pivot'] = (df['high'] + df['low'] + df['close']) / 3
        df['r1'] = 2 * df['pivot'] - df['low']
        df['s1'] = 2 * df['pivot'] - df['high']
        df['r2'] = df['pivot'] + (df['high'] - df['low'])
        df['s2'] = df['pivot'] - (df['high'] - df['low'])

        return df

    def analyze_trend(self, df: pd.DataFrame) -> Tuple[float, Dict]:
        """Analyze trend strength and direction (35 points max - optimized for futures)"""
        if df is None or len(df) < 2:
            return 0, {}

        score = 0
        details = {}
        latest = df.iloc[-1]

        # EMA Alignment (17 points) - More weight for trend
        ema_bullish = (latest['ema_20'] > latest['ema_50'] > latest['ema_200'])
        ema_bearish = (latest['ema_20'] < latest['ema_50'] < latest['ema_200'])

        if ema_bullish:
            score += 17
            details['ema_alignment'] = 'bullish'
        elif ema_bearish:
            score -= 17
            details['ema_alignment'] = 'bearish'
        else:
            details['ema_alignment'] = 'mixed'

        # Price vs EMAs (9 points)
        if latest['close'] > latest['ema_20']:
            score += 9
            details['price_position'] = 'above_ema20'
        else:
            score -= 9
            details['price_position'] = 'below_ema20'

        # ADX Strength (6 points)
        if latest['adx'] > config.ADX_THRESHOLD:
            if latest['adx_pos'] > latest['adx_neg']:
                score += 6
                details['adx_strength'] = f'strong_bullish_{latest["adx"]:.1f}'
            else:
                score -= 6
                details['adx_strength'] = f'strong_bearish_{latest["adx"]:.1f}'
        else:
            details['adx_strength'] = f'weak_{latest["adx"]:.1f}'

        # Supertrend (3 points) - reduced weight
        if 'supertrend_direction' in df.columns:
            if latest['supertrend_direction'] == 1:
                score += 3
                details['supertrend'] = 'bullish'
            elif latest['supertrend_direction'] == -1:
                score -= 3
                details['supertrend'] = 'bearish'

        # Normalize to 0-35 range
        trend_score = max(-35, min(35, score))

        return trend_score, details

    def analyze_momentum(self, df: pd.DataFrame) -> Tuple[float, Dict]:
        """Analyze momentum indicators (30 points max - optimized for futures)"""
        if df is None or len(df) < 2:
            return 0, {}

        score = 0
        details = {}
        latest = df.iloc[-1]
        prev = df.iloc[-2]

        # RSI Analysis (12 points) - increased for momentum
        rsi = latest['rsi']
        if 40 <= rsi <= 60:
            # Neutral zone - good for entry
            score += 12
            details['rsi'] = f'neutral_{rsi:.1f}'
        elif 35 < rsi < 40:
            # Slightly oversold - bullish
            score += 8
            details['rsi'] = f'oversold_{rsi:.1f}'
        elif 60 < rsi < 65:
            # Slightly overbought - bearish
            score -= 8
            details['rsi'] = f'overbought_{rsi:.1f}'
        elif rsi <= 35:
            score -= 12
            details['rsi'] = f'very_oversold_{rsi:.1f}'
        elif rsi >= 65:
            score -= 12
            details['rsi'] = f'very_overbought_{rsi:.1f}'

        # MACD Analysis (10 points) - increased
        if latest['macd'] > latest['macd_signal']:
            if latest['macd_histogram'] > prev['macd_histogram']:
                score += 10
                details['macd'] = 'bullish_expanding'
            else:
                score += 5
                details['macd'] = 'bullish_contracting'
        else:
            if latest['macd_histogram'] < prev['macd_histogram']:
                score -= 10
                details['macd'] = 'bearish_expanding'
            else:
                score -= 5
                details['macd'] = 'bearish_contracting'

        # Stochastic Analysis (8 points) - increased
        if latest['stoch_k'] > latest['stoch_d']:
            if latest['stoch_k'] < 80:
                score += 8
                details['stochastic'] = f'bullish_cross_{latest["stoch_k"]:.1f}'
            else:
                details['stochastic'] = f'overbought_{latest["stoch_k"]:.1f}'
        else:
            if latest['stoch_k'] > 20:
                score -= 8
                details['stochastic'] = f'bearish_cross_{latest["stoch_k"]:.1f}'
            else:
                details['stochastic'] = f'oversold_{latest["stoch_k"]:.1f}'

        # Normalize to 0-30 range
        momentum_score = max(-30, min(30, score))

        return momentum_score, details

    def analyze_volume(self, df: pd.DataFrame) -> Tuple[float, Dict]:
        """Analyze volume patterns (15 points max)"""
        if df is None or len(df) < 2:
            return 0, {}

        score = 0
        details = {}
        latest = df.iloc[-1]
        prev = df.iloc[-2]

        # Volume spike analysis (8 points)
        volume_ratio = latest['volume'] / latest['volume_sma']
        if volume_ratio > config.MIN_VOLUME_MULTIPLIER:
            if latest['close'] > latest['open']:
                score += 8
                details['volume_spike'] = f'bullish_{volume_ratio:.2f}x'
            else:
                score -= 8
                details['volume_spike'] = f'bearish_{volume_ratio:.2f}x'
        else:
            details['volume_spike'] = f'low_{volume_ratio:.2f}x'

        # OBV trend (7 points)
        if latest['obv'] > prev['obv']:
            score += 7
            details['obv'] = 'increasing'
        else:
            score -= 7
            details['obv'] = 'decreasing'

        # Normalize to 0-15 range
        volume_score = max(-15, min(15, score))

        return volume_score, details

    def analyze_market_structure(self, df: pd.DataFrame) -> Tuple[float, Dict]:
        """Analyze support/resistance and market structure (10 points max - reduced)"""
        if df is None or len(df) < 5:
            return 0, {}

        score = 0
        details = {}
        latest = df.iloc[-1]

        # Check price position relative to pivot points (5 points) - reduced
        if latest['close'] > latest['r1']:
            score += 5
            details['pivot_position'] = 'above_r1'
        elif latest['close'] > latest['pivot']:
            score += 3
            details['pivot_position'] = 'above_pivot'
        elif latest['close'] < latest['s1']:
            score -= 5
            details['pivot_position'] = 'below_s1'
        elif latest['close'] < latest['pivot']:
            score -= 3
            details['pivot_position'] = 'below_pivot'

        # Higher highs and higher lows check (5 points) - reduced
        recent = df.tail(5)
        highs = recent['high'].values
        lows = recent['low'].values

        higher_highs = all(highs[i] >= highs[i-1] for i in range(1, len(highs)))
        higher_lows = all(lows[i] >= lows[i-1] for i in range(1, len(lows)))
        lower_highs = all(highs[i] <= highs[i-1] for i in range(1, len(highs)))
        lower_lows = all(lows[i] <= lows[i-1] for i in range(1, len(lows)))

        if higher_highs and higher_lows:
            score += 5
            details['structure'] = 'uptrend'
        elif lower_highs and lower_lows:
            score -= 5
            details['structure'] = 'downtrend'
        else:
            details['structure'] = 'ranging'

        # Normalize to 0-10 range
        structure_score = max(-10, min(10, score))

        return structure_score, details

    def analyze_volatility(self, df: pd.DataFrame) -> Tuple[float, Dict]:
        """Analyze volatility conditions (5 points max - reduced for futures)"""
        if df is None or len(df) < 2:
            return 0, {}

        score = 0
        details = {}
        latest = df.iloc[-1]
        prev = df.iloc[-2]

        # Bollinger Bands analysis (3 points) - reduced
        bb_position = (latest['close'] - latest['bb_lower']) / (latest['bb_upper'] - latest['bb_lower'])

        if 0.4 <= bb_position <= 0.6:
            score += 3
            details['bb_position'] = f'middle_{bb_position:.2f}'
        elif bb_position < 0.2:
            score -= 3
            details['bb_position'] = f'lower_{bb_position:.2f}'
        elif bb_position > 0.8:
            score -= 3
            details['bb_position'] = f'upper_{bb_position:.2f}'

        # BB Squeeze/Expansion (2 points) - reduced
        if latest['bb_width'] > prev['bb_width']:
            score += 2
            details['bb_width'] = 'expanding'
        else:
            details['bb_width'] = 'contracting'

        # ATR check
        details['atr'] = f'{latest["atr"]:.2f}'

        # Normalize to 0-5 range
        volatility_score = max(-5, min(5, score))

        return volatility_score, details

    def analyze_sentiment(self, market_data: Dict) -> Tuple[float, Dict]:
        """Analyze market sentiment (5 points max)"""
        score = 0
        details = {}

        # Funding rate analysis (3 points)
        funding_rate = market_data.get('funding_rate', 0)
        if abs(funding_rate) < config.MAX_FUNDING_RATE * 0.5:
            # Neutral funding - good
            score += 3
            details['funding'] = f'neutral_{funding_rate:.4f}'
        elif funding_rate < -config.MAX_FUNDING_RATE:
            # Very negative - potential reversal
            score += 2
            details['funding'] = f'very_negative_{funding_rate:.4f}'
        elif funding_rate > config.MAX_FUNDING_RATE:
            # Very positive - potential reversal
            score -= 2
            details['funding'] = f'very_positive_{funding_rate:.4f}'

        # Sonar sentiment (2 points)
        sentiment = market_data.get('sentiment', {})
        sentiment_score = sentiment.get('score', 0)

        if sentiment_score > 0:
            score += 2
            details['sonar'] = 'bullish'
        elif sentiment_score < 0:
            score -= 2
            details['sonar'] = 'bearish'
        else:
            details['sonar'] = 'neutral'

        # Normalize to 0-5 range
        sentiment_score = max(-5, min(5, score))

        return sentiment_score, details

    def check_higher_timeframes(self, market_data: Dict) -> Tuple[bool, str]:
        """Check higher timeframe trend confirmation"""
        if not config.USE_MULTIPLE_TIMEFRAMES:
            return True, "Multiple timeframes disabled"
        
        reasons = []
        
        # Check 1h timeframe
        df_1h = market_data.get('ohlcv_1h')
        if df_1h is not None and len(df_1h) >= 50:
            df_1h = self.calculate_indicators(df_1h)
            latest_1h = df_1h.iloc[-1]
            
            # Check 1h trend
            if latest_1h['ema_20'] > latest_1h['ema_50']:
                reasons.append("1h: Uptrend ✅")
                tf_1h_bullish = True
            elif latest_1h['ema_20'] < latest_1h['ema_50']:
                reasons.append("1h: Downtrend ❌")
                tf_1h_bullish = False
            else:
                reasons.append("1h: Neutral")
                tf_1h_bullish = None
        else:
            tf_1h_bullish = None
            reasons.append("1h: No data")
        
        # Check 4h timeframe
        df_4h = market_data.get('ohlcv_4h')
        if df_4h is not None and len(df_4h) >= 50:
            df_4h = self.calculate_indicators(df_4h)
            latest_4h = df_4h.iloc[-1]
            
            # Check 4h trend
            if latest_4h['ema_20'] > latest_4h['ema_50']:
                reasons.append("4h: Uptrend ✅")
                tf_4h_bullish = True
            elif latest_4h['ema_20'] < latest_4h['ema_50']:
                reasons.append("4h: Downtrend ❌")
                tf_4h_bullish = False
            else:
                reasons.append("4h: Neutral")
                tf_4h_bullish = None
        else:
            tf_4h_bullish = None
            reasons.append("4h: No data")
        
        # Return True if at least one higher TF confirms or no data
        reason_str = "; ".join(reasons)
        
        if tf_1h_bullish is None and tf_4h_bullish is None:
            return True, reason_str  # No data, allow trade
        
        # If we have data, at least one should be bullish
        has_confirmation = (tf_1h_bullish == True or tf_4h_bullish == True)
        has_conflict = (tf_1h_bullish == False or tf_4h_bullish == False)
        
        if has_confirmation and not has_conflict:
            return True, reason_str
        else:
            return False, reason_str
    
    def check_market_regime(self, df: pd.DataFrame) -> Tuple[bool, str]:
        """Check if market is in trending regime"""
        if not config.USE_MARKET_REGIME_FILTER:
            return True, "Regime filter disabled"
        
        if df is None or len(df) < 2:
            return False, "Insufficient data"
        
        latest = df.iloc[-1]
        
        # Check ADX for trend strength
        adx = latest.get('adx', 0)
        
        if adx >= config.REGIME_ADX_THRESHOLD:
            return True, f"Trending market (ADX: {adx:.1f})"
        else:
            return False, f"Ranging market (ADX: {adx:.1f} < {config.REGIME_ADX_THRESHOLD})"
    
    def generate_signal(self, market_data: Dict) -> Dict:
        """Generate trading signal with confluence scoring"""
        df = market_data.get('ohlcv')

        if df is None or len(df) < config.EMA_SLOW:
            return {
                'signal': 'HOLD',
                'score': 0,
                'confidence': 0,
                'details': {'error': 'Insufficient data'}
            }

        # Calculate all indicators
        df = self.calculate_indicators(df)

        # Analyze each component
        trend_score, trend_details = self.analyze_trend(df)
        momentum_score, momentum_details = self.analyze_momentum(df)
        volume_score, volume_details = self.analyze_volume(df)
        structure_score, structure_details = self.analyze_market_structure(df)
        volatility_score, volatility_details = self.analyze_volatility(df)
        sentiment_score, sentiment_details = self.analyze_sentiment(market_data)

        # Calculate weighted total score
        total_score = (
            trend_score +
            momentum_score +
            volume_score +
            structure_score +
            volatility_score +
            sentiment_score
        )

        # Convert to percentage (max possible: 35+30+15+10+5+5 = 100)
        max_score = sum(self.weights.values())
        confidence = (total_score / max_score) * 100 if max_score > 0 else 0

        # Apply filters
        filter_passed, filter_reason = self.apply_filters(df, market_data)
        
        # Check market regime (NEW)
        regime_ok, regime_reason = self.check_market_regime(df)
        
        # Check higher timeframes (NEW)
        tf_confirmed, tf_reason = self.check_higher_timeframes(market_data)

        # Determine signal
        if confidence >= self.signal_threshold and filter_passed and regime_ok and tf_confirmed:
            signal = 'BUY'
        elif confidence <= -self.signal_threshold and filter_passed and regime_ok and tf_confirmed:
            signal = 'SELL'
        else:
            signal = 'HOLD'

        # Log signal
        latest_price = df.iloc[-1]['close']

        result = {
            'signal': signal,
            'score': total_score,
            'confidence': abs(confidence),
            'price': latest_price,
            'timestamp': datetime.now().isoformat(),
            'components': {
                'trend': {'score': trend_score, 'details': trend_details},
                'momentum': {'score': momentum_score, 'details': momentum_details},
                'volume': {'score': volume_score, 'details': volume_details},
                'structure': {'score': structure_score, 'details': structure_details},
                'volatility': {'score': volatility_score, 'details': volatility_details},
                'sentiment': {'score': sentiment_score, 'details': sentiment_details}
            },
            'filter_passed': filter_passed,
            'filter_reason': filter_reason,
            'regime_ok': regime_ok,
            'regime_reason': regime_reason,
            'timeframe_confirmed': tf_confirmed,
            'timeframe_reason': tf_reason
        }

        if signal != 'HOLD':
            logger.info(
                f"🎯 Signal Generated: {signal} | "
                f"Confidence: {abs(confidence):.1f}% | "
                f"Price: ${latest_price:.2f}"
            )

        self.last_signal = result
        self.last_signal_time = datetime.now()

        return result

    def apply_filters(self, df: pd.DataFrame, market_data: Dict) -> Tuple[bool, str]:
        """Apply quality filters to signals"""
        reasons = []

        # Volume filter
        latest = df.iloc[-1]
        volume_ratio = latest['volume'] / latest['volume_sma']

        if volume_ratio < config.MIN_VOLUME_MULTIPLIER:
            reasons.append(f"Low volume: {volume_ratio:.2f}x")

        # Funding rate filter
        funding_rate = market_data.get('funding_rate', 0)
        if abs(funding_rate) > config.MAX_FUNDING_RATE:
            reasons.append(f"High funding rate: {funding_rate:.4f}")

        # Time filter - avoid low volume hours
        from datetime import datetime
        current_hour = datetime.utcnow().hour
        if current_hour in config.LOW_VOLUME_HOURS:
            reasons.append("Low volume time period")

        filter_passed = len(reasons) == 0
        filter_reason = '; '.join(reasons) if reasons else 'All filters passed'

        return filter_passed, filter_reason

# Create global strategy instance
strategy = TradingStrategy()

