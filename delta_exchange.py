"""
Delta Exchange API Integration
Full futures trading support with leverage
"""
import aiohttp
import hmac
import hashlib
import json
import time
from typing import Dict, Optional, List
from datetime import datetime
from logger import logger

class DeltaExchange:
    """Delta Exchange API integration for futures trading"""
    
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://api.delta.exchange"
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _generate_signature(self, method: str, endpoint: str, payload: str = "") -> tuple:
        """Generate signature for Delta Exchange"""
        timestamp = str(int(time.time()))
        
        # Create signature string: method + timestamp + endpoint + payload
        signature_data = method + timestamp + endpoint + payload
        
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            signature_data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature, timestamp
    
    async def _public_request(self, endpoint: str, params: dict = None) -> Optional[dict]:
        """Make public API request"""
        try:
            url = f"{self.base_url}{endpoint}"
            
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    text = await response.text()
                    logger.error(f"Public API error {response.status}: {text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Public request failed: {e}")
            return None
    
    async def _private_request(self, method: str, endpoint: str, payload: dict = None) -> Optional[dict]:
        """Make authenticated API request"""
        try:
            url = f"{self.base_url}{endpoint}"
            
            # Prepare payload
            if payload:
                payload_str = json.dumps(payload)
            else:
                payload_str = ""
            
            # Generate signature
            signature, timestamp = self._generate_signature(method, endpoint, payload_str)
            
            headers = {
                'Content-Type': 'application/json',
                'api-key': self.api_key,
                'signature': signature,
                'timestamp': timestamp
            }
            
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            if method == 'GET':
                async with self.session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        text = await response.text()
                        logger.error(f"Private API error {response.status}: {text}")
                        return None
            elif method == 'POST':
                async with self.session.post(url, data=payload_str, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        text = await response.text()
                        logger.error(f"Private API error {response.status}: {text}")
                        return None
            elif method == 'DELETE':
                async with self.session.delete(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        text = await response.text()
                        logger.error(f"Private API error {response.status}: {text}")
                        return None
                    
        except Exception as e:
            logger.error(f"Private request failed: {e}")
            return None
    
    async def get_ticker(self, symbol: str = "ETHUSD") -> Optional[Dict]:
        """Get ticker data"""
        try:
            data = await self._public_request(f"/v2/tickers/{symbol}")
            
            if data and 'result' in data:
                ticker = data['result']
                return {
                    'symbol': ticker.get('symbol'),
                    'last': float(ticker.get('close', 0)),
                    'bid': float(ticker.get('bid', 0)),
                    'ask': float(ticker.get('ask', 0)),
                    'high': float(ticker.get('high', 0)),
                    'low': float(ticker.get('low', 0)),
                    'volume': float(ticker.get('volume', 0)),
                    'timestamp': ticker.get('timestamp')
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Get ticker failed: {e}")
            return None
    
    async def get_wallet_balance(self) -> Optional[Dict]:
        """Get wallet balance"""
        try:
            data = await self._private_request('GET', '/v2/wallet/balances')
            
            if data and 'result' in data:
                return data['result']
            
            return None
            
        except Exception as e:
            logger.error(f"Get wallet balance failed: {e}")
            return None
    
    async def get_products(self) -> Optional[List[Dict]]:
        """Get available products/contracts"""
        try:
            data = await self._public_request('/v2/products')
            
            if data and 'result' in data:
                return data['result']
            
            return None
            
        except Exception as e:
            logger.error(f"Get products failed: {e}")
            return None
    
    async def create_order(self, symbol: str, side: str, order_type: str,
                          size: int, limit_price: float = None) -> Optional[Dict]:
        """
        Create futures order on Delta Exchange
        
        Args:
            symbol: Product symbol (e.g., 'ETHUSD')
            side: 'buy' or 'sell'
            order_type: 'market_order' or 'limit_order'
            size: Number of contracts
            limit_price: Limit price (required for limit orders)
        """
        try:
            payload = {
                "product_id": None,  # Will be resolved from symbol
                "size": size,
                "side": side,
                "order_type": order_type,
            }
            
            if order_type == 'limit_order' and limit_price:
                payload['limit_price'] = str(limit_price)
            
            # Get product ID from symbol
            products = await self.get_products()
            if products:
                for product in products:
                    if product.get('symbol') == symbol:
                        payload['product_id'] = product.get('id')
                        break
            
            if not payload['product_id']:
                logger.error(f"Product not found: {symbol}")
                return None
            
            data = await self._private_request('POST', '/v2/orders', payload)
            
            if data and 'result' in data:
                order = data['result']
                return {
                    'id': order.get('id'),
                    'symbol': symbol,
                    'side': side,
                    'type': order_type,
                    'size': size,
                    'price': float(order.get('limit_price', 0)) if limit_price else None,
                    'status': order.get('state'),
                    'timestamp': order.get('created_at')
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Create order failed: {e}")
            return None
    
    async def cancel_order(self, order_id: str, product_id: int) -> bool:
        """Cancel an order"""
        try:
            payload = {
                "product_id": product_id,
                "id": order_id
            }
            
            data = await self._private_request('DELETE', '/v2/orders', payload)
            return data is not None
            
        except Exception as e:
            logger.error(f"Cancel order failed: {e}")
            return False
    
    async def get_positions(self) -> Optional[List[Dict]]:
        """Get open positions"""
        try:
            data = await self._private_request('GET', '/v2/positions')
            
            if data and 'result' in data:
                positions = []
                for pos in data['result']:
                    if float(pos.get('size', 0)) != 0:
                        positions.append({
                            'symbol': pos.get('product_symbol'),
                            'size': float(pos.get('size', 0)),
                            'entry_price': float(pos.get('entry_price', 0)),
                            'margin': float(pos.get('margin', 0)),
                            'unrealized_pnl': float(pos.get('unrealized_pnl', 0)),
                            'realized_pnl': float(pos.get('realized_pnl', 0))
                        })
                return positions
            
            return []
            
        except Exception as e:
            logger.error(f"Get positions failed: {e}")
            return None
    
    async def get_orders(self, product_id: int = None) -> Optional[List[Dict]]:
        """Get active orders"""
        try:
            endpoint = '/v2/orders'
            if product_id:
                endpoint += f'?product_id={product_id}'
            
            data = await self._private_request('GET', endpoint)
            
            if data and 'result' in data:
                return data['result']
            
            return []
            
        except Exception as e:
            logger.error(f"Get orders failed: {e}")
            return None
    
    async def test_connection(self) -> bool:
        """Test API connection"""
        try:
            # Test public API
            ticker = await self.get_ticker("BTCUSD")
            if not ticker:
                logger.error("Public API test failed")
                return False
            
            # Test private API
            balance = await self.get_wallet_balance()
            if balance is None:
                logger.error("Private API test failed - check credentials")
                return False
            
            logger.info("✅ Delta Exchange connection successful")
            return True
            
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

# Helper function
def create_delta_exchange(api_key: str, api_secret: str) -> DeltaExchange:
    """Create Delta Exchange instance"""
    return DeltaExchange(api_key, api_secret)
