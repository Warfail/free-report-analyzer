import uvicorn

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 FREE DAILY REPORT ANALYZER - BACKEND")
    print("=" * 60)
    print("📡 API Server: http://localhost:8000")
    print("📚 Swagger Docs: http://localhost:8000/docs")
    print("📊 ReDoc Docs: http://localhost:8000/redoc")
    print("🖥️  Frontend: Open frontend/index.html in browser")
    print("\n⚡ Available Endpoints:")
    print("  • GET  /              - Welcome message")
    print("  • POST /api/upload    - Upload report (text/PDF/DOCX)")
    print("  • GET  /api/reports   - List all reports")
    print("  • GET  /api/stats     - System statistics")
    print("  • GET  /api/health    - Health check")
    print("\n📝 Usage:")
    print("  1. Keep this terminal running")
    print("  2. Open frontend/index.html in browser")
    print("  3. Upload daily reports")
    print("\n" + "=" * 60)
    print("Press Ctrl+C to stop the server")
    print("=" * 60 + "\n")
    
    uvicorn.run(
        "simple_app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )