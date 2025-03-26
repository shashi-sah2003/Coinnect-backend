from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from .paymanClient import payman_client
from models.schemas import PayeeRequest, PaymentRequest
from agents.paymentAgent import agent_graph
from models.database import get_db, Payee, PaymentMethod
from sqlalchemy.orm import Session

router = APIRouter(prefix="/payman")

@router.post("/send-payment")
async def send_payment(request: PaymentRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)): 
    try:
        # Get payee details from database
        payee = db.query(Payee).join(PaymentMethod).filter(
            PaymentMethod.payman_payee_id == request.payee_id
        ).first()

        if not payee:
            raise HTTPException(status_code=404, detail="Payee not found")
        
        # Initialize agent state for payment optimization
        initial_state = {
            "messages": [
                {
                    "role": "user",
                    "content": f"""Analyze and execute payment:
                    Amount: {request.amount} {request.currency}
                    Recipient: {payee.name} ({payee.email})
                    Available Payment Methods: {[pm.type for pm in payee.payment_methods]}
                    """
                }
            ],
            "sender_info": {},
            "recipient_info": {
                "name": payee.name,
                "email": payee.email,
                "payment_methods": [
                    {
                        "type": pm.type,
                        "payman_payee_id": pm.payman_payee_id,
                        "is_default": pm.is_default
                    } for pm in payee.payment_methods
                ]
            },
            "payment_details": {
                "amount": request.amount,
                "currency": request.currency
            },
            "background_tasks": background_tasks
        }

        # Run the agent
        result = agent_graph.invoke(initial_state)
        
        # Get the final recommendation
        final_message = result["messages"][-1].content

        # Execute payment based on agent's recommendation
        recommended_method = next(
            (pm for pm in payee.payment_methods 
             if pm.type == ("CRYPTO_ADDRESS" if "usdc" in final_message.lower() else "US_ACH")),
            payee.payment_methods[0]  # Fallback to first available method
        )

        # Execute the payment
        response = payman_client.payments.send_payment(
            payee_id=recommended_method.payman_payee_id,
            amount_decimal=request.amount,
        )

        return {
            "status": "success",
            "data": response,
            "optimization": {
                "method_used": recommended_method.type,
                "reasoning": final_message,
                "fees": request.amount * (0.001 if recommended_method.type == "CRYPTO_ADDRESS" else 0.04),
                "settlement_time": "instant" if recommended_method.type == "CRYPTO_ADDRESS" else "3-5 business days"
            }
        }
    
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