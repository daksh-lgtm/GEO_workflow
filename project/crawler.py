from datetime import datetime
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
        meta_desc=""
        #storing meta tags
        #it is getting metadata link
        meta_tag=self.soup.find("meta",attrs={"name":"description"})
        if meta_tag:
            meta_desc=meta_tag.get("content"," ")
            #fteching canonical urls
        canonical=""
        canonical_tag=self.soup.find("link",rel="canonical")
        if canonical_tag:
            canonical=canonical_tag.get("href", "")
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
            price_pattern = r"(₹|\$|€|£)\s?\d{1,3}(?:,\d{3})*(?:\.\d+)?"
            #match 
            match = re.search(price_pattern, text)
            if match:
                return match.group()
            return None
        
    #extracting heading
    def extract_headings(self):
            #initializing heading
            headings=[]
            #till leve 7
            for level in range(1,7):
                tag = f"h{level}"
                for h in self.soup.find_all(tag):
                    headings.append({
                        "level":tag,
                        "text":h.get_text(strip=True)
                    })
            return headings
        
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
                
    def extract_specifications(self):
            specs = {}
            for table in self.soup.find_all("table"):
                #skip tables in nav, footer
                if table.find_parent(["nav", "footer"]):
                    continue
                rows = table.find_all("tr")
                #skip small tables
                if len(rows) < 2:
                    continue
                for row in rows:
                    cols = row.find_all(["td", "th"])
                    if len(cols) == 2:
                        key = cols[0].get_text(strip=True)
                        value = cols[1].get_text(strip=True)
                        if len(key) < 2 or len(value) < 2:
                            continue
                        if len(key) > 100 or len(value) > 300:
                            continue
                        if key in specs:
                            if isinstance(specs[key], list):
                                specs[key].append(value)
                            else:
                                specs[key] = [specs[key], value]
                        else:
                            specs[key] = value
            return specs
                        
    def extract_links(self):
            internal=[]
            external=[]
            base_domain=urlparse(self.url).netloc
            seen_internal=set()
            seen_external=set()
            for a in self.soup.find_all("a",href=True):
                href=a["href"].strip()
                #now to skip junks
                if href.startswith("#"):
                    continue
                if href.startswith("javascript"):
                    continue
                if href.startswith("mailto:"):
                    continue
                if href.startswith("tel:"):
                    continue
                #getting absolute url
                link=urljoin(self.url,href)
                #breaking that url
                parsed=urlparse(link)
                if not parsed.scheme.startswith("http"):
                    continue
                domain=parsed.netloc
                anchor_text=a.get_text(strip=True)
                link_data = {
                    "url": link,
                    "anchor_text": anchor_text
                    }
                if domain == base_domain or domain.endswith("." + base_domain):
                    if link not in seen_internal:
                        internal.append(link_data)
                        seen_internal.add(link)
                else:
                    if link not in seen_external:
                        external.append(link_data)
                        seen_external.add(link)
                
            return internal,external
    
    def detect_trust_signal(self):
        text=self.soup.get_text(" ",strip=True).lower()
        links=[a.get_text(strip=True).lower() for a in self.soup.find_all("a")]
        def contains_keywords(source,keywords):
            return any(keyword in source for keyword in keywords)
        
        trust = {
            "has_return_policy": contains_keywords(text, ["return policy", "returns"]),
        "has_refund_policy": contains_keywords(text, ["refund policy", "refunds"]),
        "has_warranty_info": contains_keywords(text, ["warranty"]),
        "has_shipping_info": contains_keywords(text, ["shipping", "delivery"]),
        "has_cancellation_policy": contains_keywords(text, ["cancellation"]),

        # Security signals
        "uses_https": self.url.startswith("https"),
        "mentions_secure_payment": contains_keywords(text, ["secure payment", "100% secure", "ssl"]),
        "has_cod_option": contains_keywords(text, ["cash on delivery", "cod"]),

        # Business identity
        "has_contact_page": any("contact" in link for link in links),
        "has_about_page": any("about" in link for link in links),
        "mentions_phone": bool(re.search(r"\+?\d[\d\s-]{8,}", text)),
        "mentions_email": bool(re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)),

        # Social proof
        "mentions_reviews": contains_keywords(text, ["review", "ratings"]),
        "mentions_testimonials": contains_keywords(text, ["testimonial"]),

        # Brand legitimacy
        "official_store_claim": contains_keywords(text, ["official store", "authorized seller"])
    }
        return trust
    
    def extract_clean_text(self):
         # Raw cleaned version
        soup = BeautifulSoup(self.html, "lxml")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        raw_text = soup.get_text(separator=" ", strip=True)
            # Readability version
        doc = Document(self.html)
        readable_html = doc.summary()
        readable_soup = BeautifulSoup(readable_html, "lxml")
        readable_text = readable_soup.get_text(separator=" ", strip=True)
            
            # Choose longer one (more content preserved)
        if len(readable_text) > len(raw_text) * 0.6:
                final_text = readable_text
        else:
                final_text = raw_text
        final_text = " ".join(final_text.split())
        return final_text, len(final_text.split())
            
    def build(self):
        load_time=self.fetch()
        if self.response.status_code!=200:
            return{
                "error": f"Failed to fetch page. Status code: {self.response.status_code}",
            "url": self.url
            }
            
        title,meta_desc,canonical=self.extract_metadata()
        schema_data=self.extract_schema()
        product_data=self.parse_product_schema(schema_data)
        
        headings=self.extract_headings()
        feature_data=self.extract_features()
        specs_data=self.extract_specifications()
        internal_links, external_links = self.extract_links()
        trust=self.detect_trust_signal()
        clean_text, word_count = self.extract_clean_text()
        #price fallback
        if not product_data.get("price"):
            fallback_price=self.extract_price_fallback(clean_text)
            product_data["price"]=fallback_price
        # Basic page classification
        page_type = "PRODUCT" if product_data.get("name") else "UNKNOWN"
        return {
            "page_info": {
                "url": self.url,
                "final_url": self.response.url,
                "status_code": self.response.status_code,
                "canonical_url": canonical,
                "title": title,
                "meta_description": meta_desc,
                "https": self.url.startswith("https"),
                "load_time_ms": load_time,
                "page_type": page_type,
                "crawl_timestamp": datetime.utcnow().isoformat()
        },
        "product": product_data,
        "content": {
            "headings": headings,
            "features": feature_data,
            "specifications": specs_data,
            "word_count": word_count
        },
        "schema_data": schema_data,
        "links": {
            "internal": internal_links,
            "external": external_links
        },
        "trust_signals": trust,
        "clean_text": clean_text  
    }