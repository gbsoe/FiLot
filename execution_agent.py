#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Execution Agent for the Telegram cryptocurrency pool bot
Builds and executes transactions for liquidity pool interactions
"""

import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple, Union
import json

# Import local modules
from models import User, Pool, Position, CompositeSignal, PositionStatus, db
from solpool_client import get_client as get_solpool_client
from filotsense_client import get_client as get_filotsense_client
import coingecko_utils
from wallet_utils import check_wallet_balance, calculate_deposit_strategy
from walletconnect_utils import create_walletconnect_session, check_walletconnect_session
from solana_wallet_service import get_wallet_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class ExecutionAgent:
    """Agent responsible for building and executing transactions"""
    
    def __init__(self):
        """Initialize the execution agent"""
        # Default slippage tolerance for transactions
        self.default_slippage = 0.01  # 1%
        
        # Load solana wallet service
        self.wallet_service = get_wallet_service()
        
    async def get_wallet_address(self, user_id: int) -> Optional[str]:
        """
        Get the user's connected wallet address
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Wallet address or None if not connected
        """
        try:
            # Check if user has WalletConnect session
            from walletconnect_utils import get_user_walletconnect_sessions
            sessions = await get_user_walletconnect_sessions(user_id)
            
            if sessions and len(sessions) > 0:
                # Use the most recent session
                sorted_sessions = sorted(sessions, key=lambda s: s.get("created_at", 0), reverse=True)
                return sorted_sessions[0].get("wallet_address")
                
            return None
            
        except Exception as e:
            logger.error(f"Error getting wallet address for user {user_id}: {e}")
            return None
            
    async def check_token_balances(self, user_id: int) -> Dict[str, Any]:
        """
        Check token balances for a wallet
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Dictionary with balance information
        """
        wallet_address = await self.get_wallet_address(user_id)
        
        if not wallet_address:
            return {
                "success": False,
                "error": "No wallet connected. Please connect a wallet using /walletconnect"
            }
            
        try:
            balances = await check_wallet_balance(wallet_address)
            return {
                "success": True,
                "wallet_address": wallet_address,
                "balances": balances
            }
        except Exception as e:
            logger.error(f"Error checking token balances: {e}")
            return {
                "success": False,
                "error": f"Error checking token balances: {e}"
            }
            
    async def get_pool_data(self, pool_id: str) -> Dict[str, Any]:
        """
        Get detailed pool data
        
        Args:
            pool_id: ID of the pool
            
        Returns:
            Dictionary with pool data
        """
        try:
            # First try to get from database
            pool = db.session.query(Pool).filter(Pool.id == pool_id).first()
            
            if pool:
                # Format pool data
                pool_data = {
                    "id": pool.id,
                    "token_a": pool.token_a_symbol,
                    "token_b": pool.token_b_symbol,
                    "token_a_price": pool.token_a_price,
                    "token_b_price": pool.token_b_price,
                    "apr": pool.apr_24h,
                    "tvl": pool.tvl,
                    "fee": pool.fee,
                    "volume_24h": pool.volume_24h,
                }
                
                # Get token ratio from prices
                if pool.token_a_price > 0 and pool.token_b_price > 0:
                    pool_data["token_ratio"] = pool.token_a_price / pool.token_b_price
                else:
                    pool_data["token_ratio"] = 1.0
                    
                return {
                    "success": True,
                    "pool": pool_data
                }
                
            # If not in database, get from Raydium API
            from raydium_client import get_client as get_raydium_client
            raydium_client = get_raydium_client()
            
            pool_detail = await raydium_client.get_pool_by_id(pool_id)
            
            if "success" in pool_detail and not pool_detail["success"]:
                return {
                    "success": False,
                    "error": f"Pool not found: {pool_id}"
                }
                
            # Format pool data
            token_a_symbol = pool_detail.get("tokenA", {}).get("symbol", "Unknown")
            token_b_symbol = pool_detail.get("tokenB", {}).get("symbol", "Unknown")
            
            pool_data = {
                "id": pool_id,
                "token_a": token_a_symbol,
                "token_b": token_b_symbol,
                "token_a_price": pool_detail.get("tokenPrices", {}).get(token_a_symbol, 0.0),
                "token_b_price": pool_detail.get("tokenPrices", {}).get(token_b_symbol, 0.0),
                "apr": pool_detail.get("apr", 0.0),
                "tvl": pool_detail.get("tvl", 0.0),
                "fee": pool_detail.get("fee", 0.0),
                "volume_24h": pool_detail.get("volumeUsd24h", 0.0),
                "token_ratio": pool_detail.get("tokenRatio", 1.0),
            }
            
            return {
                "success": True,
                "pool": pool_data
            }
            
        except Exception as e:
            logger.error(f"Error getting pool data: {e}")
            return {
                "success": False,
                "error": f"Error getting pool data: {e}"
            }
            
    async def get_swap_amounts(
        self, 
        token_a: str, 
        token_b: str, 
        usd_amount: float, 
        token_ratio: float,
        balances: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Calculate optimal token amounts for adding liquidity
        
        Args:
            token_a: First token symbol
            token_b: Second token symbol
            usd_amount: Amount in USD to invest
            token_ratio: Ratio of token_a to token_b in the pool
            balances: Current wallet balances
            
        Returns:
            Dictionary with swap and deposit amounts
        """
        try:
            # Get token prices
            token_a_price = await self._get_token_price(token_a)
            token_b_price = await self._get_token_price(token_b)
            
            if token_a_price <= 0 or token_b_price <= 0:
                return {
                    "success": False,
                    "error": f"Invalid token prices: {token_a}=${token_a_price}, {token_b}=${token_b_price}"
                }
                
            # Calculate total amount of each token needed
            token_a_total_needed = (usd_amount / 2) / token_a_price
            token_b_total_needed = (usd_amount / 2) / token_b_price
            
            # Check if the ratio is balanced
            actual_ratio = (token_a_total_needed * token_a_price) / (token_b_total_needed * token_b_price)
            expected_ratio = token_ratio
            
            # If ratio is significantly different, adjust
            if abs(actual_ratio - expected_ratio) > 0.05:  # 5% threshold
                # Recalculate based on pool's expected ratio
                value_in_a = usd_amount / (1 + (1 / expected_ratio))
                value_in_b = usd_amount - value_in_a
                
                token_a_total_needed = value_in_a / token_a_price
                token_b_total_needed = value_in_b / token_b_price
            
            # Check current balances
            token_a_balance = balances.get(token_a, 0.0)
            token_b_balance = balances.get(token_b, 0.0)
            
            # Calculate if we need to swap
            token_a_needed = max(0, token_a_total_needed - token_a_balance)
            token_b_needed = max(0, token_b_total_needed - token_b_balance)
            
            # Determine swap direction and amount
            swap_from_token = None
            swap_to_token = None
            swap_amount = 0.0
            
            if token_a_needed > 0 and token_b_balance > token_b_total_needed:
                # Swap excess token_b for token_a
                swap_from_token = token_b
                swap_to_token = token_a
                swap_amount = min(token_b_balance - token_b_total_needed, token_a_needed * token_a_price / token_b_price)
            elif token_b_needed > 0 and token_a_balance > token_a_total_needed:
                # Swap excess token_a for token_b
                swap_from_token = token_a
                swap_to_token = token_b
                swap_amount = min(token_a_balance - token_a_total_needed, token_b_needed * token_b_price / token_a_price)
            elif token_a_needed > 0 and token_b_needed > 0:
                # Not enough of either token, calculate which one to buy
                # For simplicity, assume we swap USDC or SOL for the needed tokens
                if "USDC" in balances and balances["USDC"] > 0:
                    if token_a_needed * token_a_price > token_b_needed * token_b_price:
                        swap_from_token = "USDC"
                        swap_to_token = token_a
                        swap_amount = min(balances["USDC"], token_a_needed * token_a_price)
                    else:
                        swap_from_token = "USDC"
                        swap_to_token = token_b
                        swap_amount = min(balances["USDC"], token_b_needed * token_b_price)
                elif "SOL" in balances and balances["SOL"] > 0:
                    if token_a_needed * token_a_price > token_b_needed * token_b_price:
                        swap_from_token = "SOL"
                        swap_to_token = token_a
                        swap_amount = min(balances["SOL"], token_a_needed * token_a_price / token_a_price)
                    else:
                        swap_from_token = "SOL"
                        swap_to_token = token_b
                        swap_amount = min(balances["SOL"], token_b_needed * token_b_price / token_b_price)
            
            # Final amounts to deposit
            token_a_to_deposit = min(token_a_balance, token_a_total_needed)
            token_b_to_deposit = min(token_b_balance, token_b_total_needed)
            
            # If we're swapping, adjust deposit amounts
            if swap_from_token and swap_to_token:
                if swap_to_token == token_a:
                    # Estimate how much token_a we'll get from the swap
                    estimated_received = await self._estimate_swap_output(
                        swap_from_token, swap_to_token, swap_amount
                    )
                    token_a_to_deposit += estimated_received
                elif swap_to_token == token_b:
                    # Estimate how much token_b we'll get from the swap
                    estimated_received = await self._estimate_swap_output(
                        swap_from_token, swap_to_token, swap_amount
                    )
                    token_b_to_deposit += estimated_received
            
            return {
                "success": True,
                "usd_amount": usd_amount,
                "token_a": token_a,
                "token_b": token_b,
                "token_a_price": token_a_price,
                "token_b_price": token_b_price,
                "token_a_balance": token_a_balance,
                "token_b_balance": token_b_balance,
                "token_a_total_needed": token_a_total_needed,
                "token_b_total_needed": token_b_total_needed,
                "swap_needed": bool(swap_from_token and swap_to_token),
                "swap_from_token": swap_from_token,
                "swap_to_token": swap_to_token,
                "swap_amount": swap_amount,
                "token_a_to_deposit": token_a_to_deposit,
                "token_b_to_deposit": token_b_to_deposit,
                "total_value_usd": (token_a_to_deposit * token_a_price) + (token_b_to_deposit * token_b_price)
            }
            
        except Exception as e:
            logger.error(f"Error calculating swap amounts: {e}")
            return {
                "success": False,
                "error": f"Error calculating swap amounts: {e}"
            }
    
    async def _get_token_price(self, token_symbol: str) -> float:
        """
        Get token price from CoinGecko
        
        Args:
            token_symbol: Token symbol
            
        Returns:
            Token price in USD
        """
        try:
            return coingecko_utils.get_token_price(token_symbol)
        except Exception as e:
            logger.error(f"Error getting token price for {token_symbol}: {e}")
            return 0.0
            
    async def _estimate_swap_output(self, from_token: str, to_token: str, amount: float) -> float:
        """
        Estimate output amount for a token swap
        
        Args:
            from_token: Token to swap from
            to_token: Token to swap to
            amount: Amount to swap
            
        Returns:
            Estimated output amount
        """
        try:
            from raydium_client import get_client as get_raydium_client
            raydium_client = get_raydium_client()
            
            simulation = await raydium_client.simulate_swap(from_token, to_token, amount)
            
            if simulation.get("success", False):
                return simulation.get("expectedOutput", 0.0)
            else:
                logger.error(f"Swap simulation failed: {simulation.get('error', 'Unknown error')}")
                return 0.0
                
        except Exception as e:
            logger.error(f"Error simulating swap: {e}")
            return 0.0
    
    async def build_deposit_tx(
        self,
        user_id: int,
        pool_id: str,
        usd_amount: float,
        slippage: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Build a transaction to deposit into a liquidity pool
        
        Args:
            user_id: Telegram user ID
            pool_id: ID of the pool to deposit into
            usd_amount: Amount in USD to deposit
            slippage: Slippage tolerance (default: self.default_slippage)
            
        Returns:
            Dictionary with transaction details
        """
        # Use default slippage if not provided
        slippage = slippage if slippage is not None else self.default_slippage
        
        # Get wallet address
        wallet_address = await self.get_wallet_address(user_id)
        
        if not wallet_address:
            return {
                "success": False,
                "error": "No wallet connected. Please connect a wallet using /walletconnect"
            }
            
        # Get pool data
        pool_data_result = await self.get_pool_data(pool_id)
        
        if not pool_data_result.get("success", False):
            return pool_data_result
            
        pool_data = pool_data_result["pool"]
        
        # Get token balances
        balance_result = await self.check_token_balances(user_id)
        
        if not balance_result.get("success", False):
            return balance_result
            
        balances = balance_result["balances"]
        
        # Calculate swap amounts
        swap_result = await self.get_swap_amounts(
            pool_data["token_a"],
            pool_data["token_b"],
            usd_amount,
            pool_data.get("token_ratio", 1.0),
            balances
        )
        
        if not swap_result.get("success", False):
            return swap_result
            
        # Build transaction
        try:
            # Create a position entry
            position = Position(
                user_id=user_id,
                pool_id=pool_id,
                status=PositionStatus.PENDING.value,
                invested_amount_usd=usd_amount,
                token_a_amount=swap_result["token_a_to_deposit"],
                token_b_amount=swap_result["token_b_to_deposit"],
                current_value_usd=swap_result["total_value_usd"],
                current_apr=pool_data["apr"],
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            db.session.add(position)
            db.session.commit()
            
            # Get the latest signal for this pool to set as initial signal
            latest_signal = db.session.query(CompositeSignal) \
                .filter(CompositeSignal.pool_id == pool_id) \
                .order_by(CompositeSignal.timestamp.desc()) \
                .first()
                
            if latest_signal:
                position.initial_composite_signal_id = latest_signal.id
                db.session.commit()
            
            # Build the actual transaction
            transaction_data = {
                "swap_needed": swap_result["swap_needed"],
                "position_id": position.id
            }
            
            if swap_result["swap_needed"]:
                # Add swap instruction
                swap_ix = await self.wallet_service.build_swap_instruction(
                    wallet_address,
                    swap_result["swap_from_token"],
                    swap_result["swap_to_token"],
                    swap_result["swap_amount"],
                    slippage
                )
                
                transaction_data["swap_instruction"] = swap_ix
                
            # Add add-liquidity instruction
            add_liq_ix = await self.wallet_service.build_add_liquidity_instruction(
                wallet_address,
                pool_id,
                pool_data["token_a"],
                pool_data["token_b"],
                swap_result["token_a_to_deposit"],
                swap_result["token_b_to_deposit"],
                slippage
            )
            
            transaction_data["add_liquidity_instruction"] = add_liq_ix
            
            # Build the complete transaction
            transaction = await self.wallet_service.build_transaction(
                wallet_address,
                [
                    transaction_data.get("swap_instruction", None),
                    transaction_data["add_liquidity_instruction"]
                ]
            )
            
            # Store transaction data with the position
            position.position_metadata = {
                "transaction_data": transaction_data,
                "serialized_transaction": transaction.get("serialized_transaction", ""),
                "expires_at": (datetime.now() + timedelta(minutes=30)).isoformat()
            }
            db.session.commit()
            
            return {
                "success": True,
                "position_id": position.id,
                "usd_amount": usd_amount,
                "pool_id": pool_id,
                "token_a": pool_data["token_a"],
                "token_b": pool_data["token_b"],
                "token_a_amount": swap_result["token_a_to_deposit"],
                "token_b_amount": swap_result["token_b_to_deposit"],
                "total_value_usd": swap_result["total_value_usd"],
                "transaction": transaction
            }
            
        except Exception as e:
            logger.error(f"Error building deposit transaction: {e}")
            db.session.rollback()
            return {
                "success": False,
                "error": f"Error building deposit transaction: {e}"
            }
            
    async def build_exit_tx(
        self,
        user_id: int,
        position_id: int,
        slippage: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Build a transaction to exit a liquidity pool position
        
        Args:
            user_id: Telegram user ID
            position_id: ID of the position to exit
            slippage: Slippage tolerance (default: self.default_slippage)
            
        Returns:
            Dictionary with transaction details
        """
        # Use default slippage if not provided
        slippage = slippage if slippage is not None else self.default_slippage
        
        # Get wallet address
        wallet_address = await self.get_wallet_address(user_id)
        
        if not wallet_address:
            return {
                "success": False,
                "error": "No wallet connected. Please connect a wallet using /walletconnect"
            }
            
        # Get position data
        position = db.session.query(Position).filter(
            Position.id == position_id,
            Position.user_id == user_id
        ).first()
        
        if not position:
            return {
                "success": False,
                "error": f"Position not found: {position_id}"
            }
            
        # Check position status
        if position.status not in [PositionStatus.ACTIVE.value, PositionStatus.MONITORED.value]:
            return {
                "success": False,
                "error": f"Position cannot be exited in status: {position.status}"
            }
            
        # Get pool data
        pool_data_result = await self.get_pool_data(position.pool_id)
        
        if not pool_data_result.get("success", False):
            return pool_data_result
            
        pool_data = pool_data_result["pool"]
        
        # Build transaction
        try:
            # Mark position as exiting
            position.status = PositionStatus.EXITING.value
            position.updated_at = datetime.now()
            
            # Get the latest signal for this pool to set as exit signal
            latest_signal = db.session.query(CompositeSignal) \
                .filter(CompositeSignal.pool_id == position.pool_id) \
                .order_by(CompositeSignal.timestamp.desc()) \
                .first()
                
            if latest_signal:
                position.exit_composite_signal_id = latest_signal.id
            
            db.session.commit()
            
            # Build the actual transaction
            remove_liq_ix = await self.wallet_service.build_remove_liquidity_instruction(
                wallet_address,
                position.pool_id,
                pool_data["token_a"],
                pool_data["token_b"],
                position.token_a_amount,
                position.token_b_amount,
                slippage
            )
            
            transaction_data = {
                "remove_liquidity_instruction": remove_liq_ix
            }
            
            # Build the complete transaction
            transaction = await self.wallet_service.build_transaction(
                wallet_address,
                [transaction_data["remove_liquidity_instruction"]]
            )
            
            # Store transaction data with the position
            updated_metadata = {}
            if position.position_metadata:
                updated_metadata = position.position_metadata.copy()
            
            updated_metadata.update({
                "exit_transaction_data": transaction_data,
                "exit_serialized_transaction": transaction.get("serialized_transaction", ""),
                "exit_expires_at": (datetime.now() + timedelta(minutes=30)).isoformat()
            })
            
            position.position_metadata = updated_metadata
            db.session.commit()
            
            return {
                "success": True,
                "position_id": position.id,
                "pool_id": position.pool_id,
                "token_a": pool_data["token_a"],
                "token_b": pool_data["token_b"],
                "token_a_amount": position.token_a_amount,
                "token_b_amount": position.token_b_amount,
                "total_value_usd": position.current_value_usd,
                "transaction": transaction
            }
            
        except Exception as e:
            logger.error(f"Error building exit transaction: {e}")
            db.session.rollback()
            return {
                "success": False,
                "error": f"Error building exit transaction: {e}"
            }
            
    async def submit_transaction(
        self,
        user_id: int,
        transaction_signature: str,
        position_id: Optional[int] = None,
        is_exit: bool = False
    ) -> Dict[str, Any]:
        """
        Submit a signed transaction to the network
        
        Args:
            user_id: Telegram user ID
            transaction_signature: Signed transaction
            position_id: ID of the position (optional)
            is_exit: Whether this is an exit transaction
            
        Returns:
            Dictionary with transaction result
        """
        try:
            # Submit the transaction
            result = await self.wallet_service.submit_transaction(transaction_signature)
            
            if not result.get("success", False):
                if position_id:
                    # Mark position as failed
                    position = db.session.query(Position).filter(
                        Position.id == position_id,
                        Position.user_id == user_id
                    ).first()
                    
                    if position:
                        position.status = PositionStatus.FAILED.value
                        position.updated_at = datetime.now()
                        db.session.commit()
                
                return result
                
            # Transaction was successful
            if position_id:
                # Update position status
                position = db.session.query(Position).filter(
                    Position.id == position_id,
                    Position.user_id == user_id
                ).first()
                
                if position:
                    if is_exit:
                        position.status = PositionStatus.COMPLETED.value
                        position.exited_at = datetime.now()
                        position.exit_tx_signature = result.get("signature")
                    else:
                        position.status = PositionStatus.ACTIVE.value
                        position.deposit_tx_signature = result.get("signature")
                        
                    position.updated_at = datetime.now()
                    db.session.commit()
            
            return result
            
        except Exception as e:
            logger.error(f"Error submitting transaction: {e}")
            
            if position_id:
                # Mark position as failed
                try:
                    position = db.session.query(Position).filter(
                        Position.id == position_id,
                        Position.user_id == user_id
                    ).first()
                    
                    if position:
                        position.status = PositionStatus.FAILED.value
                        position.updated_at = datetime.now()
                        db.session.commit()
                except Exception:
                    pass
            
            return {
                "success": False,
                "error": f"Error submitting transaction: {e}"
            }