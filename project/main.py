from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from crawler import ProductCrawler
import json
import os
from datetime import datetime
from urllib.parse import urlparse
from scoring import AIScoringEngine
from llm_context import LLMContextBuilder

#app title
app = FastAPI(title="Product Crawler Webpage")

#routing to data to data folder
DATA_FOLDER="data"

#ensure data folder exists
os.makedirs(DATA_FOLDER,exist_ok=True)

class CrawlRequest(BaseModel):
    
    url:str

class ScoreRequest(BaseModel):
    filename: str

    
def generate_filename(url:str):
    
        parsed=urlparse(url)
        
        domain=parsed.netloc.replace(".","-")
        
        path=parsed.path.strip("/").replace("/","-")
        
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        
        filename = f"{domain}-{path}-{timestamp}.json"
        
        return os.path.join(DATA_FOLDER, filename)
#=============================================================
# Crawler page
#=============================================================
@app.post("/crawl_product")
def crawl_product_page(request: CrawlRequest):
    try:
        crawler = ProductCrawler(request.url)
        result = crawler.build()
        
        if "error" in result:                          
            raise HTTPException(status_code=400, detail=result["error"])
        
        file_path = generate_filename(request.url)
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        return {                                        
            "message": "Crawl successful",
            "saved_to": file_path,
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
#=============================================================
# scoring result
#=============================================================
@app.post("/score_product")
def score_product(request: ScoreRequest):

    file_path = os.path.join(DATA_FOLDER, request.filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    with open(file_path, "r", encoding="utf-8") as f:
        crawl_data = json.load(f)

    scorer = AIScoringEngine(crawl_data)
    score_result = scorer.compute_score()

    return {
        "ai_visibility_score": score_result
    }
#=============================================================
# LLM context builder
#=============================================================
@app.post("/geo_context")
def geo_context(request: ScoreRequest):

    file_path = os.path.join(DATA_FOLDER, request.filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    with open(file_path, "r", encoding="utf-8") as f:
        crawl_data = json.load(f)

    scorer = AIScoringEngine(crawl_data)
    score_result = scorer.compute_score()

    context_builder = LLMContextBuilder(crawl_data, score_result)
    llm_context = context_builder.build_context()

    return {
        "llm_context": llm_context
    }