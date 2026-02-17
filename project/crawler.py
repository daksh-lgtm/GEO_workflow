import requests
import re
from bs4 import BeautifulSoup
import extruct
import time
from urllib.parse import urljoin, urlparse
from readability import Document

class ProductCrawler:
    def __init__(self,url:str):
        #initializing the url, response, html and its content
        self.url=url
        self.response=None
        self.html=None
        self.soup=None
        
    def fetch(self):
        start=time.time()
        #telling which all browser it can work on
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
        self.response=requests.get(self.url,headers=headers,timeout=15)
        load_time=int((time.time()-start)*1000)
        #store html in self.html
        self.html=self.response.text
        #Parse the HTML content using the lxml parser and store the parsed object in self.soup
        self.soup=BeautifulSoup(self.html,"lxml")
        return load_time
    
    def extract_metadata(self):
        title = self.soup.title.string.strip() if self.soup.title else ""
        #initialising the metadata
         #it is getting metadata
        meta_data=""
        #storing meta tags
        #it is getting metadata link
        meta_tag=self.soup.find("meta",attrs={"name":"Description"})
        if meta_tag:
            meta_desc=meta_tag.get("content"," ")
            #fteching canonical urls
        canonical=" "
        canonical_tag=self.soup.find("link",rel="canonical")
        if canonical_tag:
            canonical_tag=canonical_tag.get("href", "")
            return title,meta_desc,canonical
        
        def extract_schema(self):
            data=extruct.extract(self.html, base_url=self.url)
            return data.get("json-ld",[])
        
        def parse_product_schema(self,schema_data):
            product_data = {
            "name": "",
            "brand": "",
            "sku": "",
            "price": None,
            "currency": "",
            "availability": "",
            "rating": None,
            "review_count": None
            }
            for item in schema_data:
                if isinstance(item, dict) and item.get("@type") == "Product":
                    product_data["name"] = item.get("name", "")
                    # brand extraction
                    brand = item.get("brand")
                    if isinstance(brand, dict):
                        product_data["brand"] = brand.get("name", "")
                    elif isinstance(brand, str):
                        product_data["brand"] = brand
                        product_data["sku"] = item.get("sku", "")
                        #offer extraction
                        offers = item.get("offers", {})
                        if isinstance(offers, dict):
                            product_data["price"] = offers.get("price")
                            product_data["currency"] = offers.get("priceCurrency", "")
                            product_data["availability"] = offers.get("availability", "")
                        #rating extraction
                        rating = item.get("aggregateRating", {})
                        if isinstance(rating, dict):
                            product_data["rating"] = rating.get("ratingValue")
                            product_data["review_count"] = rating.get("reviewCount")
                            
                        return product_data
        #price extraction startegy
        def extract_price_fallback(self,text):
            #pattern matching
            price_pattern = r"(₹|\$|€)\s?\d+(?:,\d+)*(?:\.\d+)?"
            #match 
            match=re.search(price_pattern,text)
            if match:
                return match.group()
            return None
        #extracting heading
        def extract_headings(self):
            #initializing heading
            heading=[]
            #till leve 7
            for level in range(1,7):
                tag = f"h{level}"
                for h in self.soup.find_all(tag):
                    heading.append({
                        "level":tag,
                        "text":h.get_text(strip=True)
                    })
                    return heading
        
        def extract_features(self):
            features = []
            for ul in self.soup.find_all("ul"):
                # Skip nav or footer sections
                if ul.find_parent(["nav", "footer", "header"]):
                    continue
                items = []
                for li in ul.find_all("li"):
                    text = li.get_text(strip=True)
                     # Filter junk
                    if len(text) > 10 and not text.lower() in ["home", "about", "contact"]:
                        items.append(text)
                    if 2 <= len(items) <= 20:
                        features.extend(items)
                # Remove duplicates while preserving order
                seen = set()
                clean_features = []
                for f in features:
                    if f not in seen:
                        seen.add(f)
                        clean_features.append(f)
                return clean_features[:20]
                
            