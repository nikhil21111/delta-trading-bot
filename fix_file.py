#!/usr/bin/env python3
"""Fix corrupted trade_executor_delta.py"""

# Read the backup file
with open('trade_executor_delta.py.backup', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and fix the corrupted close_partial_position method
output_lines = []
skip_until = None

for i, line in enumerate(lines):
    if 'async def close_partial_position' in line and skip_until is None:
        # Found the corrupted method - write clean version
        output_lines.append('    async def close_partial_position(self, position_id: str, exit_price: float, \n')
        output_lines.append('                                    percent: int = 50) -> bool:\n')
        output_lines.append('        """Close partial position (NEW - for partial take profits)"""\n')
        output_lines.append('        \n')
        output_lines.append('        if position_id not in self.positions:\n')
        output_lines.append('            logger.error(f"Position {position_id} not found")\n')
        output_lines.append('            return False\n')
        output_lines.append('        \n')
        output_lines.append('        position = self.positions[position_id]\n')
        output_lines.append('        \n')
        output_lines.append('        try:\n')
        output_lines.append('            symbol = position[\'pair\']\n')
        output_lines.append('            total_contracts = position[\'contracts\']\n')
        output_lines.append('            close_contracts = int(total_contracts * (percent / 100))\n')
        output_lines.append('            \n')
        output_lines.append('            if close_contracts < 1:\n')
        output_lines.append('                logger.warning(f"Partial close too small: {close_contracts} contracts")\n')
        output_lines.append('                return False\n')
        output_lines.append('            \n')
        output_lines.append('            side = position[\'side\']\n')
        output_lines.append('            close_side = \'sell\' if side == \'buy\' else \'buy\'\n')
        output_lines.append('            \n')
        output_lines.append('            logger.info(f"Closing {percent}% ({close_contracts} contracts) of position {position_id}")\n')
        output_lines.append('            \n')
        output_lines.append('            # Place closing order\n')
        output_lines.append('            order = await self.exchange.create_order(\n')
        output_lines.append('                symbol=symbol,\n')
        output_lines.append('                side=close_side,\n')
        output_lines.append('                order_type=\'market_order\',\n')
        output_lines.append('                size=close_contracts\n')
        output_lines.append('            )\n')
        output_lines.append('            \n')
        output_lines.append('            if not order:\n')
        output_lines.append('                logger.error("Failed to close partial position")\n')
        output_lines.append('                return False\n')
        output_lines.append('            \n')
        output_lines.append('            # Update position\n')
        output_lines.append('            position[\'remaining_contracts\'] = total_contracts - close_contracts\n')
        output_lines.append('            \n')
        output_lines.append('            # Calculate partial PnL\n')
        output_lines.append('            entry_price = position[\'entry_price\']\n')
        output_lines.append('            if side == \'buy\':\n')
        output_lines.append('                pnl_pct = ((exit_price - entry_price) / entry_price) * 100 * config.LEVERAGE\n')
        output_lines.append('            else:\n')
        output_lines.append('                pnl_pct = ((entry_price - exit_price) / entry_price) * 100 * config.LEVERAGE\n')
        output_lines.append('            \n')
        output_lines.append('            partial_margin = (close_contracts / total_contracts) * position[\'margin\']\n')
        output_lines.append('            pnl_usd = (pnl_pct / 100) * partial_margin\n')
        output_lines.append('            \n')
        output_lines.append('            logger.info(f"✅ Partial close: {percent}% at ${exit_price:.2f}")\n')
        output_lines.append('            logger.info(f"   Partial P&L: ${pnl_usd:.2f} ({pnl_pct:+.2f}%)")\n')
        output_lines.append('            logger.info(f"   Remaining: {position[\'remaining_contracts\']} contracts")\n')
        output_lines.append('            \n')
        output_lines.append('            # Move stop loss to break-even\n')
        output_lines.append('            position[\'stop_loss\'] = entry_price\n')
        output_lines.append('            logger.info(f"   Stop loss moved to break-even: ${entry_price:.2f}")\n')
        output_lines.append('            \n')
        output_lines.append('            return True\n')
        output_lines.append('            \n')
        output_lines.append('        except Exception as e:\n')
        output_lines.append('            logger.error(f"Failed to close partial position: {e}", exc_info=True)\n')
        output_lines.append('            return False\n')
        output_lines.append('    \n')
        
        # Skip until we find async def close_position
        skip_until = 'async def close_position'
    elif skip_until and skip_until in line:
        # Found the next method, resume normal copying
        output_lines.append(line)
        skip_until = None
    elif skip_until is None:
        # Normal line, copy it
        output_lines.append(line)

# Write fixed file
with open('trade_executor_delta.py', 'w', encoding='utf-8') as f:
    f.writelines(output_lines)

print("✅ File fixed successfully!")
