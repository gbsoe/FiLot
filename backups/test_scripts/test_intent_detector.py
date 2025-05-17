"""
Test script for intent detection functions
"""

from intent_detector import (
    is_investment_intent,
    is_position_inquiry,
    is_pool_inquiry,
    is_wallet_inquiry,
    extract_amount
)

def test_investment_intent():
    """Test investment intent detection"""
    test_cases = [
        ("I want to invest $500", True),
        ("I'd like to put $1000 in a high-yield pool", True),
        ("Looking to invest 500 USDC", True),
        ("Should I buy some SOL?", True),
        ("How do I add liquidity?", True),
        ("I have 2000 dollars to invest", True),
        ("Tell me about FiLot", False),
        ("What's the weather like?", False),
        ("Show me the best pools", False)  # This is a pool inquiry, not investment intent
    ]
    
    for text, expected in test_cases:
        result = is_investment_intent(text)
        print(f"Text: '{text}' => Investment intent: {result} (Expected: {expected})")
        assert result == expected, f"Failed on: '{text}'"

def test_position_inquiry():
    """Test position inquiry detection"""
    test_cases = [
        ("How are my positions doing?", True),
        ("Show me my current investments", True),
        ("What's in my portfolio?", True),
        ("Check my balance", True),
        ("How am I doing?", True),
        ("Tell me about my holdings", True),
        ("What pools are available?", False),
        ("I want to invest", False),
        ("Tell me about FiLot", False)
    ]
    
    for text, expected in test_cases:
        result = is_position_inquiry(text)
        print(f"Text: '{text}' => Position inquiry: {result} (Expected: {expected})")
        assert result == expected, f"Failed on: '{text}'"

def test_pool_inquiry():
    """Test pool inquiry detection"""
    test_cases = [
        ("Show me the best pools", True),
        ("What pools are available?", True),
        ("Tell me about liquidity pools", True),
        ("Which pool has the highest APR?", True),
        ("Are there any good pools right now?", True),
        ("Pool recommendations?", True),
        ("I want to invest", False),
        ("How's my portfolio?", False),
        ("Tell me about FiLot", False)
    ]
    
    for text, expected in test_cases:
        result = is_pool_inquiry(text)
        print(f"Text: '{text}' => Pool inquiry: {result} (Expected: {expected})")
        assert result == expected, f"Failed on: '{text}'"

def test_wallet_inquiry():
    """Test wallet inquiry detection"""
    test_cases = [
        ("How do I connect my wallet?", True),
        ("Connect wallet", True),
        ("I need to setup my wallet", True),
        ("Wallet connection help", True),
        ("Link my phantom wallet", True),
        ("I want to add my wallet", True),
        ("What pools are available?", False),
        ("I want to invest", False),
        ("Tell me about FiLot", False)
    ]
    
    for text, expected in test_cases:
        result = is_wallet_inquiry(text)
        print(f"Text: '{text}' => Wallet inquiry: {result} (Expected: {expected})")
        assert result == expected, f"Failed on: '{text}'"

def test_extract_amount():
    """Test amount extraction"""
    test_cases = [
        ("I want to invest $500", 500),
        ("Put 1,000 dollars in a pool", 1000),
        ("Can I invest 250 USDC?", 250),
        ("Looking to use 10.5k", 10500),
        ("What can I get for 50 SOL?", 50),
        ("I have $1,234.56 to invest", 1234.56),
        ("Tell me about FiLot", 0),
        ("What's the best pool?", 0)
    ]
    
    for text, expected in test_cases:
        result = extract_amount(text)
        print(f"Text: '{text}' => Amount: {result} (Expected: {expected})")
        assert result == expected, f"Failed on: '{text}'"

if __name__ == "__main__":
    print("Testing investment intent detection...")
    test_investment_intent()
    print("\nTesting position inquiry detection...")
    test_position_inquiry()
    print("\nTesting pool inquiry detection...")
    test_pool_inquiry()
    print("\nTesting wallet inquiry detection...")
    test_wallet_inquiry()
    print("\nTesting amount extraction...")
    test_extract_amount()
    print("\nAll tests passed!")