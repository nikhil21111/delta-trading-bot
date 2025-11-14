"""
Data Manager for Delta Exchange
Handles market data fetching and processing for futures trading
"""
import asyncio
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional
import aiohttp

from config import config
from logger import logger
from delta_exchange import DeltaExchange

class DataManagerDelta:
    """Data manager for Delta Exchange futures"""
    
    def __init__(self):
        self.exchange = DeltaExchange(config.DELTA_API_KEY, config.DELTA_API_SECRET)
        self.last_candle_time = None
        self.cache = {}
        self.cache_time = {}
        
    async def __aenter__(self):
        await self.exchange.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.exchange.__aexit__(exc_type, exc_val, exc_tb)
    
    def _parse_timeframe(self, timeframe: str) -> int:
        """Convert timeframe to minutes"""
        unit = timeframe[-1]
        value = int(timeframe[:-1])
        
        if unit == 'm':
            return value
        elif unit == 'h':
            return value * 60
        elif unit == 'd':
            return value * 1440
        else:
            return 15  # Default 15m
    
    async def fetch_ticker(self, symbol: str = None) -> Optional[Dict]:
        """Fetch current ticker data"""
        if symbol is None:
            symbol = config.TRADING_PAIR
            
        try:
            ticker = await self.exchange.get_ticker(symbol)
            return ticker
        except Exception as e:
            logger.error(f"Failed to fetch ticker: {e}")
            return None
    
    async def fetch_ohlcv(self, symbol: str = None, timeframe: str = None, limit: int = 200) -> Optional[pd.DataFrame]:
        """
        Fetch OHLCV candlestick data
        
        Note: Delta Exchange API returns candles data through /v2/history/candles endpoint
        """
        if symbol is None:
            symbol = config.TRADING_PAIR
        if timeframe is None:
            timeframe = config.TIMEFRAME
            
        try:
            # Convert timeframe to resolution
            resolution = timeframe
            
            # Get product ID
            products = await self.exchange.get_products()
            product_id = None
            
            if products:
                for product in products:
                    if product.get('symbol') == symbol:
                        product_id = product.get('id')
                        break
            
            if not product_id:
                logger.error(f"Product not found: {symbol}")
                logger.error(f"Available products: {[p.get('symbol') for p in (products or [])[:10]]}")
                return None
            
            # Calculate time range
            minutes = self._parse_timeframe(timeframe)
            end_time = int(datetime.now().timestamp())
            start_time = end_time - (limit * minutes * 60)
            
            # Fetch candles from Delta Exchange
            endpoint = f"/v2/history/candles"
            params = {
                'resolution': resolution,
                'symbol': symbol,
                'start': start_time,
                'end': end_time
            }
            
            logger.debug(f"Fetching candles: {endpoint} with params: {params}")
            
            data = await self.exchange._public_request(endpoint, params)
            
            if not data:
                logger.error("No response from Delta Exchange candles API")
                return None
            
            # Check for API errors
            if 'error' in data:
                logger.error(f"Delta Exchange API error: {data['error']}")
                logger.error(f"Full response: {data}")
                return None
            
            if 'result' not in data:
                logger.error(f"Unexpected response format from Delta Exchange: {list(data.keys())}")
                logger.error(f"Full response: {data}")
                return None
            
            # Parse candles
            candles = data['result']
            
            if not candles or len(candles) == 0:
                logger.warning(f"No candles returned for {symbol} {timeframe} (limit: {limit})")
                logger.warning(f"Time range: {datetime.fromtimestamp(start_time)} to {datetime.fromtimestamp(end_time)}")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(candles)
            
            logger.debug(f"Received candles with columns: {df.columns.tolist()}")
            
            # Rename columns to standard format
            df = df.rename(columns={
                'time': 'timestamp',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            })
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            
            # Sort by timestamp
            df = df.sort_values('timestamp')
            df = df.reset_index(drop=True)
            
            # Ensure numeric types
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            logger.debug(f"Fetched {len(df)} candles for {symbol}")
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch OHLCV: {e}")
            return None
    
    async def fetch_order_book(self, symbol: str = None) -> Optional[Dict]:
        """Fetch order book data"""
        if symbol is None:
            symbol = config.TRADING_PAIR
            
        try:
            # Delta Exchange order book endpoint
            endpoint = f"/v2/l2orderbook/{symbol}"
            data = await self.exchange._public_request(endpoint)
            
            if data and 'result' in data:
                book = data['result']
                return {
                    'bids': book.get('buy', []),
                    'asks': book.get('sell', []),
                    'timestamp': book.get('timestamp')
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to fetch order book: {e}")
            return None
    
    async def get_market_data(self, symbol: str = None) -> Dict:
        """
        Get comprehensive market data including multiple timeframes
        
        Returns:
            Dict with keys: ohlcv, ohlcv_1h, ohlcv_4h, ticker, order_book, funding_rate
        """
        if symbol is None:
            symbol = config.TRADING_PAIR
            
        market_data = {
            'symbol': symbol,
            'ohlcv': None,
            'ohlcv_1h': None,
            'ohlcv_4h': None,
            'ticker': None,
            'order_book': None,
            'funding_rate': None
        }
        
        try:
            # Fetch all data concurrently
            tasks = [
                self.fetch_ohlcv(symbol, config.TIMEFRAME),
                self.fetch_ticker(symbol),
                self.fetch_order_book(symbol),
                self.get_funding_rate(symbol)
            ]
            
            # Add higher timeframes if enabled
            if config.USE_MULTIPLE_TIMEFRAMES:
                tasks.insert(1, self.fetch_ohlcv(symbol, config.TIMEFRAME_HIGHER_1))
                tasks.insert(2, self.fetch_ohlcv(symbol, config.TIMEFRAME_HIGHER_2))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            idx = 0
            market_data['ohlcv'] = results[idx] if not isinstance(results[idx], Exception) else None
            idx += 1
            
            if config.USE_MULTIPLE_TIMEFRAMES:
                market_data['ohlcv_1h'] = results[idx] if not isinstance(results[idx], Exception) else None
                idx += 1
                market_data['ohlcv_4h'] = results[idx] if not isinstance(results[idx], Exception) else None
                idx += 1
            
            market_data['ticker'] = results[idx] if not isinstance(results[idx], Exception) else None
            idx += 1
            market_data['order_book'] = results[idx] if not isinstance(results[idx], Exception) else None
            idx += 1
            market_data['funding_rate'] = results[idx] if not isinstance(results[idx], Exception) else None
            
            return market_data
            
        except Exception as e:
            logger.error(f"Failed to get market data: {e}")
            return market_data
    
    async def get_funding_rate(self, symbol: str = None) -> Optional[float]:
        """Get current funding rate for perpetual contract"""
        if symbol is None:
            symbol = config.TRADING_PAIR
            
        try:
            # Get product info which includes funding rate
            products = await self.exchange.get_products()
            
            if products:
                for product in products:
                    if product.get('symbol') == symbol:
                        funding_rate = product.get('funding_rate', 0)
                        return float(funding_rate) if funding_rate else 0.0
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Failed to get funding rate: {e}")
            return None
    
    def check_new_candle(self, df: pd.DataFrame) -> bool:
        """Check if a new candle has formed"""
        if df is None or len(df) == 0:
            return False
            
        current_candle_time = df.iloc[-1]['timestamp']
        
        if self.last_candle_time is None:
            self.last_candle_time = current_candle_time
            return True
            
        if current_candle_time > self.last_candle_time:
            self.last_candle_time = current_candle_time
            return True
            
        return False
    
    async def get_historical_data(self, symbol: str, start_date: str, end_date: str, 
                                  timeframe: str) -> Optional[pd.DataFrame]:
        """
        Fetch historical data for backtesting
        
        Args:
            symbol: Trading pair
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            timeframe: Candle timeframe
        """
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            
            # Calculate number of candles needed
            minutes = self._parse_timeframe(timeframe)
            days = (end - start).days
            limit = int((days * 1440) / minutes)
            
            # Fetch data
            df = await self.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            if df is not None:
                # Filter by date range
                df = df[(df['timestamp'] >= start) & (df['timestamp'] <= end)]
                logger.info(f"Loaded {len(df)} historical candles from {start_date} to {end_date}")
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to get historical data: {e}")
            return None
    
    async def test_connection(self) -> bool:
        """Test connection to Delta Exchange"""
        try:
            return await self.exchange.test_connection()
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

# Helper function
async def create_data_manager() -> DataManagerDelta:
    """Create and initialize data manager"""
    dm = DataManagerDelta()
    await dm.__aenter__()
    return dm
