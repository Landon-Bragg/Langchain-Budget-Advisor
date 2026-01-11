"""
Smart CSV Processor - Handles any bank CSV format
"""
import pandas as pd
from datetime import datetime
import re

class SmartCSVProcessor:
    """Intelligently processes CSV files from any bank"""
    
    def __init__(self):
        # Common column name patterns for date columns
        self.date_patterns = [
            'date', 'transaction date', 'post date', 'posting date', 
            'trans date', 'transaction_date', 'posted date', 'value date'
        ]
        
        # Common column name patterns for amount columns
        self.amount_patterns = [
            'amount', 'transaction amount', 'debit', 'credit', 
            'value', 'transaction_amount', 'sum', 'total'
        ]
        
        # Common column name patterns for description columns
        self.description_patterns = [
            'description', 'memo', 'details', 'transaction details',
            'merchant', 'name', 'payee', 'reference', 'transaction_description',
            'narrative', 'transaction type', 'category'
        ]
    
    def process_csv(self, file_path_or_df):
        """
        Process any CSV file and extract transactions
        
        Args:
            file_path_or_df: Path to CSV file or pandas DataFrame
            
        Returns:
            DataFrame with standardized columns: date, description, amount
        """
        # Load CSV if file path provided
        if isinstance(file_path_or_df, str):
            df = pd.read_csv(file_path_or_df)
        else:
            df = file_path_or_df.copy()
        
        # Make column names lowercase for easier matching
        df.columns = df.columns.str.lower().str.strip()
        
        # Find the right columns
        date_col = self._find_column(df, self.date_patterns)
        amount_col = self._find_amount_column(df)
        description_cols = self._find_description_columns(df)
        
        if not date_col:
            raise ValueError("Could not find date column. Please ensure CSV has a date column.")
        
        if not amount_col:
            raise ValueError("Could not find amount column. Please ensure CSV has an amount column.")
        
        if not description_cols:
            raise ValueError("Could not find description columns. Please ensure CSV has description/merchant info.")
        
        # Create standardized DataFrame
        result_df = pd.DataFrame()
        
        # Process date
        result_df['date'] = pd.to_datetime(df[date_col], errors='coerce')
        
        # Combine all description columns into rich description
        result_df['description'] = self._combine_descriptions(df, description_cols)
        
        # Process amount
        result_df['amount'] = self._process_amount(df, amount_col)
        
        # Remove any rows with missing critical data
        result_df = result_df.dropna(subset=['date', 'amount'])
        
        # Sort by date
        result_df = result_df.sort_values('date', ascending=False).reset_index(drop=True)
        
        return result_df
    
    def _find_column(self, df, patterns):
        """Find column that matches any of the patterns"""
        for col in df.columns:
            col_lower = col.lower().strip()
            for pattern in patterns:
                if pattern.lower() in col_lower:
                    return col
        return None
    
    def _find_amount_column(self, df):
        """Find amount column, handling debit/credit splits"""
        # First try to find a single amount column
        amount_col = self._find_column(df, self.amount_patterns)
        if amount_col:
            return amount_col
        
        # Check if there are separate debit/credit columns
        debit_col = None
        credit_col = None
        
        for col in df.columns:
            col_lower = col.lower().strip()
            if 'debit' in col_lower or 'withdrawal' in col_lower or 'outgoing' in col_lower:
                debit_col = col
            elif 'credit' in col_lower or 'deposit' in col_lower or 'incoming' in col_lower:
                credit_col = col
        
        if debit_col and credit_col:
            # We'll handle this in _process_amount
            return (debit_col, credit_col)
        
        return amount_col
    
    def _find_description_columns(self, df):
        """Find ALL columns that might contain useful description info"""
        desc_cols = []
        
        # Find explicit description columns
        for pattern in self.description_patterns:
            for col in df.columns:
                col_lower = col.lower().strip()
                if pattern.lower() in col_lower and col not in desc_cols:
                    desc_cols.append(col)
        
        # If we found some, return them
        if desc_cols:
            return desc_cols
        
        # Otherwise, include any text columns that aren't date or amount
        for col in df.columns:
            if col not in desc_cols:
                # Check if it's a text column with useful info
                sample = df[col].dropna().head(5)
                if len(sample) > 0 and sample.dtype == 'object':
                    # Skip if it looks like a date or number
                    first_val = str(sample.iloc[0])
                    if not re.match(r'^\d+[\.\,]?\d*$', first_val):  # Not just a number
                        desc_cols.append(col)
        
        return desc_cols if desc_cols else [df.columns[0]]  # Fallback to first column
    
    def _combine_descriptions(self, df, description_cols):
        """Combine multiple description columns into one rich description"""
        combined = []
        
        for idx, row in df.iterrows():
            parts = []
            for col in description_cols:
                val = str(row[col]).strip()
                if val and val.lower() not in ['nan', 'none', '']:
                    parts.append(val)
            
            # Join with | separator
            combined_desc = ' | '.join(parts) if parts else 'Unknown Transaction'
            combined.append(combined_desc)
        
        return combined
    
    def _process_amount(self, df, amount_col):
        """Process amount column, handling various formats"""
        if isinstance(amount_col, tuple):
            # Handle separate debit/credit columns
            debit_col, credit_col = amount_col
            
            amounts = []
            for idx, row in df.iterrows():
                debit = self._clean_amount(row[debit_col])
                credit = self._clean_amount(row[credit_col])
                
                if pd.notna(debit) and debit != 0:
                    amounts.append(-abs(debit))  # Debits are negative
                elif pd.notna(credit) and credit != 0:
                    amounts.append(abs(credit))  # Credits are positive
                else:
                    amounts.append(0)
            
            return amounts
        else:
            # Single amount column
            return df[amount_col].apply(self._clean_amount)
    
    def _clean_amount(self, value):
        """Clean and convert amount to float"""
        if pd.isna(value):
            return 0
        
        # Convert to string and clean
        val_str = str(value).strip()
        
        # Remove currency symbols and commas
        val_str = val_str.replace('$', '').replace('£', '').replace('€', '')
        val_str = val_str.replace(',', '').replace(' ', '')
        
        # Handle parentheses (negative numbers)
        if '(' in val_str and ')' in val_str:
            val_str = '-' + val_str.replace('(', '').replace(')', '')
        
        try:
            return float(val_str)
        except:
            return 0
    
    def preview_mapping(self, file_path_or_df):
        """
        Preview what columns will be used
        Useful for debugging
        """
        if isinstance(file_path_or_df, str):
            df = pd.read_csv(file_path_or_df)
        else:
            df = file_path_or_df.copy()
        
        df.columns = df.columns.str.lower().str.strip()
        
        date_col = self._find_column(df, self.date_patterns)
        amount_col = self._find_amount_column(df)
        description_cols = self._find_description_columns(df)
        
        return {
            'date_column': date_col,
            'amount_column': amount_col,
            'description_columns': description_cols,
            'all_columns': list(df.columns),
            'sample_row': df.iloc[0].to_dict() if len(df) > 0 else {}
        }