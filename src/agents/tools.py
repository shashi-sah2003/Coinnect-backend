from langchain.tools import Tool
from typing import Dict, List


def analyze_payment_methods(payment_methods: List[Dict], amount: float) -> Dict:
    """Analyze available payment methods and recommend the best option"""
    has_crypto = any(pm["type"] == "CRYPTO_ADDRESS" for pm in payment_methods)
    has_ach = any(pm["type"] == "US_ACH" for pm in payment_methods)
    
    crypto_fee = amount * 0.001  # 0.1% for stable coins
    ach_fee = amount * 0.03      # 3% for ACH
    
    if has_crypto:
        return {
            "recommended_method": "CRYPTO_ADDRESS",
            "reason": "USDC offers instant settlement with lowest fees",
            "estimated_fee": crypto_fee,
            "settlement_time": "instant"
        }
    elif has_ach:
        return {
            "recommended_method": "US_ACH",
            "reason": "ACH is the best available option",
            "estimated_fee": ach_fee,
            "settlement_time": "3-5 business days"
        }
    
    return {
        "recommended_method": None,
        "reason": "No valid payment methods found",
        "estimated_fee": 0,
        "settlement_time": "N/A"
    }

# Define tools for the agent
payment_tools = [
    Tool(
        name="analyze_payment_methods",
        func=analyze_payment_methods,
        description="Analyze available payment methods and recommend the best option"
    )
]