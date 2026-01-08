"""
Plaid Integration for Bank Account Connectivity
This module handles connecting to your bank accounts via Plaid API
"""
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import plaid
from plaid.api import plaid_api
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
from dotenv import load_dotenv
import pandas as pd

load_dotenv()


class PlaidConnector:
    """Handles Plaid API connections for bank account access"""
    
    def __init__(self):
        """Initialize Plaid client with credentials from .env"""
        self.client_id = os.getenv('PLAID_CLIENT_ID')
        self.secret = os.getenv('PLAID_SECRET')
        self.env = os.getenv('PLAID_ENV', 'sandbox')
        
        # Validate credentials
        if not self.client_id or not self.secret:
            raise ValueError(
                "Missing Plaid credentials. Please add PLAID_CLIENT_ID and PLAID_SECRET to .env file"
            )
        
        # Set up Plaid configuration
        if self.env == 'sandbox':
            host = plaid.Environment.Sandbox
        elif self.env == 'development':
            host = plaid.Environment.Development
        else:
            host = plaid.Environment.Production
        
        configuration = plaid.Configuration(
            host=host,
            api_key={
                'clientId': self.client_id,
                'secret': self.secret,
            }
        )
        
        api_client = plaid.ApiClient(configuration)
        self.client = plaid_api.PlaidApi(api_client)
        
        # Store access tokens for connected accounts
        self.access_tokens = {}
    
    def create_link_token(self, user_id: str = "default_user") -> Dict:
        """
        Create a Link token for Plaid Link UI
        This is the first step to connect a bank account
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            Dictionary with link_token and expiration
        """
        try:
            request = LinkTokenCreateRequest(
                user=LinkTokenCreateRequestUser(client_user_id=user_id),
                client_name="Personal Finance Advisor",
                products=[Products("transactions")],
                country_codes=[CountryCode("US")],
                language="en",
            )
            
            response = self.client.link_token_create(request)
            
            return {
                'link_token': response['link_token'],
                'expiration': response['expiration'],
                'request_id': response['request_id']
            }
            
        except plaid.ApiException as e:
            return {
                'error': str(e),
                'error_type': 'API_ERROR'
            }
    
    def exchange_public_token(self, public_token: str, institution_name: str = "My Bank") -> Dict:
        """
        Exchange public token for access token
        This happens after user successfully connects their bank in Plaid Link
        
        Args:
            public_token: Token received from Plaid Link
            institution_name: Name to identify this bank connection
            
        Returns:
            Dictionary with success status and item_id
        """
        try:
            request = ItemPublicTokenExchangeRequest(public_token=public_token)
            response = self.client.item_public_token_exchange(request)
            
            # Store the access token
            access_token = response['access_token']
            item_id = response['item_id']
            
            self.access_tokens[institution_name] = {
                'access_token': access_token,
                'item_id': item_id
            }
            
            return {
                'success': True,
                'item_id': item_id,
                'institution_name': institution_name
            }
            
        except plaid.ApiException as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_transactions(
        self, 
        institution_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        days_back: int = 30
    ) -> pd.DataFrame:
        """
        Fetch transactions from a connected bank account
        
        Args:
            institution_name: Name of the connected institution
            start_date: Start date for transactions (optional)
            end_date: End date for transactions (optional)
            days_back: Number of days to fetch if dates not specified
            
        Returns:
            DataFrame with columns: date, description, amount, category
        """
        if institution_name not in self.access_tokens:
            raise ValueError(f"No access token found for {institution_name}. Connect the account first.")
        
        access_token = self.access_tokens[institution_name]['access_token']
        
        # Set date range
        if not end_date:
            end_date = datetime.now().date()
        if not start_date:
            start_date = end_date - timedelta(days=days_back)
        
        try:
            request = TransactionsGetRequest(
                access_token=access_token,
                start_date=start_date,
                end_date=end_date,
                options=TransactionsGetRequestOptions()
            )
            
            response = self.client.transactions_get(request)
            transactions = response['transactions']
            
            # Handle pagination if there are more transactions
            while len(transactions) < response['total_transactions']:
                request = TransactionsGetRequest(
                    access_token=access_token,
                    start_date=start_date,
                    end_date=end_date,
                    options=TransactionsGetRequestOptions(
                        offset=len(transactions)
                    )
                )
                response = self.client.transactions_get(request)
                transactions.extend(response['transactions'])
            
            # Convert to DataFrame
            df_data = []
            for txn in transactions:
                df_data.append({
                    'date': txn['date'],
                    'description': txn['name'],
                    'amount': -txn['amount'],  # Plaid uses positive for debits, we want negative
                    'category': ', '.join(txn.get('category', ['Other'])),
                    'pending': txn['pending'],
                    'transaction_id': txn['transaction_id'],
                    'merchant_name': txn.get('merchant_name', ''),
                })
            
            df = pd.DataFrame(df_data)
            
            # Filter out pending transactions by default
            df = df[df['pending'] == False].copy()
            df = df.drop('pending', axis=1)
            
            return df
            
        except plaid.ApiException as e:
            raise Exception(f"Error fetching transactions: {str(e)}")
    
    def get_all_transactions(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        days_back: int = 30
    ) -> pd.DataFrame:
        """
        Fetch transactions from ALL connected bank accounts
        
        Args:
            start_date: Start date for transactions
            end_date: End date for transactions
            days_back: Number of days to fetch if dates not specified
            
        Returns:
            Combined DataFrame from all accounts
        """
        all_transactions = []
        
        for institution_name in self.access_tokens.keys():
            try:
                df = self.get_transactions(
                    institution_name=institution_name,
                    start_date=start_date,
                    end_date=end_date,
                    days_back=days_back
                )
                df['account'] = institution_name
                all_transactions.append(df)
            except Exception as e:
                print(f"Error fetching transactions from {institution_name}: {e}")
        
        if not all_transactions:
            return pd.DataFrame()
        
        # Combine all DataFrames
        combined_df = pd.concat(all_transactions, ignore_index=True)
        
        # Sort by date
        combined_df = combined_df.sort_values('date', ascending=False)
        
        return combined_df
    
    def list_connected_accounts(self) -> List[str]:
        """Get list of all connected bank accounts"""
        return list(self.access_tokens.keys())
    
    def remove_account(self, institution_name: str) -> bool:
        """
        Disconnect a bank account
        
        Args:
            institution_name: Name of institution to disconnect
            
        Returns:
            True if successful
        """
        if institution_name in self.access_tokens:
            del self.access_tokens[institution_name]
            return True
        return False


# Helper function for testing in sandbox mode
def test_plaid_connection():
    """
    Test function to verify Plaid credentials work
    Only works in sandbox mode with test credentials
    """
    try:
        connector = PlaidConnector()
        print(f"✅ Plaid client initialized successfully!")
        print(f"   Environment: {connector.env}")
        print(f"   Client ID: {connector.client_id[:10]}...")
        
        # Try creating a link token
        result = connector.create_link_token()
        if 'error' in result:
            print(f"❌ Error creating link token: {result['error']}")
            return False
        else:
            print(f"✅ Link token created successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    # Run test when script is executed directly
    print("Testing Plaid connection...")
    test_plaid_connection()
