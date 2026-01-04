"""
Telegram Command Handler for Semi-Auto Live Bot

Обрабатывает команды пользователя:
- /confirm <signal_id> [lot_size] - Подтвердить и открыть сделку
- /cancel <signal_id> - Отменить сигнал
- /status - Статус бота
- /positions - Показать открытые позиции
- /help - Помощь
"""

import MetaTrader5 as mt5
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import logging


class TelegramCommandHandler:
    """Handle Telegram commands for live bot"""

    def __init__(self, bot_instance):
        """
        Initialize command handler

        Args:
            bot_instance: LiveBotMT5SemiAuto instance
        """
        self.bot = bot_instance
        logging.basicConfig(level=logging.INFO)

    async def confirm_signal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Confirm and execute trade signal

        Usage: /confirm <signal_id> [lot_size]
        """
        try:
            if len(context.args) < 1:
                await update.message.reply_text(
                    "❌ Usage: /confirm <signal_id> [lot_size]\n"
                    "Example: /confirm LONG_1234567890 0.01"
                )
                return

            signal_id = context.args[0]

            # Get lot size (optional)
            lot_size = None
            if len(context.args) >= 2:
                try:
                    lot_size = float(context.args[1])
                except ValueError:
                    await update.message.reply_text("❌ Invalid lot size")
                    return

            # Check if signal exists
            with self.bot.pending_signal_lock:
                if signal_id not in self.bot.pending_signals:
                    await update.message.reply_text(
                        f"❌ Signal {signal_id} not found or expired"
                    )
                    return

                signal_data = self.bot.pending_signals[signal_id]

            # Use suggested lot if not provided
            if lot_size is None:
                lot_size = signal_data['suggested_lot']

            # Validate lot size
            if lot_size < 0.01:
                await update.message.reply_text("❌ Minimum lot size is 0.01")
                return

            # Send order to MT5
            await update.message.reply_text("⏳ Opening position...")

            direction = signal_data['direction']
            entry_price = signal_data['entry_price']
            stop_loss = signal_data['stop_loss']
            tp1 = signal_data['tp1']

            # Determine order type
            order_type = mt5.ORDER_TYPE_BUY if direction == 'LONG' else mt5.ORDER_TYPE_SELL

            # Send market order (only TP1 initially, we'll manage others manually)
            result = self.bot.send_market_order(
                symbol=self.bot.symbol,
                order_type=order_type,
                volume=lot_size,
                sl=stop_loss,
                tp=None,  # We'll manage TP manually for partial close
                comment=f"V9 {signal_data['regime']}"
            )

            if result is None:
                await update.message.reply_text("❌ Failed to open position")
                return

            # Remove from pending
            with self.bot.pending_signal_lock:
                del self.bot.pending_signals[signal_id]

            # Save position to tracking
            position_data = {
                'ticket': result.order,
                'direction': direction,
                'regime': signal_data['regime'],
                'entry_price': result.price,
                'entry_time': signal_data['timestamp'],
                'stop_loss': stop_loss,
                'tp1_price': tp1,
                'tp2_price': signal_data['tp2'],
                'tp3_price': signal_data['tp3'],
                'tp1_hit': False,
                'tp2_hit': False,
                'tp3_hit': False,
                'trailing_distance': signal_data['trailing'],
                'timeout_hours': signal_data['timeout'],
                'initial_volume': lot_size,
                'current_volume': lot_size,
            }

            self.bot.open_positions.append(position_data)

            # Send confirmation
            message = f"✅ **POSITION OPENED**\n\n"
            message += f"📍 Direction: {direction}\n"
            message += f"📊 Regime: {signal_data['regime']}\n"
            message += f"💵 Entry: {result.price:.2f}\n"
            message += f"💼 Lot size: {lot_size:.2f}\n"
            message += f"🛑 SL: {stop_loss:.2f}\n"
            message += f"🎯 TP1: {tp1:.2f} (30%)\n"
            message += f"🎯 TP2: {signal_data['tp2']:.2f} (30%)\n"
            message += f"🎯 TP3: {signal_data['tp3']:.2f} (40%)\n"
            message += f"🎫 Ticket: {result.order}\n\n"
            message += f"✨ Bot will manage TP/SL automatically"

            await update.message.reply_text(message, parse_mode='Markdown')

        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
            logging.error(f"Error in confirm_signal: {e}")

    async def cancel_signal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Cancel pending signal

        Usage: /cancel <signal_id>
        """
        try:
            if len(context.args) < 1:
                await update.message.reply_text("❌ Usage: /cancel <signal_id>")
                return

            signal_id = context.args[0]

            with self.bot.pending_signal_lock:
                if signal_id not in self.bot.pending_signals:
                    await update.message.reply_text(
                        f"❌ Signal {signal_id} not found"
                    )
                    return

                signal_data = self.bot.pending_signals[signal_id]
                del self.bot.pending_signals[signal_id]

            message = f"❌ **SIGNAL CANCELLED**\n\n"
            message += f"Signal ID: `{signal_id}`\n"
            message += f"Direction: {signal_data['direction']}\n"
            message += f"Entry: {signal_data['entry_price']:.2f}"

            await update.message.reply_text(message, parse_mode='Markdown')

        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def show_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show bot status"""
        try:
            # Get account info
            account = self.bot.get_account_info()

            message = "📊 **BOT STATUS**\n\n"

            if account:
                message += f"💰 Balance: ${account['balance']:.2f}\n"
                message += f"📈 Equity: ${account['equity']:.2f}\n"
                message += f"💼 Margin: ${account['margin']:.2f}\n"
                message += f"🆓 Free Margin: ${account['margin_free']:.2f}\n"
                message += f"📊 Profit: ${account['profit']:.2f}\n"
                message += f"⚡ Leverage: {account['leverage']}x\n\n"

            message += f"📍 Open Positions: {len(self.bot.open_positions)}\n"
            message += f"⏳ Pending Signals: {len(self.bot.pending_signals)}\n"
            message += f"🔍 Last Check: {self.bot.last_check.strftime('%H:%M:%S') if self.bot.last_check else 'N/A'}\n"

            await update.message.reply_text(message, parse_mode='Markdown')

        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def show_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show open positions"""
        try:
            positions = mt5.positions_get(symbol=self.bot.symbol)

            if not positions or len(positions) == 0:
                await update.message.reply_text("📊 No open positions")
                return

            message = f"📍 **OPEN POSITIONS ({len(positions)})**\n\n"

            for pos in positions:
                direction = "LONG" if pos.type == mt5.POSITION_TYPE_BUY else "SHORT"
                profit_pct = (pos.profit / (pos.volume * pos.price_open)) * 100

                message += f"🎫 Ticket: {pos.ticket}\n"
                message += f"📍 {direction} {pos.volume:.2f} lots\n"
                message += f"💵 Entry: {pos.price_open:.2f}\n"
                message += f"📈 Current: {pos.price_current:.2f}\n"
                message += f"💰 Profit: ${pos.profit:.2f} ({profit_pct:+.2f}%)\n"
                message += f"🛑 SL: {pos.sl:.2f if pos.sl else 'None'}\n"
                message += f"🎯 TP: {pos.tp:.2f if pos.tp else 'None'}\n"
                message += "─────────────\n"

            await update.message.reply_text(message, parse_mode='Markdown')

        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def show_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help message"""
        message = "📚 **SEMI-AUTO BOT COMMANDS**\n\n"
        message += "**Trade Management:**\n"
        message += "/confirm <id> [lot] - Confirm signal\n"
        message += "/cancel <id> - Cancel signal\n\n"
        message += "**Information:**\n"
        message += "/status - Bot status\n"
        message += "/positions - Open positions\n"
        message += "/help - This help\n\n"
        message += "**How it works:**\n"
        message += "1. Bot finds signal → sends to you\n"
        message += "2. You confirm with /confirm\n"
        message += "3. Bot opens position in MT5\n"
        message += "4. Bot manages TP/SL automatically"

        await update.message.reply_text(message, parse_mode='Markdown')

    def setup_handlers(self, app: Application):
        """Setup command handlers"""
        app.add_handler(CommandHandler("confirm", self.confirm_signal))
        app.add_handler(CommandHandler("cancel", self.cancel_signal))
        app.add_handler(CommandHandler("status", self.show_status))
        app.add_handler(CommandHandler("positions", self.show_positions))
        app.add_handler(CommandHandler("help", self.show_help))
