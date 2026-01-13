from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
from datetime import datetime
import uvicorn

app = FastAPI()

# Allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup database
def setup_db():
    conn = sqlite3.connect('reports.db', check_same_thread=False)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            department TEXT,
            report_date TEXT,
            filename TEXT,
            content TEXT,
            summary TEXT,
            word_count INTEGER,
            upload_date TEXT
        )
    ''')
    conn.close()

setup_db()

@app.get("/")
def home():
    return {"message": "✅ Report Analyzer API is running!", "status": "active"}

@app.post("/api/upload")
async def upload_report(
    department: str = Form(...),
    date: str = Form(...),
    file: UploadFile = File(...)
):
    try:
        # Read file content
        content_bytes = await file.read()
        content = content_bytes.decode('utf-8', errors='ignore')
        
        # Simple analysis
        word_count = len(content.split())
        summary = content[:200] + "..." if len(content) > 200 else content
        
        # Save to database
        conn = sqlite3.connect('reports.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO reports (department, report_date, filename, content, summary, word_count, upload_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (department, date, file.filename, content, summary, word_count, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "Report uploaded and analyzed successfully!",
            "filename": file.filename,
            "department": department,
            "word_count": word_count,
            "summary": summary
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/reports")
def get_reports():
    conn = sqlite3.connect('reports.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM reports ORDER BY id DESC LIMIT 50')
    reports = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"reports": reports, "count": len(reports)}

@app.get("/api/stats")
def get_stats():
    conn = sqlite3.connect('reports.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM reports')
    total = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(DISTINCT department) FROM reports')
    departments = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM reports WHERE DATE(upload_date) = DATE("now")')
    today = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "total_reports": total,
        "total_departments": departments,
        "today_reports": today,
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    print("🚀 Starting Report Analyzer Backend...")
    print("📡 API: http://localhost:8000")
    print("📚 Docs: http://localhost:8000/docs")
    print("\nPress Ctrl+C to stop\n")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)