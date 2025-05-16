"""
Smart investment command handler with reinforcement learning integration
"""

import logging
from typing import Dict, List, Any, Optional
import os
import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes

from keyboard_utils import BACK_KEYBOARD

# Configure logging
logger = logging.getLogger(__name__)

async def smart_invest_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /smart_invest command to provide RL-powered recommendations."""
    
    # Show typing indicator
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING
    )
    
    # Get user info
    user_id = update.effective_user.id
    
    # Get risk profile from user data or use default
    risk_profile = context.user_data.get('risk_profile', 'moderate')
    
    # Welcome message
    await update.message.reply_markdown(
        "🧠 *AI-Powered Investment Recommendations*\n\n"
        "I'm analyzing the market using reinforcement learning to find optimal investment opportunities..."
    )
    
    # Add a slight delay to simulate AI thinking
    await asyncio.sleep(1.5)
    
    try:
        # Import the investment agent with RL capabilities
        from investment_agent import InvestmentAgent
        
        # Create agent instance with user's risk profile
        agent = InvestmentAgent(
            user_id=user_id, 
            risk_profile=risk_profile,
            use_rl=True  # Explicitly use RL for recommendations
        )
        
        # Get recommendations (amount is just for calculations, not actual investment)
        amount = 1000  # Default investment amount for recommendation purposes
        recommendations = await agent.get_recommendations(amount=amount)
        
        # Extract ranked pools from the recommendations
        ranked_pools = recommendations.get('ranked_pools', [])[:3]  # Top 3 pools
        
        if not ranked_pools:
            # Fallback message if no recommendations
            await update.message.reply_markdown(
                "⚠️ *No Recommendations Available*\n\n"
                "I couldn't generate AI recommendations at this time. Please try again later or use the standard investment options.",
                reply_markup=BACK_KEYBOARD
            )
            return
        
        # Format recommendations for display
        response = f"🤖 *AI-Optimized Investment Opportunities*\n"
        response += f"_Based on {risk_profile} risk profile_\n\n"
        
        # Add timing recommendation if available
        timing = recommendations.get('timing', {})
        if timing and 'should_enter' in timing:
            entry_recommendation = "favorable" if timing.get('should_enter', False) else "cautious"
            confidence = timing.get('confidence', 0.5) * 100
            response += f"*Market Entry:* {entry_recommendation.title()} ({confidence:.0f}% confidence)\n"
        
        # Display each pool recommendation
        for i, pool in enumerate(ranked_pools, 1):
            # Basic pool info
            token_pair = f"{pool.get('token0', 'Unknown')}-{pool.get('token1', 'Unknown')}"
            apr = pool.get('apr', 0)
            tvl = pool.get('tvl', 0)
            
            # Calculate simplified returns
            daily_return = (apr / 36500) * amount  # Daily APR
            monthly_return = daily_return * 30
            yearly_return = daily_return * 365
            
            # Format response with detailed metrics
            response += f"\n*{i}. {token_pair} Pool*\n"
            response += f"• APR: {apr:.2f}%\n"
            response += f"• TVL: ${tvl:,.2f}\n"
            
            # Add explanation if available
            if 'explanation' in pool:
                response += f"• _{pool['explanation']}_\n"
                
            # Add returns estimate
            response += f"• Est. Returns on ${amount:,.0f}: ${yearly_return:.2f}/year\n"
            
            # Add RL confidence if available
            if 'confidence' in pool:
                confidence = pool['confidence'] * 100  # Convert to percentage
                response += f"• AI Confidence: {confidence:.0f}%\n"
        
        # Create invest buttons
        keyboard = []
        for i, pool in enumerate(ranked_pools):
            token_pair = f"{pool.get('token0', 'Unknown')}-{pool.get('token1', 'Unknown')}"
            keyboard.append([
                InlineKeyboardButton(f"Invest in {token_pair}", callback_data=f"smart_invest_{i}")
            ])
        
        # Add control buttons
        keyboard.append([
            InlineKeyboardButton("🔄 Refresh Analysis", callback_data="refresh_smart_invest"),
            InlineKeyboardButton("⬅️ Back", callback_data="main_menu")
        ])
        
        # Create reply markup
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Store recommendations in user data for callback handling
        context.user_data['smart_recommendations'] = ranked_pools
        
        # Send recommendations
        await update.message.reply_markdown(
            response,
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error generating smart investment recommendations: {e}")
        
        # Graceful error message
        await update.message.reply_markdown(
            "⚠️ *AI Analysis Temporarily Unavailable*\n\n"
            "I couldn't complete the AI-powered analysis at this time. Please try again later or use the standard investment options.",
            reply_markup=BACK_KEYBOARD
        )

async def handle_smart_invest_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callbacks from the smart investment recommendations."""
    
    # Get the callback data
    query = update.callback_query
    await query.answer()
    
    # Extract callback data
    data = query.data
    
    # Handle refresh request
    if data == "refresh_smart_invest":
        # Clear the message
        await query.delete_message()
        
        # Restart the command
        await smart_invest_command(update, context)
        return
    
    # Handle investment selection
    if data.startswith("smart_invest_"):
        try:
            # Extract pool index
            index = int(data.split("_")[-1])
            
            # Get recommendations from user data
            recommendations = context.user_data.get('smart_recommendations', [])
            
            if not recommendations or index >= len(recommendations):
                # Invalid selection
                await query.edit_message_text(
                    "⚠️ Invalid selection. Please try again with a fresh recommendation.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("Get New Recommendations", callback_data="refresh_smart_invest")
                    ]])
                )
                return
            
            # Get selected pool
            selected_pool = recommendations[index]
            token_pair = f"{selected_pool.get('token0', 'Unknown')}-{selected_pool.get('token1', 'Unknown')}"
            
            # Ask for investment amount
            keyboard = [
                [
                    InlineKeyboardButton("$50", callback_data=f"smart_amount_{index}_50"),
                    InlineKeyboardButton("$100", callback_data=f"smart_amount_{index}_100"),
                    InlineKeyboardButton("$250", callback_data=f"smart_amount_{index}_250")
                ],
                [
                    InlineKeyboardButton("$500", callback_data=f"smart_amount_{index}_500"),
                    InlineKeyboardButton("$1,000", callback_data=f"smart_amount_{index}_1000"),
                    InlineKeyboardButton("$5,000", callback_data=f"smart_amount_{index}_5000")
                ],
                [
                    InlineKeyboardButton("⬅️ Back", callback_data="refresh_smart_invest")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Edit message to ask for amount
            await query.edit_message_text(
                f"💰 *Investment Amount for {token_pair}*\n\n"
                f"How much would you like to invest in this AI-recommended pool?",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Error handling smart invest selection: {e}")
            
            # Error message
            await query.edit_message_text(
                "⚠️ There was an error processing your selection. Please try again.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("Try Again", callback_data="refresh_smart_invest")
                ]])
            )
    
    # Handle amount selection
    if data.startswith("smart_amount_"):
        try:
            # Extract pool index and amount
            parts = data.split("_")
            index = int(parts[2])
            amount = float(parts[3])
            
            # Get recommendations from user data
            recommendations = context.user_data.get('smart_recommendations', [])
            
            if not recommendations or index >= len(recommendations):
                # Invalid selection
                await query.edit_message_text(
                    "⚠️ Invalid selection. Please try again with a fresh recommendation.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("Get New Recommendations", callback_data="refresh_smart_invest")
                    ]])
                )
                return
            
            # Get selected pool
            selected_pool = recommendations[index]
            token_pair = f"{selected_pool.get('token0', 'Unknown')}-{selected_pool.get('token1', 'Unknown')}"
            apr = selected_pool.get('apr', 0)
            
            # Calculate returns
            daily_return = (apr / 36500) * amount
            monthly_return = daily_return * 30
            yearly_return = daily_return * 365
            
            # Create confirmation buttons
            keyboard = [
                [
                    InlineKeyboardButton("✅ Confirm Investment", callback_data=f"smart_confirm_{index}_{amount}")
                ],
                [
                    InlineKeyboardButton("⬅️ Back to Amount", callback_data=f"smart_invest_{index}"),
                    InlineKeyboardButton("❌ Cancel", callback_data="refresh_smart_invest")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Edit message to confirm
            await query.edit_message_text(
                f"🔍 *Investment Confirmation*\n\n"
                f"You are about to invest *${amount:,.2f}* in *{token_pair}* pool.\n\n"
                f"*Expected Returns:*\n"
                f"• Daily: ${daily_return:.2f}\n"
                f"• Monthly: ${monthly_return:.2f}\n"
                f"• Yearly: ${yearly_return:.2f} ({apr:.2f}% APR)\n\n"
                f"Please confirm your investment:",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Error handling smart amount selection: {e}")
            
            # Error message
            await query.edit_message_text(
                "⚠️ There was an error processing your amount selection. Please try again.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("Try Again", callback_data="refresh_smart_invest")
                ]])
            )
    
    # Handle investment confirmation
    if data.startswith("smart_confirm_"):
        try:
            # Extract pool index and amount
            parts = data.split("_")
            index = int(parts[2])
            amount = float(parts[3])
            
            # Get recommendations from user data
            recommendations = context.user_data.get('smart_recommendations', [])
            
            if not recommendations or index >= len(recommendations):
                # Invalid selection
                await query.edit_message_text(
                    "⚠️ Invalid selection. Please try again with a fresh recommendation.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("Get New Recommendations", callback_data="refresh_smart_invest")
                    ]])
                )
                return
            
            # Get selected pool
            selected_pool = recommendations[index]
            token_pair = f"{selected_pool.get('token0', 'Unknown')}-{selected_pool.get('token1', 'Unknown')}"
            
            # In a real implementation, this would interact with wallet APIs and execute the trade
            # For demonstration, we'll simulate a successful investment
            
            # Edit message to show success
            await query.edit_message_text(
                f"✅ *Investment Successful!*\n\n"
                f"You have successfully invested *${amount:,.2f}* in *{token_pair}* pool.\n\n"
                f"Your investment is now being processed and will appear in your portfolio shortly.\n\n"
                f"_This investment was recommended by our AI-powered analysis system._",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📊 View Portfolio", callback_data="view_portfolio"),
                    InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
                ]])
            )
            
            # Log the investment
            user_id = update.effective_user.id
            logger.info(f"User {user_id} invested ${amount} in {token_pair} via smart invest")
            
            # Record in database (if available)
            try:
                from app import app
                with app.app_context():
                    from db_utils import log_user_activity
                    log_user_activity(user_id, f"smart_invest_{token_pair}_{amount}")
            except Exception as e:
                logger.error(f"Error logging investment to database: {e}")
            
        except Exception as e:
            logger.error(f"Error handling investment confirmation: {e}")
            
            # Error message
            await query.edit_message_text(
                "⚠️ There was an error processing your investment. Please try again.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("Try Again", callback_data="refresh_smart_invest")
                ]])
            )