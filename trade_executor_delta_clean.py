"""
Trade Executor for Delta Exchange
Handles futures order execution with leverage
"""
import asyncio
from typing import Dict, List, Optional
from datetime import datetime

from config import config
from logger import logger, trading_logger
from database import db
from delta_exchange import DeltaExchange
from risk_manager import risk_manager

class TradeExecutorDelta:
    """Trade executor for Delta Exchange futures"""
    
    def __init__(self, mode='LIVE'):
        self.mode = mode.upper()
        self.exchange = DeltaExchange(config.DELTA_API_KEY, config.DELTA_API_SECRET)
        self.positions = {}  # symbol -> position data
        self.orders = {}  # order_id -> order data
        self.product_cache = {}  # Cache product IDs
        
    async def __aenter__(self):
        await self.exchange.__aenter__()
        # Load product cache
        await self._load_products()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.exchange.__aexit__(exc_type, exc_val, exc_tb)
    
    async def _load_products(self):
        """Load and cache product information"""
        try:
            products = await self.exchange.get_products()
            if products:
                for product in products:
                    symbol = product.get('symbol')
                    if symbol:
                        self.product_cache[symbol] = product
                logger.info(f"Loaded {len(self.product_cache)} products")
        except Exception as e:
            logger.error(f"Failed to load products: {e}")
    
    def _get_product_id(self, symbol: str) -> Optional[int]:
        """Get product ID from symbol"""
        product = self.product_cache.get(symbol)
        return product.get('id') if product else None
    
    def _calculate_position_size(self, signal: Dict, trade_params: Dict, current_price: float) -> int:
        """
        Calculate position size in contracts for futures trading
        
        Delta Exchange uses USD-based contracts where 1 contract = $1
        """
        risk_amount = trade_params['risk_amount']  # USD to risk
        stop_distance = abs(current_price - trade_params['stop_loss'])
        stop_distance_pct = stop_distance / current_price
        
        # Calculate position size with leverage
        # Position value = risk_amount / stop_distance_pct * leverage
        position_value = (risk_amount / stop_distance_pct) * config.LEVERAGE
        
        # For Delta Exchange: 1 contract = $1
        # So number of contracts = position_value
        contracts = int(position_value)
        
        # Minimum 1 contract
        if contracts < 1:
            contracts = 1
        
        logger.info(f"Position calculation: risk=${risk_amount:.2f}, "
                   f"stop_distance={stop_distance_pct*100:.2f}%, "
                   f"leverage={config.LEVERAGE}x, contracts={contracts}")
        
        return contracts
    
    def _calculate_liquidation_price(self, entry_price: float, side: str, 
                                     leverage: int, margin: float) -> float:
        """Calculate liquidation price"""
        if side == 'buy':
            # Long position: liquidation when price drops
            liq_price = entry_price * (1 - (1 / leverage) * 0.9)  # 90% of margin
        else:
            # Short position: liquidation when price rises
            liq_price = entry_price * (1 + (1 / leverage) * 0.9)
        
        return liq_price
    
    async def execute_trade(self, signal: Dict, trade_params: Dict) -> Optional[Dict]:
        """
        Execute futures trade on Delta Exchange
        
        Args:
            signal: Trading signal from strategy
            trade_params: Risk management parameters
            
        Returns:
            Position dict if successful, None otherwise
        """
        try:
            symbol = signal['pair']
            side = 'buy' if signal['signal'] == 'BUY' else 'sell'
            current_price = signal['price']
            
            # Calculate position size (number of contracts)
            contracts = self._calculate_position_size(signal, trade_params, current_price)
            
            logger.info(f"\n{'='*60}")
            logger.info(f"EXECUTING {signal['signal']} ORDER")
            logger.info(f"{'='*60}")
            logger.info(f"Symbol: {symbol}")
            logger.info(f"Side: {side}")
            logger.info(f"Contracts: {contracts}")
            logger.info(f"Entry Price: ${current_price:.2f}")
            logger.info(f"Leverage: {config.LEVERAGE}x")
            logger.info(f"Stop Loss: ${trade_params['stop_loss']:.2f}")
            logger.info(f"Take Profit: ${trade_params['take_profit']:.2f}")
            
            # Place market order
            order = await self.exchange.create_order(
                symbol=symbol,
                side=side,
                order_type='market_order',
                size=contracts
            )
            
            if not order:
                logger.error("Failed to create order")
                return None
            
            logger.info(f"✅ Order placed: {order['id']}")
            
            # Calculate margin and liquidation
            margin = (contracts * current_price) / config.LEVERAGE
            liq_price = self._calculate_liquidation_price(
                current_price, side, config.LEVERAGE, margin
            )
            
            # Create position record
            position = {
                'id': order['id'],
                'pair': symbol,
                'side': side,
                'entry_price': current_price,
                'contracts': contracts,
                'position_size': contracts,  # For Delta: 1 contract = $1
                'margin': margin,
                'leverage': config.LEVERAGE,
                'stop_loss': trade_params['stop_loss'],
                'take_profit': trade_params['take_profit'],
                'partial_tp': trade_params.get('partial_tp'),
                'partial_tp_percent': trade_params.get('partial_tp_percent', 0),
                'partial_tp_hit': False,
                'remaining_contracts': contracts,
                'trailing_stop_active': False,
                'trailing_stop_price': None,
                'liquidation_price': liq_price,
                'entry_time': datetime.now(),
                'status': 'OPEN',
                'confidence': signal['confidence'],
                'signal_data': signal
            }
            
            # Store position
            self.positions[order['id']] = position
            
            # Save to database
            db.save_trade(position)
            
            # Log trade
            trading_logger.log_trade(
                'ENTRY',
                symbol,
                current_price,
                contracts,
                f"Leverage: {config.LEVERAGE}x, Margin: ${margin:.2f}, Liq: ${liq_price:.2f}"
            )
            
            logger.info(f"✅ Position opened: {contracts} contracts @ ${current_price:.2f}")
            logger.info(f"   Margin: ${margin:.2f}")
            logger.info(f"   Liquidation: ${liq_price:.2f}")
            logger.info(f"   SL: ${trade_params['stop_loss']:.2f}")
            logger.info(f"   TP: ${trade_params['take_profit']:.2f}")
            logger.info(f"{'='*60}\n")
            
            # Update risk manager
            risk_manager.add_position(position)
            
            return position
            
        except Exception as e:
            logger.error(f"Execute trade failed: {e}", exc_info=True)
            return None
    
    async def monitor_positions(self, current_price: float):
        """Monitor open positions and manage exits"""
        
        if not self.positions:
            return
        
        positions_to_close = []
        
        for position_id, position in self.positions.items():
            try:
                side = position['side']
                entry_price = position['entry_price']
                stop_loss = position['stop_loss']
                take_profit = position['take_profit']
                liq_price = position['liquidation_price']
                
                # Calculate PnL
                if side == 'buy':
                    pnl_pct = ((current_price - entry_price) / entry_price) * 100 * config.LEVERAGE
                else:
                    pnl_pct = ((entry_price - current_price) / entry_price) * 100 * config.LEVERAGE
                
                position['current_pnl_pct'] = pnl_pct
                position['current_pnl'] = (pnl_pct / 100) * position['margin']
                
                # Check partial take profit (NEW)
                partial_tp = position.get('partial_tp')
                if partial_tp and not position.get('partial_tp_hit', False):
                    if (side == 'buy' and current_price >= partial_tp) or \
                       (side == 'sell' and current_price <= partial_tp):
                        # Hit partial TP - close 50%
                        logger.info(f"💰 Partial TP hit for position {position_id}")
                        await self.close_partial_position(position_id, current_price, 
                                                        position['partial_tp_percent'])
                        position['partial_tp_hit'] = True
                        continue
                
                # Check liquidation warning (within 10% of liquidation)
                if side == 'buy':
                    liq_distance = ((current_price - liq_price) / entry_price) * 100
                    if liq_distance < 10:
                        logger.warning(f"⚠️ Position {position_id} near liquidation! "
                                     f"Current: ${current_price:.2f}, Liq: ${liq_price:.2f}")
                else:
                    liq_distance = ((liq_price - current_price) / entry_price) * 100
                    if liq_distance < 10:
                        logger.warning(f"⚠️ Position {position_id} near liquidation! "
                                     f"Current: ${current_price:.2f}, Liq: ${liq_price:.2f}")
                
                # Check stop loss
                if side == 'buy' and current_price <= stop_loss:
                    logger.info(f"🛑 Stop loss hit for position {position_id}")
                    positions_to_close.append((position_id, 'STOP_LOSS'))
                    continue
                elif side == 'sell' and current_price >= stop_loss:
                    logger.info(f"🛑 Stop loss hit for position {position_id}")
                    positions_to_close.append((position_id, 'STOP_LOSS'))
                    continue
                
                # Check take profit
                if side == 'buy' and current_price >= take_profit:
                    logger.info(f"🎯 Take profit hit for position {position_id}")
                    positions_to_close.append((position_id, 'TAKE_PROFIT'))
                    continue
                elif side == 'sell' and current_price <= take_profit:
                    logger.info(f"🎯 Take profit hit for position {position_id}")
                    positions_to_close.append((position_id, 'TAKE_PROFIT'))
                    continue
                
                # Trailing stop logic
                if not position['trailing_stop_active']:
                    # Activate trailing stop at 1:1 RR
                    if pnl_pct >= 50:  # 50% to TP = 1:1 RR
                        position['trailing_stop_active'] = True
                        position['trailing_stop_price'] = stop_loss
                        logger.info(f"✅ Trailing stop activated for position {position_id}")
                
                if position['trailing_stop_active']:
                    # Update trailing stop
                    risk_distance = abs(entry_price - stop_loss)
                    trail_distance = risk_distance * config.TRAILING_STOP_DISTANCE
                    
                    if side == 'buy':
                        new_trail = current_price - trail_distance
                        if new_trail > position['trailing_stop_price']:
                            position['trailing_stop_price'] = new_trail
                            logger.debug(f"Trailing stop updated: ${new_trail:.2f}")
                        
                        # Check trailing stop
                        if current_price <= position['trailing_stop_price']:
                            logger.info(f"📈 Trailing stop hit for position {position_id}")
                            positions_to_close.append((position_id, 'TRAILING_STOP'))
                    else:
                        new_trail = current_price + trail_distance
                        if new_trail < position['trailing_stop_price']:
                            position['trailing_stop_price'] = new_trail
                            logger.debug(f"Trailing stop updated: ${new_trail:.2f}")
                        
                        # Check trailing stop
                        if current_price >= position['trailing_stop_price']:
                            logger.info(f"📉 Trailing stop hit for position {position_id}")
                            positions_to_close.append((position_id, 'TRAILING_STOP'))
                
            except Exception as e:
                logger.error(f"Error monitoring position {position_id}: {e}")
        
        # Close positions
        for position_id, exit_reason in positions_to_close:
            await self.close_position(position_id, current_price, exit_reason)
    
