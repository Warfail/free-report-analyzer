from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
from datetime import datetime
import pandas as pd
import io
import csv
import json
import re
from collections import Counter
import os
from dotenv import load_dotenv
from template_manager import template_manager

# Load environment variables
load_dotenv()

app = FastAPI(title="Report Analyzer with AI", version="4.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Gemini AI - USING NEW google-genai package
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyDSKpnuiEQpmgK2XcghNr89Pv1UUM6WCiI")

# Initialize Gemini
GEMINI_AVAILABLE = True
gemini_model = None

try:
    if GEMINI_API_KEY and GEMINI_API_KEY != "AIzaSyDSKpnuiEQpmgK2XcghNr89Pv1UUM6WCiI":
        # Use NEW google-genai package
        try:
            import google.genai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            
            # Get available models
            models = genai.list_models()
            print(f"✅ Available Gemini models: {[m.name for m in models]}")
            
            # Try to find a working model
            working_model = None
            for model in models:
                if 'generateContent' in model.supported_generation_methods:
                    working_model = model.name
                    break
            
            if working_model:
                gemini_model = genai.GenerativeModel(working_model)
                print(f"✅ Using model: {working_model}")
                GEMINI_AVAILABLE = True
            else:
                print("❌ No model supports generateContent")
                GEMINI_AVAILABLE = False
                
        except ImportError:
            print("❌ google-genai package not installed. Run: pip install google-genai")
            GEMINI_AVAILABLE = False
            
    else:
        print("⚠️ Gemini API key not configured. Using simple AI only.")
except Exception as e:
    print(f"⚠️ Gemini setup failed: {e}")
    GEMINI_AVAILABLE = False

class EnhancedAI:
    def __init__(self):
        self.positive_words = {'good', 'great', 'excellent', 'success', 'completed', 
                              'fixed', 'working', 'improved', 'finished', 'achieved',
                              'positive', 'better', 'fast', 'efficient', 'solved',
                              'completed', 'deployed', 'resolved', 'launched'}
        
        self.negative_words = {'bad', 'poor', 'failed', 'issue', 'problem', 'error',
                              'broken', 'slow', 'delayed', 'blocked', 'stuck',
                              'negative', 'worse', 'difficult', 'challenge', 'risk',
                              'concern', 'bug', 'crash', 'down', 'outage'}
        
        self.action_words = {'need', 'must', 'should', 'will', 'plan', 'next', 
                            'tomorrow', 'schedule', 'assign', 'action', 'task'}
    
    def analyze(self, text):
        """Basic AI analysis"""
        text_lower = text.lower()
        words = text_lower.split()
        
        # Sentiment analysis
        pos_count = sum(1 for w in words if w in self.positive_words)
        neg_count = sum(1 for w in words if w in self.negative_words)
        
        # Calculate sentiment
        if pos_count > neg_count:
            sentiment = "positive"
            score = pos_count / max(pos_count + neg_count, 1)
        elif neg_count > pos_count:
            sentiment = "negative"
            score = -neg_count / max(pos_count + neg_count, 1)
        else:
            sentiment = "neutral"
            score = 0
        
        # Topics extraction
        topics = self._extract_topics(text_lower)
        
        # Summary
        summary = self._generate_summary(text)
        
        # Urgency detection
        urgency = self._detect_urgency(text_lower)
        
        # Accomplishments and problems
        accomplishments = self._extract_accomplishments(text)
        problems = self._extract_problems(text)
        action_items = self._extract_action_items(text)
        
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
            "action_items": action_items[:3],
            "analysis_complete": True
        }
    
    def _extract_topics(self, text_lower):
        """Extract key topics from text"""
        topics = []
        project_words = {'bug', 'feature', 'deploy', 'test', 'meeting', 'report',
                        'database', 'api', 'system', 'user', 'client', 'team',
                        'project', 'code', 'software', 'hardware', 'network',
                        'security', 'performance', 'update', 'version', 'release'}
        
        for topic in project_words:
            if topic in text_lower:
                topics.append(topic)
        
        # If no topics found, use most frequent words
        if not topics:
            words = [w for w in text_lower.split() if len(w) > 3 and w.isalpha()]
            word_counts = Counter(words)
            topics = [word for word, count in word_counts.most_common(5)]
        
        return topics
    
    def _generate_summary(self, text):
        """Generate a simple summary"""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Find the most informative line
        for line in lines:
            if len(line) > 30 and not line.startswith(('=', '-', '#', '*')):
                return line[:150] + "..." if len(line) > 150 else line
        
        # Fallback
        return text[:100] + "..." if len(text) > 100 else text
    
    def _detect_urgency(self, text_lower):
        """Detect urgency level"""
        urgent_words = {'urgent', 'immediate', 'asap', 'critical', 'emergency', 
                       'important', 'blocked', 'failed', 'broken', 'down'}
        
        if any(word in text_lower for word in urgent_words):
            return "high"
        
        # Check for negative words but not urgent
        negative_words_in_text = sum(1 for w in text_lower.split() if w in self.negative_words)
        return "medium" if negative_words_in_text > 0 else "low"
    
    def _extract_accomplishments(self, text):
        """Extract accomplishments"""
        lines = text.split('\n')
        accomplishments = []
        
        accomplishment_keywords = {'completed', 'finished', 'achieved', 'fixed',
                                  'resolved', 'deployed', 'implemented', 'launched',
                                  'success', 'good', 'great', 'excellent'}
        
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in accomplishment_keywords):
                if len(line.strip()) > 10:
                    accomplishments.append(line.strip())
        
        return accomplishments
    
    def _extract_problems(self, text):
        """Extract problems"""
        lines = text.split('\n')
        problems = []
        
        problem_keywords = {'issue', 'problem', 'error', 'bug', 'failed',
                           'blocked', 'delayed', 'stuck', 'broken', 'challenge',
                           'difficult', 'slow', 'risk', 'concern'}
        
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in problem_keywords):
                if len(line.strip()) > 10:
                    problems.append(line.strip())
        
        return problems
    
    def _extract_action_items(self, text):
        """Extract action items"""
        lines = text.split('\n')
        actions = []
        
        action_patterns = [r'need to', r'must', r'should', r'will', r'plan to',
                          r'next steps', r'action required', r'task']
        
        for line in lines:
            line_lower = line.lower()
            if any(pattern in line_lower for pattern in action_patterns):
                if len(line.strip()) > 10:
                    actions.append(line.strip())
        
        return actions

    async def generate_gemini_conclusion(self, text, basic_analysis):
        """Generate AI-powered conclusion using Gemini"""
        if not GEMINI_AVAILABLE or not gemini_model:
            return self._generate_fallback_conclusion(basic_analysis)
        
        try:
            prompt = f"""
            Analyze this daily work report and provide a professional conclusion in 3-4 bullet points:
            
            REPORT CONTENT:
            {text[:1500]}
            
            BASIC ANALYSIS:
            - Sentiment: {basic_analysis['sentiment']['label']} (score: {basic_analysis['sentiment']['score']})
            - Urgency: {basic_analysis['urgency']}
            - Key Topics: {', '.join(basic_analysis['topics'])}
            
            Please provide a concise conclusion with:
            1. Overall assessment
            2. Key achievements  
            3. Main concerns
            4. Suggested next steps
            
            Format: Clear bullet points only. Keep it under 200 words.
            """
            
            response = gemini_model.generate_content(prompt)
            
            if response and response.text:
                return {
                    "ai_conclusion": response.text,
                    "generated_by": "gemini_ai",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return self._generate_fallback_conclusion(basic_analysis)
                
        except Exception as e:
            print(f"Gemini API error: {e}")
            return self._generate_fallback_conclusion(basic_analysis)
    
    def _generate_fallback_conclusion(self, analysis):
        """Generate a conclusion when Gemini is not available"""
        sentiment = analysis['sentiment']['label']
        urgency = analysis['urgency']
        
        if sentiment == "positive" and urgency == "low":
            conclusion = """✅ **Overall Status: Good Progress**
• Report shows positive developments and completed tasks
• Team is on track with minimal issues
• Continue current momentum and maintain communication"""
        elif sentiment == "negative" or urgency == "high":
            conclusion = """⚠️ **Overall Status: Attention Needed**
• Several issues require immediate attention
• Negative sentiment indicates significant challenges
• Prioritize problem resolution and escalate if needed"""
        else:
            conclusion = """ℹ️ **Overall Status: Stable Operations**
• Standard operational report with mixed results
• Some minor issues noted but overall stable
• Monitor ongoing tasks and follow up on action items"""
        
        return {
            "ai_conclusion": conclusion,
            "generated_by": "fallback_ai",
            "timestamp": datetime.now().isoformat()
        }

# Create AI instance
ai = EnhancedAI()

# Database setup
def setup_db():
    conn = sqlite3.connect('reports.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reports'")
    table_exists = cursor.fetchone() is not None
    
    if not table_exists:
        # Create table with all columns
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
                file_type TEXT,
                ai_analysis TEXT,
                ai_conclusion TEXT
            )
        ''')
        print("✅ Created new database with AI conclusion support")
    else:
        # Table exists, check for ai_conclusion column
        cursor.execute("PRAGMA table_info(reports)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'ai_conclusion' not in column_names:
            print("⚠️ Adding missing 'ai_conclusion' column to existing database...")
            try:
                cursor.execute('ALTER TABLE reports ADD COLUMN ai_conclusion TEXT')
                print("✅ Added 'ai_conclusion' column")
            except Exception as e:
                print(f"⚠️ Could not add column: {e}")
    
    conn.commit()
    conn.close()
    print(f"✅ Database ready | Gemini: {'✅ Available' if GEMINI_AVAILABLE else '❌ Not configured'}")

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
        for sheet_name in excel_file.sheet_names[:2]:
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
            text_parts.append(f"Sheet: {sheet_name} ({len(df)} rows)")
            for i, row in df.head(3).iterrows():
                text_parts.append(str(row.to_dict()))
        return "\n".join(text_parts)
    except Exception as e:
        return f"Excel content (error: {str(e)})"

def process_csv(content):
    try:
        content_str = content.decode('utf-8', errors='ignore')
        lines = content_str.split('\n')
        return "\n".join(lines[:10])
    except:
        return "CSV content"

@app.get("/")
def home():
    return {
        "message": "✅ Report Analyzer with Enhanced AI", 
        "ai": "active",
        "gemini_available": GEMINI_AVAILABLE,
        "endpoints": ["/api/upload", "/api/reports", "/api/stats", "/api/health", "/api/gemini-conclusion"]
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
        
        # Get text content
        if file_type == 'excel':
            content = process_excel(content_bytes)
        elif file_type == 'csv':
            content = process_csv(content_bytes)
        else:
            content = content_bytes.decode('utf-8', errors='ignore')
        
        print(f"📝 Content length: {len(content)} chars")
        
        # Run basic AI analysis
        print("🤖 Running AI analysis...")
        ai_result = ai.analyze(content)
        
        # Generate AI conclusion
        print("🧠 Generating AI conclusion...")
        ai_conclusion = await ai.generate_gemini_conclusion(content, ai_result)
        
        # Add conclusion to result
        ai_result["ai_conclusion"] = ai_conclusion
        
        print(f"✅ AI analysis complete: {ai_result['sentiment']['label']}")
        
        # Save to database
        conn = sqlite3.connect('reports.db', check_same_thread=False)
        cursor = conn.cursor()
        
        ai_conclusion_json = json.dumps(ai_conclusion) if ai_conclusion else None
        ai_analysis_json = json.dumps(ai_result)
        
        cursor.execute('''
            INSERT INTO reports 
            (department, report_date, filename, content, summary, word_count, 
             upload_date, file_type, ai_analysis, ai_conclusion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            department, 
            date, 
            file.filename, 
            content,
            ai_result["summary"], 
            ai_result["word_count"],
            datetime.now().isoformat(), 
            file_type,
            ai_analysis_json,
            ai_conclusion_json
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
            "ai_analysis": ai_result,
            "ai_conclusion": ai_conclusion,
            "gemini_used": ai_conclusion["generated_by"] == "gemini_ai"
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
            
            if report.get('ai_conclusion'):
                try:
                    report['ai_conclusion'] = json.loads(report['ai_conclusion'])
                except:
                    report['ai_conclusion'] = None
            
            reports.append(report)
        
        conn.close()
        return {"reports": reports, "count": len(reports), "gemini_available": GEMINI_AVAILABLE}
        
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
        
        # Get sentiment distribution
        cursor.execute('SELECT ai_analysis FROM reports WHERE ai_analysis IS NOT NULL')
        sentiments = {'positive': 0, 'negative': 0, 'neutral': 0}
        gemini_used = 0
        
        for row in cursor.fetchall():
            try:
                analysis = json.loads(row[0])
                sentiment = analysis.get('sentiment', {}).get('label', 'neutral')
                if sentiment in sentiments:
                    sentiments[sentiment] += 1
            except:
                pass
        
        # Count Gemini usage
        cursor.execute('SELECT ai_conclusion FROM reports WHERE ai_conclusion IS NOT NULL')
        for row in cursor.fetchall():
            try:
                conclusion = json.loads(row[0])
                if conclusion.get('generated_by') == 'gemini_ai':
                    gemini_used += 1
            except:
                pass
        
        conn.close()
        
        return {
            "total_reports": total,
            "total_departments": departments,
            "today_reports": today,
            "sentiment_distribution": sentiments,
            "ai_enabled": True,
            "gemini_available": GEMINI_AVAILABLE,
            "gemini_reports": gemini_used,
            "fallback_reports": total - gemini_used,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/gemini-conclusion")
async def generate_gemini_conclusion_endpoint(text: str = Form(...)):
    """Generate AI conclusion for any text"""
    try:
        if not GEMINI_AVAILABLE:
            return {"success": False, "error": "Gemini AI not configured"}
        
        # Generate basic analysis first
        basic_analysis = ai.analyze(text)
        
        # Generate Gemini conclusion
        conclusion = await ai.generate_gemini_conclusion(text, basic_analysis)
        
        return {
            "success": True,
            "conclusion": conclusion,
            "basic_analysis": basic_analysis,
            "gemini_used": conclusion["generated_by"] == "gemini_ai"
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

# Keep your existing template endpoints
@app.post("/api/analyze-template")
async def analyze_template(
    department: str = Form(...),
    file: UploadFile = File(...)
):
    try:
        content_bytes = await file.read()
        content = content_bytes.decode('utf-8', errors='ignore')
        
        template = template_manager.analyze_report_structure(content, department)
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
    return {
        "success": True,
        "templates": template_manager.get_all_templates(),
        "count": len(template_manager.templates)
    }

@app.post("/api/set-template-sections")
async def set_template_sections(
    department: str = Form(...),
    required_sections: str = Form(...)
):
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
        "ai": "active",
        "gemini_available": GEMINI_AVAILABLE
    }

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("🚀 REPORT ANALYZER WITH ENHANCED AI")
    print("=" * 60)
    print(f"🤖 Gemini AI: {'✅ Available' if GEMINI_AVAILABLE else '❌ Not configured'}")
    print("📡 API: http://localhost:8000")
    print("📚 Docs: http://localhost:8000/docs")
    print("=" * 60)
    if not GEMINI_AVAILABLE:
        print("To enable Gemini AI:")
        print("1. Get free API key: https://makersuite.google.com/app/apikey")
        print("2. Create .env file with: GEMINI_API_KEY=AIzaSyDSKpnuiEQpmgK2XcghNr89Pv1UUM6WCiI")
        print("3. Restart the server")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)