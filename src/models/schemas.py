from pydantic import BaseModel
from typing import Optional, List, Dict
from pydantic import BaseModel
from typing import Literal

class ACHDetails(BaseModel):
    account_holder_name: str
    account_holder_type: Literal["individual", "business"]
    routing_number: str
    account_number: str
    account_type: Literal["checking", "savings"]

class CryptoDetails(BaseModel):
    wallet_address: str
    blockchain: Literal["Ethereum", "Polygon", "Base", "Arbitrum", "Avalanche", "Optimism", "Solana"]

class PaymentMethodRequest(BaseModel):
    type: Literal["US_ACH", "CRYPTO_ADDRESS"]
    is_default: bool = False
    ach_details: Optional[ACHDetails] = None
    crypto_details: Optional[CryptoDetails] = None

class PayeeRequest(BaseModel):
    name: str
    email: str
    contact_details: dict
    payment_methods: List[PaymentMethodRequest]

class PaymentRequest(BaseModel):
    payee_id: str
    amount: float
    currency: str
    recipient_email: str