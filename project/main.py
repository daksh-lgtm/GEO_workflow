from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from crawler import ProductCrawler
import json
import os
from datetime import datetime
from urllib.parse import urlparse

#app title
app=FastAPI("Product Crawler webpage")

#routing to data to data folder
DATA_FOLDER="data"

#ensure data folder exists
os.makedirs(DATA_FOLDER,exist_ok=True)

class CrawlRequest(BaseModel):
    
    url:str
    
def generate_filename(url:str):
    
        parsed=urlparse(url)
        
        domain=parsed.netloc.replace(".","-")
        
        path=parsed.path.strip("/").replace("/","-")
        
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        
        filename = f"{domain}-{path}-{timestamp}.json"
        
        return os.path.join(DATA_FOLDER, filename)

@app.post("/crawl_product")
def crawl_product_page(request: CrawlRequest):
    
    try:
        
        crawler=ProductCrawler(request.url)
        result=crawler.build()
        
        #generate file path
        file_path=generate_filename(request.url)
        
        #save to json file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
            
            return {
            "message": "Crawl successful",
            "saved_to": file_path,
            "data": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))