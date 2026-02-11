from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json
import os
from datetime import datetime
from typing import List, Dict, Any

# 🔥 ЧИСТЫЙ FASTAPI API (БЕЗ aiogram/bot!)
app = FastAPI(
    title="🚗 АвтоСтоянка API",
    description="API для Telegram Mini App каталога авто СПб",
    version="1.0.0"
)

# CORS для Mini App
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def load_ads_db() -> List[Dict[str, Any]]:
    """🔥 Загрузка объявлений из ads_db.json"""
    ads_db_path = "ads_db.json"
    if os.path.exists(ads_db_path):
        try:
            with open(ads_db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                approved_ads = data.get('approved', [])
                return approved_ads
        except Exception as e:
            print(f"❌ Error loading DB: {e}")
            return []
    return []

@app.get("/")
async def root():
    """🔥 Главная страница API"""
    return {
        "message": "🚗 АвтоСтоянка API LIVE!",
        "status": "healthy",
        "version": "1.0.0"
    }

@app.get("/api/ads")
async def get_ads():
    """🔥 ГЛАВНЫЙ ENDPOINT для Telegram Mini App"""
    approved_ads = load_ads_db()
    
    return {
        "success": True,
        "ads": approved_ads,
        "count": len(approved_ads),
        "live": True,
        "updated": datetime.now().isoformat(),
        "city": "СПб"
    }

@app.get("/api/stats")
async def get_stats():
    """📊 Статистика"""
    approved_ads = load_ads_db()
    return {
        "total_ads": len(approved_ads),
        "bmw_count": len([ad for ad in approved_ads if "BMW" in ad.get("title", "").upper()]),
        "price_min": min([ad.get("price", 0) for ad in approved_ads], default=0),
        "price_max": max([ad.get("price", 0) for ad in approved_ads], default=0)
    }

@app.get("/health")
async def health_check():
    """❤️ Health check для Render"""
    return {
        "status": "healthy",
        "database": os.path.exists("ads_db.json"),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/ads/{ad_id}")
async def get_ad(ad_id: int):
    """🔍 Одно объявление по ID"""
    approved_ads = load_ads_db()
    for ad in approved_ads:
        if ad.get("id") == ad_id:
            return {"success": True, "ad": ad}
    return JSONResponse(
        status_code=404,
        content={"success": False, "error": "Ad not found"}
    )

# 404 для всех остальных путей
@app.get("/{path:path}")
@app.post("/{path:path}")
async def not_found(path: str):
    return JSONResponse(
        status_code=404,
        content={"error": "Endpoint not found"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
