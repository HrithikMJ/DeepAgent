from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings
from dotenv import dotenv_values

config = dotenv_values(".env")

URL = "https://aisera-api-uat.mydesktopnow.com"


INGESTER_URL = "http://localhost:8000"
CONNECTION_STRING = f"postgresql://{config['POSTGRES_USER']}:{config['POSTGRES_PASSWORD']}@{config['POSTGRES_HOST']}:{config['POSTGRES_PORT']}/{config['POSTGRES_DB']}"
