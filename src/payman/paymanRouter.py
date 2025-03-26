from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from .paymanClient import payman_client
from models.schemas import PaymentOptimizationRequest, RecipientAnalysis, PaymentResult, PayeeRequest
from agents.paymentAgent import agent_graph
from models.database import get_db, Payee, PaymentMethod
from sqlalchemy.orm import Session

router = APIRouter(prefix="/payman")

class PaymentRequest(BaseModel):
    payee_id: str
    amount: float
    currency: str

@router.post("/send-payment")
async def send_payment(request: PaymentRequest): 
    try:
        response = payman_client.payments.send_payment(
            payee_id=request.payee_id,
            amount_decimal=request.amount,
        )
        return {"status": "success", "data": response}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/create-payee")
async def create_payee(request: PayeeRequest, db: Session = Depends(get_db)):
    try:
        # First, create or get the payee record
        db_payee = db.query(Payee).filter(Payee.email == request.email).first()

        if not db_payee:
            db_payee = Payee(
                name=request.name,
                email=request.email,
                contact_details=request.contact_details
            )
            db.add(db_payee)
            db.commit()
            db.refresh(db_payee)

         # Process each payment method
        for payment_method in request.payment_methods:
            if payment_method.type == "US_ACH":
                ach = payment_method.ach_details
                response = payman_client.payments.create_payee(
                    name=request.name,
                    type="US_ACH",
                    account_holder_name=ach.account_holder_name,
                    account_holder_type=ach.account_holder_type,
                    routing_number=ach.routing_number,
                    account_number=ach.account_number,
                    account_type=ach.account_type,
                    contact_details=request.contact_details,
                )
                account_details = payment_method.ach_details.model_dump()

            elif payment_method.type == "CRYPTO_ADDRESS":
                crypto = payment_method.crypto_details
                response = payman_client.payments.create_payee(
                    name=request.name,
                    type="CRYPTO_ADDRESS",
                    currency="USDC",
                    address=crypto.wallet_address,
                    chain=crypto.blockchain,
                    contact_details=request.contact_details,
                )
                account_details = payment_method.crypto_details.model_dump()

            # Create payment method record
            db_payment_method = PaymentMethod(
                payee_id=db_payee.id,
                payman_payee_id=response["id"],
                type=payment_method.type,
                account_details=account_details,
                is_default=payment_method.is_default
            )
            
            # If this is default, remove default from other payment methods
            if payment_method.is_default:
                db.query(PaymentMethod).filter(
                    PaymentMethod.payee_id == db_payee.id,
                    PaymentMethod.id != db_payment_method.id
                ).update({"is_default": False})

            db.add(db_payment_method)
            
        db.commit()
        return {"status": "success", "data": {"payee_id": db_payee.id}}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/search-payees")
async def search_payees():
    try:
        response = payman_client.payments.search_payees()
        return {"status": "success", "data": response}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/get-balance")
async def get_balance():
    try:
        response = payman_client.balances.get_spendable_balance("USD")
        return {"status": "success", "data": response}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/optimize-payment", response_model=RecipientAnalysis)
async def optimize_payment(request: PaymentOptimizationRequest):
    """Analyze and optimize a payment transaction"""
    try:
        # Initialize agent state
        initial_state = {
            "messages": [
                {
                    "role": "user",
                    "content": f"""Analyze payment optimization for:
                    Amount: {request.amount} {request.source_currency}
                    Recipient: {request.recipient_name} ({request.recipient_email})
                    Country: {request.recipient_country}
                    Urgency: {request.payment_urgency}
                    """
                }
            ],
            "sender_info": {},
            "recipient_info": {},
            "payment_details": {
                "amount": request.amount,
                "currency": request.source_currency,
                "destination_currency": request.destination_currency
            }
        }

        # Run the agent
        result = agent_graph.invoke(initial_state)
        
        # Process the agent's recommendation
        final_message = result["messages"][-1].content
        
        # Parse recommendation into structured format
        # (You'll need to implement proper parsing based on your agent's output format)
        analysis = RecipientAnalysis(
            has_crypto_wallet=True if "crypto" in final_message.lower() else False,
            recommended_payment_method="USDC" if "usdc" in final_message.lower() else "WIRE",
            estimated_fees={
                "USDC": request.amount * 0.001,
                "WIRE": request.amount * 0.04
            },
            estimated_settlement_time={
                "USDC": "instant",
                "WIRE": "3-5 business days"
            },
            optimal_route=final_message
        )
        
        return analysis

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/execute-optimized-payment", response_model=PaymentResult)
async def execute_optimized_payment(request: PaymentOptimizationRequest):
    """Execute the optimized payment based on agent's recommendation"""
    try:
        # First get the optimization analysis
        analysis = await optimize_payment(request)
        
        # Execute the payment using the recommended method
        if analysis.recommended_payment_method == "USDC":
            # Create crypto payee if doesn't exist
            payee = payman_client.create_payee(
                type="CRYPTO_ADDRESS",
                name=request.recipient_name,
                contact_details={"email": request.recipient_email}
            )
            
            # Send payment
            payment = payman_client.send_payment(
                amount_decimal=request.amount,
                payee_id=payee.id,
                memo=f"Optimized payment to {request.recipient_name}"
            )
            
            return PaymentResult(
                success=True,
                transaction_id=payment.reference,
                payment_method_used="USDC",
                fees_saved=request.amount * 0.039,  # Difference between WIRE and USDC fees
                settlement_time="instant",
                message="Payment successfully processed via USDC"
            )
        else:
            # Handle traditional wire transfer
            # ... implement wire transfer logic ...
            pass

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))