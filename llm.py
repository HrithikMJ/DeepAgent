import constants as c
from langchain_openai import AzureChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import AzureOpenAIEmbeddings

LARGE_MODEL = AzureChatOpenAI(
    model="gpt-4o-2024-11-20",
    api_key=c.config["OPENAI_API_KEY_AGENTIC"],
    azure_endpoint="https://agentic-ai-euv.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2025-01-01-preview",
    azure_deployment="Agentic-AI-EuV",
    api_version="2025-01-01-preview",
)

MINI_MODEL = AzureChatOpenAI(
    model="gpt-5-mini",
    api_key=c.config["OPENAI_API_KEY_ADMIN"],
    azure_endpoint="https://admin-4780-resource.cognitiveservices.azure.com/openai/deployments/gpt-5-mini/chat/completions?api-version=2025-01-01-preview",
    azure_deployment="admin-4780-resource",
    api_version="2025-01-01-preview",
)

NANO_MODEL = AzureChatOpenAI(
    model="gpt-5-nano",
    api_key=c.config["OPENAI_API_KEY_ADMIN"],
    azure_endpoint="https://admin-4780-resource.cognitiveservices.azure.com/openai/deployments/gpt-5-nano/chat/completions?api-version=2025-01-01-preview",
    azure_deployment="admin-4780-resource",
    api_version="2025-01-01-preview",
)

HF_EMBEDDING_MODEL = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    encode_kwargs={"normalize_embeddings": True},
)
OPENAI_EMBEDDING_MODEL = AzureOpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key=c.config["OPENAI_API_KEY_AGENTIC"],
    azure_endpoint="https://agentic-ai-euv.openai.azure.com/",
)