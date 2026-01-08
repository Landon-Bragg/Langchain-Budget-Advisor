"""
Transaction categorization using LangChain with FREE API options
"""
import os
from typing import List, Dict
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from dotenv import load_dotenv
from pathlib import Path

# Load .env file from current directory or parent directories
env_path = Path('.') / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)
else:
    load_dotenv(override=True)  # Try to find .env in parent directories

# Verify the API key is loaded
if not os.getenv("GROQ_API_KEY"):
    print("WARNING: GROQ_API_KEY not found in environment!")
    print(f"Looking for .env file at: {env_path.absolute()}")
    print(f".env exists: {env_path.exists()}")


def get_llm(provider="groq"):
    """Get LLM based on provider choice"""
    
    if provider == "groq":
        # Groq - FREE and FAST (llama3 models)
        from groq import Groq as GroqClient
        from langchain.llms.base import LLM
        from typing import Any, List, Optional
        from pydantic import Field
        
        class GroqLLM(LLM):
            client: Any = Field(default=None)
            model: str = "llama-3.3-70b-versatile"  # Updated to current model
            
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.client = GroqClient(api_key=os.getenv("GROQ_API_KEY"))
            
            @property
            def _llm_type(self) -> str:
                return "groq"
            
            def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                return response.choices[0].message.content
        
        return GroqLLM()
    
    elif provider == "openai":
        # OpenAI - has free tier with GPT-3.5
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
    
    elif provider == "ollama":
        # Ollama - 100% FREE, runs locally (no API key needed!)
        from langchain_community.llms import Ollama
        return Ollama(
            model="llama3.1",  # or "mistral", "phi3", etc.
            temperature=0
        )
    
    else:
        raise ValueError(f"Unsupported provider: {provider}")


class TransactionCategorizer:
    """Categorizes financial transactions using LLM"""
    
    CATEGORIES = [
        "Groceries",
        "Restaurants & Dining",
        "Transportation",
        "Utilities",
        "Rent/Mortgage",
        "Entertainment",
        "Shopping",
        "Healthcare",
        "Insurance",
        "Subscriptions",
        "Travel",
        "Income",
        "Transfers",
        "Other"
    ]
    
    def __init__(self, provider="groq"):
        self.provider = provider
        self.llm = get_llm(provider)
        
        self.categorization_prompt = PromptTemplate(
            input_variables=["description", "amount", "categories"],
            template="""You are a financial transaction categorizer. Given a transaction description and amount, 
categorize it into the most appropriate category.

Transaction Description: {description}
Amount: ${amount}

Available Categories:
{categories}

Return ONLY the category name that best fits this transaction. Be consistent with your categorization.

Category:"""
        )
        
        self.categorization_chain = LLMChain(
            llm=self.llm,
            prompt=self.categorization_prompt
        )
    
    def categorize_transaction(self, description: str, amount: float) -> str:
        """Categorize a single transaction"""
        try:
            result = self.categorization_chain.run(
                description=description,
                amount=abs(amount),
                categories="\n".join(f"- {cat}" for cat in self.CATEGORIES)
            )
            
            # Clean up the result
            category = result.strip()
            
            # Validate it's in our list
            if category in self.CATEGORIES:
                return category
            
            # If not exact match, find closest
            for cat in self.CATEGORIES:
                if cat.lower() in category.lower() or category.lower() in cat.lower():
                    return cat
            
            return "Other"
            
        except Exception as e:
            print(f"Error categorizing transaction: {e}")
            return "Other"
    
    def categorize_batch(self, transactions: List[Dict]) -> List[Dict]:
        """Categorize a batch of transactions"""
        categorized = []
        
        for i, transaction in enumerate(transactions):
            print(f"Categorizing transaction {i+1}/{len(transactions)}...")
            
            category = self.categorize_transaction(
                transaction['description'],
                transaction['amount']
            )
            
            transaction['category'] = category
            categorized.append(transaction)
        
        return categorized