from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
from datetime import datetime
import pandas as pd
import io
import csv
import json
import re
from collections import Counter
from template_manager import template_manager

app = FastAPI(title="Report Analyzer with AI", version="3.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SIMPLE AI CLASS
class SimpleAI:
    def analyze(self, text):
        text_lower = text.lower()
        words = text_lower.split()
        
        # Sentiment words
        positive = {'good', 'great', 'excellent', 'success', 'completed', 
                   'fixed', 'working', 'improved', 'finished', 'achieved',
                   'positive', 'better', 'fast', 'efficient', 'solved',
                   'completed', 'deployed', 'resolved', 'launched'}
        
        negative = {'bad', 'poor', 'failed', 'issue', 'problem', 'error',
                   'broken', 'slow', 'delayed', 'blocked', 'stuck',
                   'negative', 'worse', 'difficult', 'challenge', 'risk',
                   'concern', 'bug', 'crash', 'down', 'outage'}
        
        pos_count = sum(1 for w in words if w in positive)
        neg_count = sum(1 for w in words if w in negative)
        
        # Sentiment
        if pos_count > neg_count:
            sentiment = "positive"
            score = pos_count / max(pos_count + neg_count, 1)
        elif neg_count > pos_count:
            sentiment = "negative"
            score = -neg_count / max(pos_count + neg_count, 1)
        else:
            sentiment = "neutral"
            score = 0
        
        # Topics (common project words)
        topics = []
        project_words = ['bug', 'feature', 'deploy', 'test', 'meeting', 'report',
                        'database', 'api', 'system', 'user', 'client', 'team',
                        'project', 'code', 'software', 'hardware', 'network',
                        'security', 'performance', 'update', 'version', 'release']
        
        for topic in project_words:
            if topic in text_lower:
                topics.append(topic)
        
        # If no topics found, use most frequent words
        if not topics:
            word_counts = Counter([w for w in words if len(w) > 3])
            topics = [word for word, count in word_counts.most_common(5)]
        
        # Summary (first meaningful part)
        lines = text.split('\n')
        summary = ""
        for line in lines:
            line = line.strip()
            if len(line) > 30 and not line.startswith(('=', '-', '#', '*')):
                summary = line[:150] + "..." if len(line) > 150 else line
                break
        
        if not summary:
            summary = text[:100] + "..." if len(text) > 100 else text
        
        # Check for urgency
        urgent_words = {'urgent', 'immediate', 'asap', 'critical', 'emergency', 'important'}
        urgency = "high" if any(word in text_lower for word in urgent_words) else "medium" if neg_count > 0 else "low"
        
        # Find accomplishments and problems
        accomplishments = []
        problems = []
        
        for line in lines:
            line_lower = line.lower()
            if any(word in line_lower for word in positive):
                if len(line) > 10:
                    accomplishments.append(line.strip())
            if any(word in line_lower for word in negative):
                if len(line) > 10:
                    problems.append(line.strip())
        
        return {
            "sentiment": {
                "label": sentiment,
                "score": round(score, 2),
                "positive_words": pos_count,
                "negative_words": neg_count
            },
            "topics": topics[:5],
            "summary": summary,
            "word_count": len(words),
            "urgency": urgency,
            "accomplishments": accomplishments[:3],
            "problems": problems[:3],
            "analysis_complete": True
        }

# Create AI instance
ai = SimpleAI()

# Database setup
def setup_db():
    conn = sqlite3.connect('reports.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            department TEXT,
            report_date TEXT,
            filename TEXT,
            content TEXT,
            summary TEXT,
            word_count INTEGER,
            upload_date TEXT,
            file_type TEXT,
            ai_analysis TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print("✅ Database ready with AI support")

setup_db()

# File processing functions
def detect_file_type(filename):
    filename_lower = filename.lower()
    if filename_lower.endswith('.xlsx') or filename_lower.endswith('.xls'):
        return 'excel'
    elif filename_lower.endswith('.csv'):
        return 'csv'
    elif filename_lower.endswith('.txt'):
        return 'text'
    elif filename_lower.endswith('.pdf'):
        return 'pdf'
    elif filename_lower.endswith('.docx') or filename_lower.endswith('.doc'):
        return 'word'
    else:
        return 'unknown'

def process_excel(content):
    try:
        excel_file = pd.ExcelFile(io.BytesIO(content))
        text_parts = []
        for sheet_name in excel_file.sheet_names[:2]:  # First 2 sheets
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
            text_parts.append(f"Sheet: {sheet_name} ({len(df)} rows)")
            # Add first few rows as text
            for i, row in df.head(3).iterrows():
                text_parts.append(str(row.to_dict()))
        return "\n".join(text_parts)
    except Exception as e:
        return f"Excel content (error: {str(e)})"

def process_csv(content):
    try:
        content_str = content.decode('utf-8', errors='ignore')
        lines = content_str.split('\n')
        return "\n".join(lines[:10])  # First 10 lines
    except:
        return "CSV content"

@app.get("/")
def home():
    return {
        "message": "✅ Report Analyzer with Simple AI", 
        "ai": "active",
        "endpoints": ["/api/upload", "/api/reports", "/api/stats", "/api/health"]
    }

@app.post("/api/upload")
async def upload_report(
    department: str = Form(...), 
    date: str = Form(...), 
    file: UploadFile = File(...)
):
    try:
        print(f"📤 Uploading: {file.filename}")
        
        content_bytes = await file.read()
        file_type = detect_file_type(file.filename)
        
        # Get text content based on file type
        if file_type == 'excel':
            content = process_excel(content_bytes)
        elif file_type == 'csv':
            content = process_csv(content_bytes)
        else:
            content = content_bytes.decode('utf-8', errors='ignore')
        
        print(f"📝 Content length: {len(content)} chars")
        
        # Run AI analysis
        print("🤖 Running AI analysis...")
        ai_result = ai.analyze(content)
        print(f"✅ AI analysis complete: {ai_result['sentiment']['label']}")
        
        # Save to database
        conn = sqlite3.connect('reports.db', check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO reports 
            (department, report_date, filename, content, summary, word_count, upload_date, file_type, ai_analysis)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            department, 
            date, 
            file.filename, 
            content,
            ai_result["summary"], 
            ai_result["word_count"],
            datetime.now().isoformat(), 
            file_type,
            json.dumps(ai_result)
        ))
        
        conn.commit()
        conn.close()
        
        print("💾 Saved to database")
        
        return {
            "success": True,
            "message": f"✅ {file_type.upper()} file analyzed with AI!",
            "filename": file.filename,
            "department": department,
            "file_type": file_type,
            "word_count": ai_result["word_count"],
            "ai_analysis": ai_result
        }
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {"success": False, "error": str(e)}

@app.get("/api/reports")
def get_reports():
    try:
        conn = sqlite3.connect('reports.db', check_same_thread=False)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM reports ORDER BY id DESC LIMIT 20')
        
        reports = []
        for row in cursor.fetchall():
            report = dict(row)
            if report.get('ai_analysis'):
                try:
                    report['ai_analysis'] = json.loads(report['ai_analysis'])
                except:
                    report['ai_analysis'] = None
            reports.append(report)
        
        conn.close()
        return {"reports": reports, "count": len(reports)}
        
    except Exception as e:
        return {"error": str(e), "reports": []}

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
        
        # Get sentiment distribution from AI analysis
        cursor.execute('SELECT ai_analysis FROM reports WHERE ai_analysis IS NOT NULL')
        sentiments = {'positive': 0, 'negative': 0, 'neutral': 0}
        
        for row in cursor.fetchall():
            try:
                analysis = json.loads(row[0])
                sentiment = analysis.get('sentiment', {}).get('label', 'neutral')
                if sentiment in sentiments:
                    sentiments[sentiment] += 1
            except:
                pass
        
        conn.close()
        
        return {
            "total_reports": total,
            "total_departments": departments,
            "today_reports": today,
            "sentiment_distribution": sentiments,
            "ai_enabled": True,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {"error": str(e)}
    

@app.post("/api/analyze-template")
async def analyze_template(
    department: str = Form(...),
    file: UploadFile = File(...)
):
    """Analyze a report to learn/update department template"""
    try:
        content_bytes = await file.read()
        content = content_bytes.decode('utf-8', errors='ignore')
        
        # Analyze template structure
        template = template_manager.analyze_report_structure(content, department)
        
        # Save/update template
        template_manager.save_template(department, template)
        
        return {
            "success": True,
            "message": f"Template analyzed for {department}",
            "template": template,
            "guide": template_manager.generate_template_guide(department)
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/templates/{department}")
def get_department_template(department: str):
    """Get template for a department"""
    template = template_manager.get_template(department)
    if template:
        return {
            "success": True,
            "template": template,
            "guide": template_manager.generate_template_guide(department)
        }
    return {"success": False, "error": "No template found"}

@app.post("/api/validate-report")
async def validate_report(
    department: str = Form(...),
    file: UploadFile = File(...)
):
    """Validate report against department template"""
    try:
        content_bytes = await file.read()
        content = content_bytes.decode('utf-8', errors='ignore')
        
        validation = template_manager.validate_report(content, department)
        
        return {
            "success": True,
            "validation": validation,
            "structured_data": template_manager.extract_structured_data(content, department)
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/templates")
def get_all_templates():
    """Get all learned templates"""
    return {
        "success": True,
        "templates": template_manager.get_all_templates(),
        "count": len(template_manager.templates)
    }

@app.post("/api/set-template-sections")
async def set_template_sections(
    department: str = Form(...),
    required_sections: str = Form(...)  # JSON array
):
    """Set required sections for a department template"""
    try:
        sections = json.loads(required_sections)
        
        template = template_manager.get_template(department)
        if template:
            template['required_sections'] = sections
            template_manager.save_template(department, template)
            
            return {
                "success": True,
                "message": f"Updated template for {department}",
                "template": template
            }
        
        return {"success": False, "error": "Template not found. Analyze a report first."}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy", 
        "timestamp": datetime.now().isoformat(),
        "ai": "active"
    }

if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("🚀 REPORT ANALYZER WITH SIMPLE AI")
    print("=" * 50)
    print("🤖 AI Features: Sentiment, Topics, Urgency")
    print("📡 API: http://localhost:8000")
    print("📚 Docs: http://localhost:8000/docs")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)