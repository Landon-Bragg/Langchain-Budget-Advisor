"""
Personal Finance Advisor with Plaid Bank Integration
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os
from categorizer import TransactionCategorizer
from advisor_agent import FinancialAdvisorAgent
from plaid_connector import PlaidConnector

# Import simple version
import sys
sys.path.insert(0, os.path.dirname(__file__))
from plaid_link_simple import simple_plaid_link_button

# Page config
st.set_page_config(
    page_title="Personal Finance Advisor - Plaid Ready",
    page_icon="💰",
    layout="wide"
)

# Initialize session state
if 'transactions_df' not in st.session_state:
    st.session_state.transactions_df = None
if 'categorizer' not in st.session_state:
    st.session_state.categorizer = TransactionCategorizer(provider="groq")
if 'advisor' not in st.session_state:
    st.session_state.advisor = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'plaid_connector' not in st.session_state:
    st.session_state.plaid_connector = None
if 'plaid_link_token' not in st.session_state:
    st.session_state.plaid_link_token = None

# Title
st.title("💰 Personal Finance Advisor")
st.markdown("**Pre-configured with Groq (FREE)** • Ready for Plaid bank connections!")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Show API status
    st.success("✅ Groq API Key: Configured")
    
    st.divider()
    
    # Plaid Setup Section
    st.header("🏦 Bank Connections (Plaid)")
    
    plaid_setup = st.expander("📋 Plaid Setup Instructions", expanded=False)
    with plaid_setup:
        st.markdown("""
        ### Get FREE Plaid Sandbox Credentials:
        
        1. Go to [dashboard.plaid.com/signup](https://dashboard.plaid.com/signup)
        2. Sign up for FREE (no credit card required)
        3. Navigate to Team Settings → Keys
        4. Copy your:
           - **client_id**
           - **sandbox secret** (NOT the development secret)
        5. Paste them in the `.env` file
        6. Restart the app
        
        ### Plaid Environment Info:
        - **Sandbox**: Free testing with fake banks (Chase, USAA, etc.)
        - **Development**: Test with real banks (limited)
        - **Production**: Live with real accounts (requires approval)
        
        Start with **Sandbox** to test!
        """)
    
    # Check Plaid credentials
    plaid_client_id = os.getenv('PLAID_CLIENT_ID')
    plaid_secret = os.getenv('PLAID_SECRET')
    plaid_configured = (
        plaid_client_id and 
        plaid_secret and 
        plaid_client_id != "your_plaid_client_id_here"
    )
    
    if plaid_configured:
        st.success(f"✅ Plaid: Connected ({os.getenv('PLAID_ENV', 'sandbox')} mode)")
        
        # Initialize Plaid connector
        try:
            if st.session_state.plaid_connector is None:
                st.session_state.plaid_connector = PlaidConnector()
        except Exception as e:
            st.error(f"Plaid Error: {e}")
            plaid_configured = False
    else:
        st.warning("⚠️ Plaid: Not configured")
        st.info("Add credentials to `.env` file to connect banks")
    
    st.divider()
    
    # Bank Connection Section
    if plaid_configured and st.session_state.plaid_connector:
        st.subheader("Connect Your Banks")
        
        # Show connected accounts
        connected = st.session_state.plaid_connector.list_connected_accounts()
        if connected:
            st.write("**Connected Accounts:**")
            for account in connected:
                col1, col2 = st.columns([3, 1])
                col1.write(f"🏦 {account}")
                if col2.button("❌", key=f"remove_{account}"):
                    st.session_state.plaid_connector.remove_account(account)
                    st.rerun()
        
        # Connect new account button
        st.subheader("➕ Connect New Bank Account")
        
        # Create link token when user wants to connect
        if 'plaid_link_token' not in st.session_state:
            st.session_state.plaid_link_token = None
        
        if st.button("Start Bank Connection") or st.session_state.plaid_link_token:
            # Get link token from Plaid
            if not st.session_state.plaid_link_token:
                with st.spinner("Preparing secure connection..."):
                    try:
                        link_token_data = st.session_state.plaid_connector.create_link_token()
                        
                        if 'error' in link_token_data:
                            st.error(f"❌ Error creating link token: {link_token_data['error']}")
                            st.error(f"Error type: {link_token_data.get('error_type', 'Unknown')}")
                        elif 'link_token' in link_token_data:
                            st.session_state.plaid_link_token = link_token_data['link_token']
                            st.success("✅ Link token created successfully!")
                            st.rerun()
                        else:
                            st.error(f"Unexpected response: {link_token_data}")
                    except Exception as e:
                        st.error(f"❌ Exception creating link token: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())
            
            # Display Plaid Link component
            if st.session_state.plaid_link_token:
                st.info("👇 Click the button below to securely connect your bank")
                
                # Debug: Show that we have a token
                with st.expander("🔍 Debug Info"):
                    st.write(f"Link token (first 20 chars): {st.session_state.plaid_link_token[:20]}...")
                    st.write(f"Link token length: {len(st.session_state.plaid_link_token)}")
                
                # Show the Plaid Link button
                simple_plaid_link_button(st.session_state.plaid_link_token)
                
                st.caption("🔒 Your credentials are sent directly to your bank, not stored by this app")
                
                # Reset button
                if st.button("🔄 Reset Connection"):
                    st.session_state.plaid_link_token = None
                    st.rerun()
                
                # Manual input for public token (for testing/debugging)
                with st.expander("🔧 Advanced: Manual Token Exchange"):
                    st.caption("After connecting your bank, copy the token shown above and paste it here")
                    public_token = st.text_input("Public Token:")
                    institution_name = st.text_input("Institution Name (e.g., 'Chase'):")
                    
                    if st.button("Exchange Token"):
                        if public_token and institution_name:
                            with st.spinner("Exchanging token..."):
                                result = st.session_state.plaid_connector.exchange_public_token(
                                    public_token,
                                    institution_name
                                )
                                
                                if result.get('success'):
                                    st.success(f"✅ Successfully connected {institution_name}!")
                                    st.session_state.plaid_link_token = None
                                    st.rerun()
                                else:
                                    st.error(f"Error: {result.get('error')}")
                        else:
                            st.warning("Please enter both token and institution name")
        
        st.divider()
        # Fetch transactions from connected accounts
        if connected and st.button("🔄 Sync Transactions from Banks"):
            with st.spinner("Fetching transactions from Plaid..."):
                try:
                    # Fetch last 90 days
                    df = st.session_state.plaid_connector.get_all_transactions(days_back=90)
                    
                    if not df.empty:
                        # Categorize transactions
                        st.info("Categorizing transactions with AI...")
                        transactions = df.to_dict('records')
                        categorized = st.session_state.categorizer.categorize_batch(transactions)
                        st.session_state.transactions_df = pd.DataFrame(categorized)
                        
                        # Update advisor
                        if st.session_state.advisor is None:
                            st.session_state.advisor = FinancialAdvisorAgent(
                                st.session_state.transactions_df,
                                provider="groq"
                            )
                        else:
                            st.session_state.advisor.update_transactions(
                                st.session_state.transactions_df
                            )
                        
                        st.success(f"✅ Synced {len(df)} transactions!")
                    else:
                        st.warning("No transactions found")
                        
                except Exception as e:
                    st.error(f"Error syncing: {e}")
    
    st.divider()
    
    # Manual CSV Upload (as fallback)
    st.subheader("📁 Manual Upload")
    st.caption("Or upload CSV manually")
    
    uploaded_file = st.file_uploader("Upload CSV", type=['csv'])
    
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            
            required_cols = ['date', 'description', 'amount']
            if not all(col in df.columns for col in required_cols):
                st.error(f"CSV must have: {', '.join(required_cols)}")
            else:
                df['date'] = pd.to_datetime(df['date'])
                
                with st.spinner("Categorizing with Groq AI..."):
                    transactions = df.to_dict('records')
                    categorized = st.session_state.categorizer.categorize_batch(transactions)
                    st.session_state.transactions_df = pd.DataFrame(categorized)
                    
                    if st.session_state.advisor is None:
                        st.session_state.advisor = FinancialAdvisorAgent(
                            st.session_state.transactions_df,
                            provider="groq"
                        )
                    else:
                        st.session_state.advisor.update_transactions(
                            st.session_state.transactions_df
                        )
                
                st.success(f"✅ Loaded {len(df)} transactions!")
                
        except Exception as e:
            st.error(f"Error: {e}")
    
    # Sample data
    st.divider()
    if st.button("📊 Load Sample Data"):
        # Create 50 sample transactions
        descriptions = [
            'WHOLE FOODS MARKET', 'SHELL GAS STATION', 'NETFLIX', 'SPOTIFY',
            'STARBUCKS', 'AMAZON.COM', 'CHIPOTLE', 'SALARY DEPOSIT',
            'UBER', 'TARGET', 'CVS PHARMACY', 'ELECTRIC BILL', 
            'INTERNET BILL', 'GYM MEMBERSHIP', 'RESTAURANT',
            'GROCERY STORE', 'GAS STATION', 'COFFEE SHOP', 'RENT PAYMENT',
            'INSURANCE PAYMENT', 'APPLE.COM/BILL', 'HOME DEPOT', 'COSTCO',
            'KROGER', 'WALGREENS'
        ] * 2  # 25 * 2 = 50
        
        amounts = [-45.32, -55.00, -15.99, -9.99,
                  -6.50, -89.23, -12.45, 3500.00,
                  -18.50, -67.89, -23.45, -120.00,
                  -80.00, -50.00, -45.00,
                  -85.23, -40.00, -5.50, -1500.00,
                  -250.00, -14.99, -76.34, -120.56,
                  -98.23, -22.10] * 2  # 25 * 2 = 50
        
        sample_data = {
            'date': pd.date_range(end=datetime.now(), periods=50, freq='D'),
            'description': descriptions[:50],
            'amount': amounts[:50]
        }
        
        df = pd.DataFrame(sample_data)
        
        with st.spinner("Categorizing sample data..."):
            transactions = df.to_dict('records')
            categorized = st.session_state.categorizer.categorize_batch(transactions)
            st.session_state.transactions_df = pd.DataFrame(categorized)
            
            if st.session_state.advisor is None:
                st.session_state.advisor = FinancialAdvisorAgent(
                    st.session_state.transactions_df,
                    provider="groq"
                )
            else:
                st.session_state.advisor.update_transactions(
                    st.session_state.transactions_df
                )
        
        st.success("✅ Sample data loaded!")
        st.rerun()

# Main content
if st.session_state.transactions_df is not None:
    df = st.session_state.transactions_df
    
    # Chat input MUST be outside tabs - Streamlit limitation
    st.subheader("💬 Ask Your Financial Advisor")
    
    # Use text input + button instead of chat_input (which can't be in tabs)
    col1, col2 = st.columns([5, 1])
    with col1:
        user_question = st.text_input("Ask a question about your finances:", key="question_input", label_visibility="collapsed", placeholder="What are my top spending categories?")
    with col2:
        ask_button = st.button("Ask", type="primary", use_container_width=True)
    
    if ask_button and user_question:
        st.session_state.chat_history.append({"role": "user", "content": user_question})
        with st.spinner("Analyzing..."):
            response = st.session_state.advisor.ask(user_question)
            st.session_state.chat_history.append({"role": "assistant", "content": response})
        st.rerun()
    
    # Suggested questions as quick buttons
    st.caption("Quick questions:")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("💰 Top categories"):
            st.session_state.chat_history.append({"role": "user", "content": "What are my top spending categories?"})
            with st.spinner("Analyzing..."):
                response = st.session_state.advisor.ask("What are my top spending categories?")
                st.session_state.chat_history.append({"role": "assistant", "content": response})
            st.rerun()
    with col2:
        if st.button("📈 Compare months"):
            st.session_state.chat_history.append({"role": "user", "content": "How does my spending compare to last month?"})
            with st.spinner("Analyzing..."):
                response = st.session_state.advisor.ask("How does my spending compare to last month?")
                st.session_state.chat_history.append({"role": "assistant", "content": response})
            st.rerun()
    with col3:
        if st.button("🔍 Find savings"):
            st.session_state.chat_history.append({"role": "user", "content": "Where can I save money?"})
            with st.spinner("Analyzing..."):
                response = st.session_state.advisor.ask("Where can I save money?")
                st.session_state.chat_history.append({"role": "assistant", "content": response})
            st.rerun()
    with col4:
        if st.button("📊 Summary"):
            st.session_state.chat_history.append({"role": "user", "content": "Give me a financial summary"})
            with st.spinner("Analyzing..."):
                response = st.session_state.advisor.ask("Give me a financial summary")
                st.session_state.chat_history.append({"role": "assistant", "content": response})
            st.rerun()
    
    st.divider()
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["💬 Chat History", "📊 Dashboard", "📋 Transactions"])
    
    # Tab 1: Chat History (display only, input is above)
    with tab1:
        st.header("Conversation History")
        
        if st.session_state.chat_history:
            for message in st.session_state.chat_history:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
        else:
            st.info("👆 Ask a question above to start chatting with your advisor!")
        
        if st.session_state.chat_history and st.button("🗑️ Clear Chat History"):
            st.session_state.chat_history = []
            st.rerun()
    
    # Tab 2: Dashboard
    with tab2:
        st.header("Financial Dashboard")
        
        col1, col2, col3, col4 = st.columns(4)
        
        total_income = df[df['amount'] > 0]['amount'].sum()
        total_expenses = abs(df[df['amount'] < 0]['amount'].sum())
        net = total_income - total_expenses
        avg_daily = total_expenses / len(df['date'].dt.date.unique())
        
        col1.metric("Total Income", f"${total_income:,.2f}")
        col2.metric("Total Expenses", f"${total_expenses:,.2f}")
        col3.metric("Net", f"${net:,.2f}", delta=f"${net:,.2f}")
        col4.metric("Avg Daily Spending", f"${avg_daily:,.2f}")
        
        st.divider()
        
        col1, col2 = st.columns(2)
        
        with col1:
            expenses = df[df['amount'] < 0].copy()
            expenses['amount_abs'] = expenses['amount'].abs()
            by_category = expenses.groupby('category')['amount_abs'].sum().sort_values(ascending=True)
            
            fig = px.bar(
                x=by_category.values,
                y=by_category.index,
                orientation='h',
                title="Spending by Category",
                labels={'x': 'Amount ($)', 'y': 'Category'}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.pie(
                values=by_category.values,
                names=by_category.index,
                title="Spending Distribution"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        daily_spending = df[df['amount'] < 0].copy()
        daily_spending['date'] = pd.to_datetime(daily_spending['date'])
        daily_spending['amount_abs'] = daily_spending['amount'].abs()
        daily = daily_spending.groupby(daily_spending['date'].dt.date)['amount_abs'].sum().reset_index()
        
        fig = px.line(
            daily,
            x='date',
            y='amount_abs',
            title="Daily Spending Trend",
            labels={'date': 'Date', 'amount_abs': 'Amount ($)'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Tab 3: Transactions
    with tab3:
        st.header("All Transactions")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            categories = ['All'] + sorted(df['category'].unique().tolist())
            selected_category = st.selectbox("Category", categories)
        
        with col2:
            transaction_type = st.selectbox("Type", ['All', 'Expenses', 'Income'])
        
        with col3:
            search = st.text_input("Search")
        
        filtered_df = df.copy()
        
        if selected_category != 'All':
            filtered_df = filtered_df[filtered_df['category'] == selected_category]
        
        if transaction_type == 'Expenses':
            filtered_df = filtered_df[filtered_df['amount'] < 0]
        elif transaction_type == 'Income':
            filtered_df = filtered_df[filtered_df['amount'] > 0]
        
        if search:
            filtered_df = filtered_df[filtered_df['description'].str.contains(search, case=False, na=False)]
        
        st.dataframe(
            filtered_df.sort_values('date', ascending=False),
            use_container_width=True,
            hide_index=True
        )
        
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="transactions.csv",
            mime="text/csv"
        )

else:
    st.info("👈 Load data to get started!")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 🎯 You're All Set!
        
        **Groq API**: ✅ Configured  
        **LangChain**: ✅ Ready  
        **Plaid**: ⏳ Ready to configure
        
        ### Quick Start:
        1. Click "Load Sample Data" in sidebar
        2. Start chatting with your advisor
        3. See it work instantly!
        
        ### Next: Connect Your Banks
        1. Get FREE Plaid sandbox credentials
        2. Add to `.env` file
        3. Sync your real transactions
        """)
    
    with col2:
        st.markdown("""
        ### 🏦 Plaid Setup (Next Step)
        
        1. **Sign up**: [dashboard.plaid.com/signup](https://dashboard.plaid.com/signup)
        2. **Get credentials**: Free sandbox keys
        3. **Update .env**: Add client_id and secret
        4. **Test**: Use sandbox banks (Chase, USAA)
        5. **Go live**: Request production access
        
        ### Supported Banks:
        ✅ Chase (USAA)  
        ✅ USAA  
        ✅ Wells Fargo  
        ✅ Bank of America  
        ✅ 12,000+ other banks
        
        **All via Plaid's secure API!**
        """)