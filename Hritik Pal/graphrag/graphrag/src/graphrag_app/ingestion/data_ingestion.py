"""
Data ingestion module for CSV and Excel files
"""

import pandas as pd
import os
from typing import List, Dict, Any


class DataIngestion:
    """Handle CSV and Excel file ingestion"""
    
    def __init__(self):
        """Initialize the data ingestion handler"""
        self.data = None
        self.file_path = None
        self.file_type = None
    
    def load_file(self, file_path: str) -> pd.DataFrame:
        """
        Load CSV or Excel file
        
        Args:
            file_path: Path to the CSV or Excel file
            
        Returns:
            pandas DataFrame with the loaded data
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        self.file_path = file_path
        
        # Determine file type
        if file_path.endswith('.csv'):
            self.file_type = 'csv'
            self.data = pd.read_csv(file_path)
        elif file_path.endswith(('.xlsx', '.xls')):
            self.file_type = 'excel'
            self.data = pd.read_excel(file_path)
        else:
            raise ValueError("File must be CSV or Excel format (.csv, .xlsx, .xls)")

        self.data.columns = [str(column) for column in self.data.columns]
        
        print(f"[OK] Loaded {self.file_type.upper()} file: {file_path}")
        print(f"  Shape: {self.data.shape}")
        print(f"  Columns: {list(self.data.columns)}")
        
        return self.data
    
    def get_data(self) -> pd.DataFrame:
        """Get the loaded data"""
        return self.data
    
    def get_columns(self) -> List[str]:
        """Get column names"""
        if self.data is None:
            raise ValueError("No data loaded yet")
        return list(self.data.columns)
    
    def get_preview(self, rows: int = 5) -> pd.DataFrame:
        """Get preview of the data"""
        if self.data is None:
            raise ValueError("No data loaded yet")
        return self.data.head(rows)
    
    def get_data_types(self) -> Dict[str, str]:
        """Get data types of columns"""
        if self.data is None:
            raise ValueError("No data loaded yet")
        return dict(self.data.dtypes)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get basic statistics about the data"""
        if self.data is None:
            raise ValueError("No data loaded yet")
        return {
            "total_rows": len(self.data),
            "total_columns": len(self.data.columns),
            "columns": list(self.data.columns),
            "data_types": dict(self.data.dtypes),
            "missing_values": dict(self.data.isnull().sum())
        }
