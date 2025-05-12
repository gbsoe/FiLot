#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Bot command handlers for the Telegram cryptocurrency pool bot
"""

import os
import logging
import asyncio
from datetime import datetime, timedelta
import json
from typing import Dict, Any, Optional, List, Tuple, Union
import io
import qrcode

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# Import local modules
from models import User, Pool, Position, PositionStatus, db
from orchestrator import get_orchestrator
from walletconnect_utils import create_walletconnect_session, check_walletconnect_session
from utils import format_pool_info

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

#########################
# Agentic Command Handlers
#########################

async def recommend_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Command handler for /recommend - Provide personalized pool recommendations
    
    Args:
        update: Telegram update
        context: Callback context
    """
    user = update.effective_user
    message = update.effective_message
    
    try:
        # Get profile type from arguments, default to high-risk
        args = context.args
        profile = "high-risk"  # Default profile
        
        if args and len(args) > 0:
            arg = args[0].lower()
            if arg in ["stable", "high-risk"]:
                profile = arg
            else:
                await message.reply_text(
                    "Invalid profile type. Please use /recommend high-risk or /recommend stable."
                )
                return
                
        # Send processing message
        processing_message = await message.reply_text(
            "🔍 Analyzing the market for the best pools based on your risk profile...\n"
            "This may take a moment as I'm checking on-chain data and market sentiment."
        )
        
        # Get recommendations from orchestrator
        orchestrator = get_orchestrator()
        result = await orchestrator.recommend(user.id, profile)
        
        # Delete processing message
        await processing_message.delete()
        
        if not result.get("success", False):
            await message.reply_text(
                f"❌ Sorry, I couldn't generate recommendations at this time.\n\n"
                f"Error: {result.get('error', 'Unknown error')}"
            )
            return
            
        # Get the recommended pools
        higher_return = result.get("higher_return")
        stable_return = result.get("stable_return")
        
        if not higher_return:
            await message.reply_text(
                "❌ Sorry, I couldn't find any suitable pools matching your profile.\n\n"
                "Please try again later when market conditions improve."
            )
            return
            
        # Format response
        response = (
            f"🌟 *Recommended Pools for {profile}* 🌟\n\n"
            f"I've analyzed the market and found the following opportunities for you:\n\n"
        )
        
        # Add higher return pool details
        response += (
            f"🚀 *Higher Return Option*\n"
            f"Pool: {higher_return['token_a']}/{higher_return['token_b']}\n"
            f"Current APR: {higher_return['apr_current']:.2f}%\n"
            f"Prediction Score: {higher_return['sol_score']:.2f}\n"
            f"Market Sentiment: {format_sentiment_score(higher_return['sentiment_score'])}\n"
            f"TVL: ${higher_return['tvl']:,.2f}\n\n"
        )
        
        # Add stable return pool details if available
        if stable_return:
            response += (
                f"🛡️ *Stable Option*\n"
                f"Pool: {stable_return['token_a']}/{stable_return['token_b']}\n"
                f"Current APR: {stable_return['apr_current']:.2f}%\n"
                f"Prediction Score: {stable_return['sol_score']:.2f}\n"
                f"Market Sentiment: {format_sentiment_score(stable_return['sentiment_score'])}\n"
                f"TVL: ${stable_return['tvl']:,.2f}\n\n"
            )
            
        response += (
            f"Use `/execute <amount>` to invest in the Higher Return option. For example:\n"
            f"`/execute 100` to invest $100 USD.\n\n"
            f"I'll automatically handle token swaps if needed and generate the optimal transaction."
        )
        
        # Create inline keyboard with buttons
        keyboard = [
            [
                InlineKeyboardButton("Invest $50", callback_data=f"execute_50"),
                InlineKeyboardButton("Invest $100", callback_data=f"execute_100")
            ],
            [
                InlineKeyboardButton("Invest $500", callback_data=f"execute_500"),
                InlineKeyboardButton("Custom Amount", callback_data=f"execute_custom")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send response
        await message.reply_text(response, reply_markup=reply_markup, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error in recommend_command: {e}")
        await message.reply_text(
            "❌ Sorry, something went wrong while generating recommendations.\n"
            "Please try again later."
        )
        
async def execute_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Command handler for /execute - Execute investment into a liquidity pool
    
    Args:
        update: Telegram update
        context: Callback context
    """
    user = update.effective_user
    message = update.effective_message
    
    try:
        # Get amount from arguments
        args = context.args
        
        if not args or len(args) == 0:
            await message.reply_text(
                "Please specify an amount to invest. For example:\n"
                "/execute 100"
            )
            return
            
        try:
            amount = float(args[0])
        except ValueError:
            await message.reply_text(
                "Invalid amount. Please provide a numeric value, for example:\n"
                "/execute 100"
            )
            return
            
        if amount <= 0:
            await message.reply_text(
                "Amount must be positive. Please try again with a valid amount."
            )
            return
            
        # Check wallet connection first
        orchestrator = get_orchestrator()
        wallet_info = await orchestrator.get_wallet_info(user.id)
        
        if not wallet_info.get("success", False):
            # Check if the error is about missing wallet
            if "No wallet connected" in wallet_info.get("error", ""):
                # Create a WalletConnect session
                session_result = await create_walletconnect_session(user.id)
                
                if not session_result.get("success", False):
                    await message.reply_text(
                        "❌ You need to connect a wallet before executing transactions.\n\n"
                        f"Error: {session_result.get('error', 'Could not create WalletConnect session')}"
                    )
                    return
                    
                # Send QR code for connecting
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=4,
                )
                qr.add_data(session_result["uri"])
                qr.make(fit=True)
                
                img = qr.make_image(fill_color="black", back_color="white")
                
                # Convert to bytes
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')
                img_byte_arr.seek(0)
                
                await message.reply_photo(
                    photo=img_byte_arr,
                    caption=(
                        "📱 Please connect your wallet by scanning this QR code with your mobile wallet app.\n\n"
                        "After connecting, run the /execute command again."
                    )
                )
                return
            else:
                await message.reply_text(
                    f"❌ Could not access wallet information.\n\n"
                    f"Error: {wallet_info.get('error', 'Unknown error')}"
                )
                return
                
        # Send processing message
        processing_message = await message.reply_text(
            f"🔄 Processing your investment of ${amount:.2f}...\n"
            f"Building transaction and calculating optimal token amounts..."
        )
        
        # Execute investment
        result = await orchestrator.execute(user.id, amount)
        
        # Delete processing message
        await processing_message.delete()
        
        if not result.get("success", False):
            await message.reply_text(
                f"❌ Sorry, I couldn't execute your investment at this time.\n\n"
                f"Error: {result.get('error', 'Unknown error')}"
            )
            return
            
        # Get transaction details
        position_id = result.get("position_id")
        pool_id = result.get("pool_id")
        token_a = result.get("token_a")
        token_b = result.get("token_b")
        token_a_amount = result.get("token_a_amount")
        token_b_amount = result.get("token_b_amount")
        total_value_usd = result.get("total_value_usd")
        transaction = result.get("transaction", {})
        
        # Generate WalletConnect session for signing
        wc_result = await create_walletconnect_session(
            user.id,
            transaction=transaction.get("serialized_transaction"),
            metadata={
                "position_id": position_id,
                "is_exit": False
            }
        )
        
        if not wc_result.get("success", False):
            await message.reply_text(
                f"❌ Transaction prepared but couldn't create signing session.\n\n"
                f"Error: {wc_result.get('error', 'Unknown error')}"
            )
            return
            
        # Send confirmation message with signing QR code
        response = (
            f"✅ *Investment Transaction Ready*\n\n"
            f"Pool: {token_a}/{token_b}\n"
            f"Investing: ${amount:.2f} USD\n"
            f"Token A: {token_a_amount:.6f} {token_a}\n"
            f"Token B: {token_b_amount:.6f} {token_b}\n"
            f"Total Value: ${total_value_usd:.2f}\n\n"
            f"Please scan the QR code below with your wallet app to sign and submit this transaction."
        )
        
        # Create QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(wc_result["uri"])
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to bytes
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        await message.reply_photo(
            photo=img_byte_arr,
            caption=response,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error in execute_command: {e}")
        await message.reply_text(
            "❌ Sorry, something went wrong while processing your investment.\n"
            "Please try again later."
        )
        
async def positions_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Command handler for /positions - List all positions
    
    Args:
        update: Telegram update
        context: Callback context
    """
    user = update.effective_user
    message = update.effective_message
    
    try:
        # Get positions from orchestrator
        orchestrator = get_orchestrator()
        result = await orchestrator.get_positions(user.id)
        
        if not result.get("success", False):
            await message.reply_text(
                f"❌ Sorry, I couldn't retrieve your positions at this time.\n\n"
                f"Error: {result.get('error', 'Unknown error')}"
            )
            return
            
        positions = result.get("positions", [])
        
        if not positions:
            await message.reply_text(
                "You don't have any positions yet.\n\n"
                "Use /recommend to get investment recommendations and start investing."
            )
            return
            
        # Format response
        response = "📊 *Your Liquidity Positions* 📊\n\n"
        
        for position in positions:
            # Format status with emoji
            status_emoji = {
                PositionStatus.PENDING.value: "⏳",
                PositionStatus.ACTIVE.value: "✅",
                PositionStatus.MONITORED.value: "🔍",
                PositionStatus.EXITING.value: "🚪",
                PositionStatus.COMPLETED.value: "🏁",
                PositionStatus.FAILED.value: "❌"
            }.get(position["status"], "❓")
            
            # Calculate profit/loss
            invested = position["invested_amount_usd"]
            current = position.get("current_value_usd", invested)
            profit_loss = current - invested
            profit_loss_pct = (profit_loss / invested) * 100 if invested > 0 else 0
            
            # Format profit/loss
            profit_loss_text = (
                f"Profit: ${profit_loss:.2f} ({profit_loss_pct:.2f}%)" 
                if profit_loss >= 0 
                else f"Loss: -${abs(profit_loss):.2f} ({profit_loss_pct:.2f}%)"
            )
            
            # Add position details
            response += (
                f"{status_emoji} *Position #{position['id']}*\n"
                f"Pool: {position.get('token_a', 'Token A')}/{position.get('token_b', 'Token B')}\n"
                f"Status: {position['status'].capitalize()}\n"
                f"Invested: ${position['invested_amount_usd']:.2f}\n"
                f"Current Value: ${position.get('current_value_usd', position['invested_amount_usd']):.2f}\n"
                f"{profit_loss_text}\n"
                f"Current APR: {position.get('current_apr', 0):.2f}%\n"
                f"Created: {format_datetime(position['created_at'])}\n\n"
            )
            
        # Add call to action
        response += (
            "Use `/exit <position_id>` to exit a specific position.\n"
            "Example: `/exit 1` to exit position #1."
        )
        
        await message.reply_text(response, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error in positions_command: {e}")
        await message.reply_text(
            "❌ Sorry, something went wrong while retrieving your positions.\n"
            "Please try again later."
        )
        
async def exit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Command handler for /exit - Exit a position
    
    Args:
        update: Telegram update
        context: Callback context
    """
    user = update.effective_user
    message = update.effective_message
    
    try:
        # Get position ID from arguments
        args = context.args
        position_id = None
        
        if args and len(args) > 0:
            try:
                position_id = int(args[0])
            except ValueError:
                await message.reply_text(
                    "Invalid position ID. Please provide a numeric value, for example:\n"
                    "/exit 1"
                )
                return
                
        # Send processing message
        processing_message = await message.reply_text(
            "🔄 Processing your exit request...\n"
            "Building transaction to remove liquidity..."
        )
        
        # Execute exit
        orchestrator = get_orchestrator()
        result = await orchestrator.exit(user.id, position_id)
        
        # Delete processing message
        await processing_message.delete()
        
        if not result.get("success", False):
            await message.reply_text(
                f"❌ Sorry, I couldn't process your exit request at this time.\n\n"
                f"Error: {result.get('error', 'Unknown error')}"
            )
            return
            
        # Get transaction details
        position_id = result.get("position_id")
        pool_id = result.get("pool_id")
        token_a = result.get("token_a")
        token_b = result.get("token_b")
        token_a_amount = result.get("token_a_amount")
        token_b_amount = result.get("token_b_amount")
        total_value_usd = result.get("total_value_usd")
        transaction = result.get("transaction", {})
        
        # Generate WalletConnect session for signing
        wc_result = await create_walletconnect_session(
            user.id,
            transaction=transaction.get("serialized_transaction"),
            metadata={
                "position_id": position_id,
                "is_exit": True
            }
        )
        
        if not wc_result.get("success", False):
            await message.reply_text(
                f"❌ Exit transaction prepared but couldn't create signing session.\n\n"
                f"Error: {wc_result.get('error', 'Unknown error')}"
            )
            return
            
        # Send confirmation message with signing QR code
        response = (
            f"✅ *Exit Transaction Ready*\n\n"
            f"Position: #{position_id}\n"
            f"Pool: {token_a}/{token_b}\n"
            f"Removing: {token_a_amount:.6f} {token_a} and {token_b_amount:.6f} {token_b}\n"
            f"Estimated Value: ${total_value_usd:.2f}\n\n"
            f"Please scan the QR code below with your wallet app to sign and submit this transaction."
        )
        
        # Create QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(wc_result["uri"])
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to bytes
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        await message.reply_photo(
            photo=img_byte_arr,
            caption=response,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error in exit_command: {e}")
        await message.reply_text(
            "❌ Sorry, something went wrong while processing your exit request.\n"
            "Please try again later."
        )

#########################
# Callback Query Handlers
#########################

async def handle_agentic_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for inline keyboard button callbacks
    
    Args:
        update: Telegram update
        context: Callback context
    """
    query = update.callback_query
    user = query.from_user
    
    try:
        # Extract callback data
        data = query.data
        
        # Handle different callback types
        if data.startswith("execute_"):
            # Execute investment with predefined amount
            await query.answer("Processing your investment...")
            
            amount_str = data.replace("execute_", "")
            
            if amount_str == "custom":
                # Ask user to enter custom amount
                await query.message.reply_text(
                    "Please enter a custom amount to invest using the /execute command.\n"
                    "For example: /execute 250"
                )
                return
                
            try:
                amount = float(amount_str)
            except ValueError:
                await query.message.reply_text(
                    "Invalid amount. Please use the /execute command with a numeric value."
                )
                return
                
            # Run the execute command with this amount
            context.args = [str(amount)]
            await execute_command(update, context)
            
        elif data.startswith("exit_"):
            # Exit a position
            await query.answer("Processing your exit request...")
            
            position_id_str = data.replace("exit_", "")
            
            try:
                position_id = int(position_id_str)
            except ValueError:
                await query.message.reply_text(
                    "Invalid position ID. Please use the /exit command with a numeric value."
                )
                return
                
            # Run the exit command with this position ID
            context.args = [str(position_id)]
            await exit_command(update, context)
            
        elif data == "confirm_position_alert":
            # User confirmed position exit alert
            await query.answer("Building exit transaction...")
            
            # Extract position ID from callback context
            metadata = context.bot_data.get("alert_metadata", {})
            position_id = metadata.get("position_id")
            
            if not position_id:
                await query.message.reply_text(
                    "Could not find position information. Please use /positions to see your positions."
                )
                return
                
            # Run the exit command with this position ID
            context.args = [str(position_id)]
            await exit_command(update, context)
            
        elif data == "ignore_position_alert":
            # User ignored position exit alert
            await query.answer("Alert ignored")
            
            # Simply acknowledge that we've ignored the alert
            await query.message.edit_text(
                f"{query.message.text}\n\n"
                f"✅ You've chosen to ignore this alert. The position will continue to be monitored."
            )
            
        else:
            # Unknown callback query type
            await query.answer("Unknown action")
            
    except Exception as e:
        logger.error(f"Error in handle_agentic_callback_query: {e}")
        await query.answer("An error occurred")
        await query.message.reply_text(
            "❌ Sorry, something went wrong while processing your request.\n"
            "Please try again later."
        )

#########################
# Alert Handler
#########################

async def handle_position_alert(alert_data: Dict[str, Any]) -> None:
    """
    Handler for position exit alerts from monitoring agent
    
    Args:
        alert_data: Alert data
    """
    try:
        from bot import application
        
        user_id = alert_data.get("user_id")
        position_id = alert_data.get("position_id")
        exit_reason = alert_data.get("exit_reason", "Exit conditions met")
        transaction = alert_data.get("transaction", {})
        
        if not user_id or not position_id:
            logger.error(f"Invalid alert data: {alert_data}")
            return
            
        # Get position details
        position = db.session.query(Position).filter(
            Position.id == position_id,
            Position.user_id == user_id
        ).first()
        
        if not position:
            logger.error(f"Position not found: {position_id}")
            return
            
        # Get pool details
        pool = db.session.query(Pool).filter(Pool.id == position.pool_id).first()
        
        if not pool:
            logger.error(f"Pool not found: {position.pool_id}")
            return
            
        # Format alert message
        message = (
            f"⚠️ *Position Exit Alert* ⚠️\n\n"
            f"Position: #{position_id}\n"
            f"Pool: {pool.token_a_symbol}/{pool.token_b_symbol}\n"
            f"Current Value: ${position.current_value_usd:.2f}\n"
            f"Current APR: {position.current_apr:.2f}%\n"
            f"Reason: {exit_reason}\n\n"
            f"I recommend exiting this position to protect your investment. Would you like to proceed?"
        )
        
        # Create inline keyboard with confirm/ignore buttons
        keyboard = [
            [
                InlineKeyboardButton("Exit Now", callback_data=f"exit_{position_id}"),
                InlineKeyboardButton("Ignore Alert", callback_data="ignore_position_alert")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Store metadata for callback
        if not hasattr(application.bot_data, "alert_metadata"):
            application.bot_data["alert_metadata"] = {}
            
        application.bot_data["alert_metadata"][position_id] = {
            "position_id": position_id,
            "user_id": user_id
        }
        
        # Send alert message
        await application.bot.send_message(
            chat_id=user_id,
            text=message,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error in handle_position_alert: {e}")

#########################
# Helper functions
#########################

def format_sentiment_score(score: float) -> str:
    """
    Format sentiment score with emoji
    
    Args:
        score: Sentiment score (-1.0 to 1.0)
        
    Returns:
        Formatted string with emoji
    """
    if score >= 0.6:
        return f"Very Positive 😁 ({score:.2f})"
    elif score >= 0.2:
        return f"Positive 🙂 ({score:.2f})"
    elif score >= -0.2:
        return f"Neutral 😐 ({score:.2f})"
    elif score >= -0.6:
        return f"Negative 🙁 ({score:.2f})"
    else:
        return f"Very Negative 😞 ({score:.2f})"
        
def format_datetime(dt_str: str) -> str:
    """
    Format datetime string for display
    
    Args:
        dt_str: ISO datetime string
        
    Returns:
        Formatted date string
    """
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return dt_str