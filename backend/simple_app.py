from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
from datetime import datetime
import pandas as pd
import io
import csv
import os

app = FastAPI(title="Free Report Analyzer", version="2.0.0")

# Allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup database with error handling
def setup_db():
    conn = sqlite3.connect('reports.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reports'")
    if not cursor.fetchone():
        # Create table if it doesn't exist
        cursor.execute('''
            CREATE TABLE reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                department TEXT,
                report_date TEXT,
                filename TEXT,
                content TEXT,
                summary TEXT,
                word_count INTEGER,
                upload_date TEXT,
                file_type TEXT
            )
        ''')
        print("✅ Created new database table")
    else:
        # Check if file_type column exists
        cursor.execute("PRAGMA table_info(reports)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'file_type' not in columns:
            try:
                cursor.execute('ALTER TABLE reports ADD COLUMN file_type TEXT')
                print("✅ Added file_type column to existing table")
            except Exception as e:
                print(f"⚠️ Could not add column: {e}")
    
    conn.commit()
    conn.close()

# Initialize database on startup
setup_db()

def detect_file_type(filename: str) -> str:
    """Detect file type from extension"""
    filename_lower = filename.lower()
    
    if filename_lower.endswith('.xlsx') or filename_lower.endswith('.xls'):
        return 'excel'
    elif filename_lower.endswith('.csv'):
        return 'csv'
    elif filename_lower.endswith('.pdf'):
        return 'pdf'
    elif filename_lower.endswith('.docx') or filename_lower.endswith('.doc'):
        return 'word'
    elif filename_lower.endswith('.txt'):
        return 'text'
    else:
        return 'unknown'

def process_excel_file(content: bytes) -> str:
    """Convert Excel file to text"""
    try:
        excel_file = pd.ExcelFile(io.BytesIO(content))
        text_parts = [f"Excel File: {len(excel_file.sheet_names)} sheet(s)"]
        
        for sheet_name in excel_file.sheet_names[:3]:  # Limit to 3 sheets
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
            text_parts.append(f"\n--- Sheet: {sheet_name} ({len(df)} rows) ---")
            
            # Get column names
            text_parts.append(f"Columns: {', '.join(df.columns.astype(str))}")
            
            # Add first 5 rows
            for i, row in df.head(5).iterrows():
                row_text = " | ".join([str(val)[:50] for val in row.values])  # Limit cell length
                text_parts.append(f"Row {i+1}: {row_text}")
        
        return "\n".join(text_parts)
    except Exception as e:
        return f"Excel File (Error in processing: {str(e)})"

def process_csv_file(content: bytes) -> str:
    """Convert CSV file to text"""
    try:
        content_str = content.decode('utf-8', errors='ignore')
        lines = content_str.split('\n')
        
        text_parts = [f"CSV File: {len(lines)} lines total"]
        
        if lines:
            # Show headers
            text_parts.append(f"Headers: {lines[0]}")
            text_parts.append("--- First 5 rows ---")
            
            # Show first 5 data rows
            for i, line in enumerate(lines[1:6], 1):
                if line.strip():
                    text_parts.append(f"Row {i}: {line}")
        
        return "\n".join(text_parts)
    except Exception as e:
        return f"CSV File Content (first 1000 chars):\n{content_str[:1000]}"

@app.get("/")
def home():
    return {
        "message": "✅ Report Analyzer API v2.0",
        "status": "active",
        "endpoints": ["/api/upload", "/api/reports", "/api/stats", "/api/health"]
    }

@app.post("/api/upload")
async def upload_report(
    department: str = Form(...),
    date: str = Form(...),
    file: UploadFile = File(...)
):
    try:
        print(f"📤 Upload: {file.filename} | Dept: {department}")
        
        content_bytes = await file.read()
        file_type = detect_file_type(file.filename)
        
        # Process based on file type
        if file_type == 'excel':
            content = process_excel_file(content_bytes)
        elif file_type == 'csv':
            content = process_csv_file(content_bytes)
        else:
            content = content_bytes.decode('utf-8', errors='ignore')
        
        word_count = len(content.split())
        summary = content[:300] + "..." if len(content) > 300 else content
        
        # Save to database
        conn = sqlite3.connect('reports.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO reports 
            (department, report_date, filename, content, summary, word_count, upload_date, file_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            department, date, file.filename, content, summary, 
            word_count, datetime.now().isoformat(), file_type
        ))
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": f"✅ {file_type.upper()} file uploaded!",
            "filename": file.filename,
            "department": department,
            "word_count": word_count,
            "file_type": file_type,
            "summary": summary[:100]
        }
        
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/reports")
def get_reports():
    try:
        conn = sqlite3.connect('reports.db', check_same_thread=False)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM reports ORDER BY id DESC LIMIT 50')
        reports = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return {"reports": reports, "count": len(reports)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/api/stats")
def get_stats():
    try:
        conn = sqlite3.connect('reports.db', check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM reports')
        total = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT department) FROM reports')
        departments = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM reports WHERE DATE(upload_date) = DATE("now")')
        today = cursor.fetchone()[0]
        
        # Try to get file types, but handle if column doesn't exist
        file_types = {}
        try:
            cursor.execute('SELECT file_type, COUNT(*) FROM reports GROUP BY file_type')
            file_types = {ftype: count for ftype, count in cursor.fetchall()}
        except:
            file_types = {"text": total}  # Default if column doesn't exist
        
        conn.close()
        
        return {
            "total_reports": total,
            "total_departments": departments,
            "today_reports": today,
            "file_types": file_types,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats error: {str(e)}")

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 REPORT ANALYZER BACKEND v2.0")
    print("=" * 50)
    print("📡 API: http://localhost:8000")
    print("📚 Docs: http://localhost:8000/docs")
    print("✅ Database initialized")
    print("=" * 50)
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)