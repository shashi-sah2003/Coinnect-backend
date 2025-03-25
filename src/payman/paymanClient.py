from paymanai import Paymanai
from dotenv import load_dotenv
import os

load_dotenv()

PAYMAN_API_KEY = os.getenv("PAYMAN_API_KEY")

payman_client = Paymanai(x_payman_api_secret=PAYMAN_API_KEY)