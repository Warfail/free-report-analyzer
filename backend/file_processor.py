import pandas as pd
import io
import csv
from typing import Dict, List, Any

class FileProcessor:
    @staticmethod
    def process_excel(file_bytes: bytes) -> Dict[str, Any]:
        """Process Excel file and extract structured data"""
        try:
            # Read all sheets
            excel_data = pd.read_excel(io.BytesIO(file_bytes), sheet_name=None)
            
            result = {
                "type": "excel",
                "sheets": [],
                "total_rows": 0,
                "total_columns": 0,
                "content": ""
            }
            
            text_parts = []
            for sheet_name, df in excel_data.items():
                sheet_info = {
                    "name": sheet_name,
                    "rows": len(df),
                    "columns": len(df.columns),
                    "headers": list(df.columns)
                }
                result["sheets"].append(sheet_info)
                result["total_rows"] += len(df)
                result["total_columns"] += len(df.columns)
                
                # Convert to text
                text_parts.append(f"=== {sheet_name} ===")
                text_parts.append(df.to_string(index=False))
                text_parts.append("")
            
            result["content"] = "\n".join(text_parts)
            return result
            
        except Exception as e:
            return {"type": "excel", "error": str(e), "content": f"Error processing Excel: {str(e)}"}
    
    @staticmethod
    def process_csv(file_bytes: bytes) -> Dict[str, Any]:
        """Process CSV file and extract structured data"""
        try:
            content_str = file_bytes.decode('utf-8', errors='ignore')
            
            # Parse CSV
            csv_reader = list(csv.reader(io.StringIO(content_str)))
            
            result = {
                "type": "csv",
                "rows": len(csv_reader) - 1 if csv_reader else 0,  # Exclude header
                "columns": len(csv_reader[0]) if csv_reader else 0,
                "headers": csv_reader[0] if csv_reader else [],
                "content": ""
            }
            
            # Convert to readable text
            text_parts = []
            for i, row in enumerate(csv_reader):
                if i == 0:
                    text_parts.append("Headers: " + " | ".join(row))
                    text_parts.append("-" * 50)
                else:
                    text_parts.append(" | ".join(row))
            
            result["content"] = "\n".join(text_parts)
            return result
            
        except Exception as e:
            return {"type": "csv", "error": str(e), "content": f"Error processing CSV: {str(e)}"}
    
    @staticmethod
    def analyze_data(content: str, file_type: str) -> Dict[str, Any]:
        """Analyze the extracted data"""
        lines = content.split('\n')
        words = content.split()
        
        analysis = {
            "file_type": file_type,
            "line_count": len(lines),
            "word_count": len(words),
            "char_count": len(content),
            "avg_line_length": sum(len(line) for line in lines) / max(len(lines), 1)
        }
        
        # Extract potential metrics from content
        metrics_keywords = ['metric', 'kpi', 'target', 'goal', 'achieved', 'completed', 'progress']
        found_metrics = []
        
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in metrics_keywords):
                found_metrics.append(line[:100])  # First 100 chars
        
        analysis["found_metrics"] = found_metrics[:5]  # Limit to 5
        
        return analysis