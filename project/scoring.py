import re
from typing import Any

class AIScoringEngine:
    
    def __init__(self, crawl_data: dict):
        self.data     = crawl_data
        self.product  = crawl_data.get("product", {})
        self.content  = crawl_data.get("content", {})
        self.trust    = crawl_data.get("trust_signals", {})
        self.schema   = crawl_data.get("schema_data", [])
        self.meta     = crawl_data.get("meta", {})

    # ------------------------------------------------------------------ 
    #  Section 1 — Schema Completeness                     
    # ------------------------------------------------------------------ 
    def score_schema(self) -> dict:
        score = 0
        breakdown = {}

        # Core identity fields
        breakdown["name"]         = 4 if self.product.get("name") else 0
        breakdown["price"]        = 4 if self.product.get("price") else 0
        breakdown["currency"]     = 2 if self.product.get("currency") else 0
        breakdown["brand"]        = 2 if self.product.get("brand") else 0
        breakdown["availability"] = 2 if self.product.get("availability") else 0

       
        price = str(self.product.get("price", ""))
        if re.match(r"^\d+(\.\d{1,2})?$", price):
            breakdown["price_format_bonus"] = 2
        else:
            breakdown["price_format_bonus"] = 0

        
        if self.schema:
            schema_types = [s.get("@type", "") for s in self.schema if isinstance(s, dict)]
            breakdown["schema_markup"]  = 2 if schema_types else 0
            breakdown["product_schema"] = 2 if "Product" in schema_types else 0
        else:
            breakdown["schema_markup"]  = 0
            breakdown["product_schema"] = 0

        score = sum(breakdown.values())
        return {"score": min(score, 20), "max": 20, "breakdown": breakdown}

    # ------------------------------------------------------------------ 
    #  Section 2 — Entity Clarity                         
    # ------------------------------------------------------------------ 
    def score_entity_clarity(self) -> dict:
        score = 0
        breakdown = {}

        breakdown["name"]     = 4 if self.product.get("name") else 0
        breakdown["brand"]    = 3 if self.product.get("brand") else 0
        breakdown["sku"]      = 2 if self.product.get("sku") else 0
        breakdown["category"] = 2 if self.product.get("category") else 0
        breakdown["gtin"]     = 2 if self.product.get("gtin") else 0  

        
        name = self.product.get("name", "")
        if name:
            word_count = len(name.split())
            if word_count >= 4:
                breakdown["name_quality"] = 2   
            elif word_count >= 2:
                breakdown["name_quality"] = 1
            else:
                breakdown["name_quality"] = 0   
        score = sum(breakdown.values())
        return {"score": min(score, 15), "max": 15, "breakdown": breakdown}

    # ------------------------------------------------------------------ 
    #  Section 3 — Content Depth                          
    # ------------------------------------------------------------------ 
    def score_content_depth(self) -> dict:
        score = 0
        breakdown = {}

        word_count = self.content.get("word_count", 0)

 
        if word_count > 1500:   breakdown["word_count"] = 8
        elif word_count > 800:  breakdown["word_count"] = 6
        elif word_count > 400:  breakdown["word_count"] = 4
        elif word_count > 150:  breakdown["word_count"] = 2
        else:                   breakdown["word_count"] = 0

    
        headings = self.content.get("headings", [])
        if len(headings) >= 8:   breakdown["headings"] = 4
        elif len(headings) >= 4: breakdown["headings"] = 2
        elif len(headings) >= 1: breakdown["headings"] = 1
        else:                    breakdown["headings"] = 0

    
        features = self.content.get("features", [])
        if len(features) >= 6:   breakdown["features"] = 4
        elif len(features) >= 3: breakdown["features"] = 2
        elif len(features) >= 1: breakdown["features"] = 1
        else:                    breakdown["features"] = 0

        
        specs = self.content.get("specifications", {})
        if len(specs) >= 8:   breakdown["specifications"] = 5
        elif len(specs) >= 4: breakdown["specifications"] = 3
        elif len(specs) >= 1: breakdown["specifications"] = 1
        else:                 breakdown["specifications"] = 0

     
        images = self.content.get("images", [])
        images_with_alt = [i for i in images if isinstance(i, dict) and i.get("alt")]
        if images_with_alt:
            breakdown["image_alt_text"] = 2
        else:
            breakdown["image_alt_text"] = 0

    
        breakdown["faq"] = 2 if self.content.get("faq") else 0

        score = sum(breakdown.values())
        return {"score": min(score, 25), "max": 25, "breakdown": breakdown}

    # ------------------------------------------------------------------ 
    #  Section 4 — Trust Signals                          
    # ------------------------------------------------------------------ 
    def score_trust(self) -> dict:
        score = 0
        breakdown = {}

        weighted_signals = {
    "has_return_policy": 3,
    "has_warranty_info": 3,
    "has_shipping_info": 2,
    "mentions_secure_payment": 2,
    "has_contact_page": 2,
    "mentions_reviews": 3,
    "uses_https": 1
}

        for signal, weight in weighted_signals.items():
            value = self.trust.get(signal)
            if value:
                
                if signal == "reviews_count":
                    count = int(value) if str(value).isdigit() else 0
                    if count >= 100:   breakdown[signal] = weight
                    elif count >= 20:  breakdown[signal] = weight - 1
                    elif count >= 5:   breakdown[signal] = weight - 2
                    else:              breakdown[signal] = 1
                else:
                    breakdown[signal] = weight
            else:
                breakdown[signal] = 0

        score = sum(breakdown.values())
        return {"score": min(score, 20), "max": 20, "breakdown": breakdown}

    # ------------------------------------------------------------------ 
    #  Section 5 — AI Extractability                       
    # ------------------------------------------------------------------ 
    def score_extractability(self) -> dict:
        score = 0
        breakdown = {}

        breakdown["schema_present"]  = 4 if self.schema else 0


        headings = self.content.get("headings", [])
        h_types   = [h.get("level") for h in headings if isinstance(h, dict)]
        breakdown["heading_hierarchy"] = 2 if ("h1" in h_types and "h2" in h_types) else (1 if headings else 0)


        specs = self.content.get("specifications", {})
        if len(specs) >= 5:   breakdown["specs_table"] = 4
        elif len(specs) >= 1: breakdown["specs_table"] = 2
        else:                 breakdown["specs_table"] = 0


        breakdown["meta_title"]       = 2 if self.meta.get("title") else 0
        breakdown["meta_description"] = 2 if self.meta.get("description") else 0


        breakdown["canonical_url"] = 2 if self.meta.get("canonical") else 0


        breakdown["hreflang"] = 4 if self.meta.get("hreflang") else 0

        score = sum(breakdown.values())
        return {"score": min(score, 20), "max": 20, "breakdown": breakdown}

    # ------------------------------------------------------------------ 
    #  PENALTIES          
    # ------------------------------------------------------------------ 
    def _compute_penalties(self) -> dict:
        penalties = {}

        if not self.product.get("price"):
            penalties["missing_price"] = -5

        if not self.product.get("name"):
            penalties["missing_product_name"] = -10

        if not self.schema:
            penalties["no_schema_markup"] = -5

        word_count = self.content.get("word_count", 0)
        if word_count < 100:
            penalties["thin_content"] = -8

        return penalties

    # ------------------------------------------------------------------
    #  GEO READINESS BAND                                                 
    # ------------------------------------------------------------------ 
    @staticmethod
    def _readiness_band(pct: float) -> str:
        if pct >= 85: return "Excellent — AI/GEO Ready"
        if pct >= 70: return "Good — Minor Gaps"
        if pct >= 50: return "Fair — Needs Improvement"
        if pct >= 30: return "Poor — Significant Issues"
        return        "Critical — Not AI-Ready"

    # ------------------------------------------------------------------ 
    #  MASTER COMPUTE                                                      
    # ------------------------------------------------------------------ 
    def compute_score(self) -> dict:
        schema      = self.score_schema()
        entity      = self.score_entity_clarity()
        content     = self.score_content_depth()
        trust       = self.score_trust()
        extract     = self.score_extractability()
        penalties   = self._compute_penalties()

        raw_total  = (schema["score"] + entity["score"] + content["score"]
                      + trust["score"] + extract["score"])
        penalty_total = sum(penalties.values())
        max_score     = schema["max"] + entity["max"] + content["max"] + trust["max"] + extract["max"]

        final_score  = max(0, raw_total + penalty_total)
        percentage   = round((final_score / max_score) * 100, 2)

        return {
            
            "schema_score":          schema["score"],
            "entity_score":          entity["score"],
            "content_score":         content["score"],
            "trust_score":           trust["score"],
            "extractability_score":  extract["score"],
            
            "penalties":             penalties,
            "penalty_total":         penalty_total,
            
            "raw_score":             raw_total,
            "final_score":           final_score,
            "max_possible":          max_score,
            "ai_readiness_pct":      percentage,
            
            
            "readiness_band":        self._readiness_band(percentage),
            
            "breakdowns": {
                "schema":         schema["breakdown"],
                "entity":         entity["breakdown"],
                "content":        content["breakdown"],
                "trust":          trust["breakdown"],
                "extractability": extract["breakdown"],
            }
        }