"""
Financial Advisor Agent using LangChain with FREE APIs
"""
import os
from typing import List, Dict, Any
import pandas as pd
from datetime import datetime, timedelta
from langchain.agents import Tool, AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from dotenv import load_dotenv
from pathlib import Path
import json

# Load .env file
env_path = Path('.') / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)
else:
    load_dotenv(override=True)


def get_llm(provider="groq"):
    """Get LLM based on provider choice"""
    
    if provider == "groq":
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
                    temperature=0.3
                )
                return response.choices[0].message.content
        
        return GroqLLM()
    
    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.3,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
    
    elif provider == "ollama":
        from langchain_community.llms import Ollama
        return Ollama(
            model="llama3.1",
            temperature=0.3
        )
    
    else:
        raise ValueError(f"Unsupported provider: {provider}")


class FinancialAdvisorAgent:
    """LangChain agent that provides financial advice based on transaction data"""
    
    def __init__(self, transactions_df: pd.DataFrame = None, provider="groq"):
        self.transactions_df = transactions_df if transactions_df is not None else pd.DataFrame()
        self.provider = provider
        
        # Initialize LLM
        self.llm = get_llm(provider)
        
        # Create tools
        self.tools = self._create_tools()
        
        # Create memory
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # Create agent
        self.agent = self._create_agent()
    
    def _create_tools(self) -> List[Tool]:
        """Create tools for the agent to use"""
        
        def query_transactions(query: str) -> str:
            """Query transaction data. Input should be a description of what to search for."""
            if self.transactions_df.empty:
                return "No transaction data available. Please upload transaction data first."
            
            try:
                df = self.transactions_df.copy()
                
                result = {
                    "total_transactions": len(df),
                    "date_range": f"{df['date'].min()} to {df['date'].max()}",
                    "total_spent": float(df[df['amount'] < 0]['amount'].sum()),
                    "total_income": float(df[df['amount'] > 0]['amount'].sum()),
                    "categories": df['category'].value_counts().to_dict()
                }
                
                return json.dumps(result, indent=2)
            except Exception as e:
                return f"Error querying transactions: {str(e)}"
        
        def calculate_category_spending(category: str = None) -> str:
            """Calculate spending by category. If category specified, returns details for that category."""
            if self.transactions_df.empty:
                return "No transaction data available."
            
            try:
                df = self.transactions_df.copy()
                expenses = df[df['amount'] < 0].copy()
                
                if category:
                    category_expenses = expenses[expenses['category'].str.lower() == category.lower()]
                    if category_expenses.empty:
                        return f"No expenses found for category: {category}"
                    
                    total = float(category_expenses['amount'].sum())
                    count = len(category_expenses)
                    avg = float(category_expenses['amount'].mean())
                    
                    return json.dumps({
                        "category": category,
                        "total_spent": total,
                        "transaction_count": count,
                        "average_transaction": avg,
                        "recent_transactions": category_expenses.tail(5)[['date', 'description', 'amount']].to_dict('records')
                    }, indent=2, default=str)
                else:
                    by_category = expenses.groupby('category')['amount'].agg(['sum', 'count', 'mean']).round(2)
                    return by_category.to_string()
                    
            except Exception as e:
                return f"Error calculating spending: {str(e)}"
        
        def find_savings_opportunities() -> str:
            """Analyze spending patterns to find potential savings opportunities."""
            if self.transactions_df.empty:
                return "No transaction data available."
            
            try:
                df = self.transactions_df.copy()
                expenses = df[df['amount'] < 0].copy()
                
                expenses['amount_abs'] = expenses['amount'].abs()
                potential_subscriptions = expenses[
                    (expenses['amount_abs'] < 50) & 
                    (expenses['amount_abs'] > 5)
                ].groupby('description').size()
                
                by_category = expenses.groupby('category')['amount'].sum().abs().sort_values(ascending=False)
                
                result = {
                    "top_spending_categories": by_category.head(5).to_dict(),
                    "potential_subscriptions": potential_subscriptions[potential_subscriptions > 1].to_dict(),
                    "monthly_average": float(expenses['amount'].sum() / len(expenses['date'].dt.to_period('M').unique())) if not expenses.empty else 0
                }
                
                return json.dumps(result, indent=2)
                
            except Exception as e:
                return f"Error finding savings: {str(e)}"
        
        def compare_periods(months: int = 1) -> str:
            """Compare current period spending to previous periods. Default is 1 month comparison."""
            if self.transactions_df.empty:
                return "No transaction data available."
            
            try:
                df = self.transactions_df.copy()
                df['date'] = pd.to_datetime(df['date'])
                expenses = df[df['amount'] < 0].copy()
                
                today = datetime.now()
                current_start = today - timedelta(days=30*months)
                previous_start = current_start - timedelta(days=30*months)
                
                current_period = expenses[expenses['date'] >= current_start]
                previous_period = expenses[
                    (expenses['date'] >= previous_start) & 
                    (expenses['date'] < current_start)
                ]
                
                current_total = float(current_period['amount'].sum())
                previous_total = float(previous_period['amount'].sum())
                
                change = current_total - previous_total
                percent_change = (change / previous_total * 100) if previous_total != 0 else 0
                
                current_by_cat = current_period.groupby('category')['amount'].sum()
                previous_by_cat = previous_period.groupby('category')['amount'].sum()
                
                result = {
                    "current_period_total": current_total,
                    "previous_period_total": previous_total,
                    "change": change,
                    "percent_change": f"{percent_change:.1f}%",
                    "categories_increased": (current_by_cat - previous_by_cat).sort_values().tail(3).to_dict(),
                    "categories_decreased": (current_by_cat - previous_by_cat).sort_values().head(3).to_dict()
                }
                
                return json.dumps(result, indent=2)
                
            except Exception as e:
                return f"Error comparing periods: {str(e)}"
        
        return [
            Tool(
                name="QueryTransactions",
                func=query_transactions,
                description="Query transaction data to get summary statistics and overview of spending"
            ),
            Tool(
                name="CalculateCategorySpending",
                func=calculate_category_spending,
                description="Calculate spending by category. Input can be a specific category name or leave empty for all categories."
            ),
            Tool(
                name="FindSavingsOpportunities",
                func=find_savings_opportunities,
                description="Analyze spending to find potential savings opportunities, subscriptions, and high spending areas"
            ),
            Tool(
                name="ComparePeriods",
                func=compare_periods,
                description="Compare current spending to previous periods to identify trends"
            )
        ]
    
    def _create_agent(self) -> AgentExecutor:
        """Create the ReAct agent"""
        
        template = """You are a helpful personal financial advisor. You have access to tools to analyze transaction data and provide insights.

Answer the user's questions about their finances using the available tools. Be conversational, helpful, and provide actionable advice.

When analyzing spending, be specific with numbers and categories. When suggesting savings, be realistic and considerate.

TOOLS:
{tools}

TOOL NAMES: {tool_names}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought: {agent_scratchpad}"""
        
        prompt = PromptTemplate(
            template=template,
            input_variables=["input", "agent_scratchpad", "tools", "tool_names"]
        )
        
        agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=10,  # Increased from 5
            early_stopping_method="generate"  # Better stopping
        )
    
    def update_transactions(self, transactions_df: pd.DataFrame):
        """Update the transaction data"""
        self.transactions_df = transactions_df
        self.tools = self._create_tools()
        self.agent = self._create_agent()
    
    def ask(self, question: str) -> str:
        """Ask the financial advisor a question"""
        try:
            # Get relevant data based on question
            context = ""
            
            if self.transactions_df.empty:
                return "No transaction data available. Please upload transactions first."
            
            # Build context from data
            df = self.transactions_df.copy()
            expenses = df[df['amount'] < 0].copy()
            
            # Summary stats
            total_spent = abs(expenses['amount'].sum())
            total_income = df[df['amount'] > 0]['amount'].sum()
            
            # By category
            by_category = expenses.groupby('category')['amount'].sum().abs().sort_values(ascending=False)
            
            context = f"""
You are a helpful financial advisor. Here is the user's financial data:

SUMMARY:
- Total Expenses: ${total_spent:.2f}
- Total Income: ${total_income:.2f}
- Net: ${total_income - total_spent:.2f}
- Date Range: {df['date'].min()} to {df['date'].max()}
- Number of Transactions: {len(df)}

TOP SPENDING CATEGORIES:
{by_category.head(10).to_string()}

SAMPLE RECENT TRANSACTIONS:
{df.tail(10)[['date', 'description', 'amount', 'category']].to_string()}

Based on this data, please answer the following question in a helpful, conversational way.
Be specific with numbers and provide actionable advice.

User Question: {question}

Your Answer:"""
            
            # Get response from LLM
            response = self.llm._call(context)
            return response.strip()
            
        except Exception as e:
            return f"I encountered an error: {str(e)}. Please try asking in a different way."