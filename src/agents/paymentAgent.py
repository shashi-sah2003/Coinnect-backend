from langchain.agents.format_scratchpad import format_log_to_str
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from typing import Dict, TypedDict, Annotated, Sequence
from .tools import payment_tools
from dotenv import load_dotenv
import os 
from email.message import EmailMessage
import aiosmtplib

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

class AgentState(TypedDict):
    messages: Annotated[Sequence[HumanMessage | AIMessage], "The messages in the conversation"]
    sender_info: Dict
    recipient_info: Dict
    payment_details: Dict
    iteration_count: int

# Initialize LLM with proper API key
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    groq_api_key=GROQ_API_KEY
)

# Create agent prompt with structured output format
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an AI payment optimization agent that helps reduce cross-border payment fees.
    Your goal is to find the most cost-effective way to send payments while ensuring quick settlement.
    
    Available Tools:
    - analyze_payment_methods: Analyzes available payment methods and recommends the best option
    
    Process:
    1. Analyze available payment methods using the analyze_payment_methods tool
    2. Consider amount, fees, and settlement time
    3. Make a recommendation based on the analysis
    
    Output Format:
    After you have gathered all the information and made your final decision, ALWAYS conclude your analysis with:
    FINAL RECOMMENDATION:
    - Method: [CRYPTO_ADDRESS/US_ACH]
    - Reason: [Brief explanation]
    - Estimated Fees: [Amount]
    - Settlement Time: [Duration]
    - Savings: [Amount saved compared to alternative method]

    **IMPORTANT: Once you provide the FINAL RECOMMENDATION, do not add any further information or steps.**
    """),
    MessagesPlaceholder(variable_name="messages"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])


async def send_fee_notification(recipient_email: str, amount: float):
    """Send email notification about fees and settlement time"""
    try: 
        message = EmailMessage()
        message["From"] = EMAIL_USERNAME
        message["To"] = recipient_email
        message["Subject"] = "Payment Processing Information - USDC Option Available"
        print(f"Sending email to {recipient_email}")

        # Calculate potential savings
        ach_fee = amount * 0.03
        usdc_fee = amount * 0.001
        potential_savings = ach_fee - usdc_fee

        content = f"""
        Hello,

        A payment of ${amount:.2f} has been initiated to your account via ACH transfer.

        Current Payment Details:
        - Method: ACH Transfer
        - Fee: ${ach_fee:.2f} (4%)
        - Settlement Time: 3-5 business days

        You could save on fees by accepting USDC payments:
        - Potential Fee with USDC: ${usdc_fee:.2f} (0.1%)
        - Potential Savings: ${potential_savings:.2f}
        - Settlement Time: Instant

        To start accepting USDC payments and reduce your fees:
        1. Reply to this email
        2. We'll help you set up a USDC wallet
        3. Future payments will be faster and cheaper

        Best regards,
        Coinnect Team
        """

        message.set_content(content)

        try:
            async with aiosmtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as smtp:
                await smtp.starttls()
                await smtp.login(EMAIL_USERNAME, EMAIL_PASSWORD)
                await smtp.send_message(message)
            print(f"Email sent to {recipient_email}")
        except Exception as e:
            print(f"Failed to send email: {e}")
    except Exception as e:
        print(f"Failed to send email: {e}")

def process_step(state: AgentState):
    """Process one step of the agent's analysis"""
    messages = state["messages"]
    recipient_info = state["recipient_info"]
    payment_details = state["payment_details"]
    background_tasks = state.get("background_tasks")
    iteration_count = state["iteration_count"] + 1

    # Run payment method analysis if available
    if recipient_info.get("payment_methods"):
        analysis_result = payment_tools[0].func(
            payment_methods=recipient_info["payment_methods"],
            amount=payment_details["amount"]
        )
        
        # If no USDC method available, schedule email notification
        if analysis_result["recommended_method"] == "US_ACH" and background_tasks:
            background_tasks.add_task(
                send_fee_notification,
                recipient_email=recipient_info["email"],
                amount=payment_details["amount"],
                analysis_result=analysis_result
            )

        analysis_content = f"""
        Payment Method Analysis:
        - Recommended: {analysis_result['recommended_method']}
        - Reason: {analysis_result['reason']}
        - Fee: ${analysis_result['estimated_fee']:.2f}
        - Settlement: {analysis_result['settlement_time']}
        """
        
        messages.append(HumanMessage(content=analysis_content))

    # Get LLM response
    response = llm.invoke(
        prompt.format(
            messages=messages,
            agent_scratchpad=[]
        )
    )

    print("Response: ", response)
    
    # Add response to message history
    messages.append(AIMessage(content=response.content))

    # Check if the agent should continue
    max_iterations = 3  # Set maximum iterations
    if iteration_count >= max_iterations or "final recommendation:" in response.content.lower():
        should_continue_flag = False
    else:
        should_continue_flag = True
    
    return {
        "messages": messages,
        "sender_info": state["sender_info"],
        "recipient_info": state["recipient_info"],
        "payment_details": state["payment_details"],
        "iteration_count": iteration_count,
        "continue": should_continue_flag  
    }

# Create the workflow graph
workflow = StateGraph(AgentState)

# Add nodes and edges
workflow.add_node("process", process_step)

# Add conditional edges
workflow.add_conditional_edges(
    "process",
    lambda state: state["continue"],  # Check the 'continue' flag in the state
    {
        True: "process",
        False: END
    }
)

workflow.set_entry_point("process")

# Compile the graph
agent_graph = workflow.compile()
