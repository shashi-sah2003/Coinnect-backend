# Coinnect Backend

A FastAPI backend service that optimizes cross-border payments by analyzing and recommending the most cost-effective payment methods.

## Features

- Payment method optimization using AI agent
- Support for both ACH and cryptocurrency (USDC) payments
- Automated fee analysis and recommendations
- Email notifications for potential fee savings
- Payee management (create, search)
- Balance checking

## Setup

### Prerequisites

- Python 3.12+
- [Payman API](https://paymanai.com/) account
- [Groq API](https://groq.com/) account 
- SMTP email service (for notifications)

### Environment Variables

Create a `.env` file in the root directory with the following variables:

```
PAYMAN_API_KEY=your_payman_api_key
GROQ_API_KEY=your_groq_api_key
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USERNAME=your_email@example.com
EMAIL_PASSWORD=your_email_password
```

### Installation

1. Clone the repository
2. Install dependencies:
    ```bash
    pip install -e .
    ```
3. ```bash
    python -m venv venv
    ```
    If not already made by uv
4. ```bash
    uv pip install -r pyproject.toml
    ```

## Running the Application

Start the application with:

```bash
python main.py
```

The server will be available at `http://127.0.0.1:3000`

## API Endpoints

### Create Payee

Create a new payee with payment methods.

- **URL**: `/payman/create-payee`
- **Method**: `POST`
- **Body**:
  ```json
  {
     "name": "John Doe",
     "contact_details": {
        "email": "john.doe@example.com",
        "phone": "123-456-7890"
     },
     "payment_methods": [
        {
          "type": "US_ACH",
          "is_default": true,
          "ach_details": {
             "account_holder_name": "John Doe",
             "account_holder_type": "individual",
             "routing_number": "123456789",
             "account_number": "987654321",
             "account_type": "checking"
          }
        },
        {
          "type": "CRYPTO_ADDRESS",
          "crypto_details": {
             "address": "0x1234567890abcdef1234567890abcdef12345678",
             "chain": "Ethereum"
          }
        }
     ]
  }
  ```

### Send Payment

Send a payment to a payee with automatic optimization.

- **URL**: `/payman/send-payment`
- **Method**: `POST`
- **Body**:
  ```json
  {
     "payee_id": "pay_123456789",
     "amount": 1000.00,
     "currency": "USD",
     "recipient_email": "john.doe@example.com"
  }
  ```

### Search Payees

Search for existing payees.

- **URL**: `/payman/search-payees`
- **Method**: `GET`

### Get Balance

Check available balance for a specific currency.

- **URL**: `/payman/get-balance/{currency}`
- **Method**: `GET`
- **Example**: `/payman/get-balance/USD`

## Database

The application uses SQLite for local storage of payee and payment method information. The database file is created as `payees.db` in the root directory.

## Note

This project requires valid API keys. Make sure to sign up for Payman and Groq services and configure your environment variables before running the application.