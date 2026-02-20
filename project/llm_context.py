import re
from typing import Dict, List
class LLMContextBuilder:
    def __init__(self, crawl_data=Dict, score_data=dict):
        self.crawl=crawl_data
        self.product = crawl_data.get("product", {})
        self.score=score_data.get("ai_visibility_score", score_data)
        self.page = crawl_data.get("page_info", {})
        self.content=crawl_data.get("content",{})
        self.trust = crawl_data.get("trust_signals", {})
    #======================================================================
    #It finds which scoring signals got 0 points and groups them by section
    #======================================================================
    def identify_weak_areas(self)->dict[str,list[str]]:
        weak={}
        breakdown = self.score.get("breakdowns", {})
        for section, values in breakdown.items():
            missing = [k for k, v in values.items() if v == 0]
            if missing:
                weak[section] = missing
        return weak
    #=======================================================================
    # Identify Priority Order 
    #=======================================================================
    def get_priority(self)->List[str]:
        sections = {
            "schema": self.score.get("schema_score", 0),
            "entity": self.score.get("entity_score", 0),
            "content": self.score.get("content_score", 0),
            "trust": self.score.get("trust_score", 0),
            "extractability": self.score.get("extractability_score", 0),
        }
        return sorted(sections,key=sections.get)
    #==========================================================================
    #extract short content
    #==========================================================================
    def get_excerpt(self, limit:int=1200)->str:
        sections=[]
        #clean text
        clean_text = self.crawl.get("clean_text", "")
        clean_text = re.sub(r"\s+", " ", clean_text).strip()
        if clean_text:
            sections.append(clean_text[:600])
        features=self.content.get("features",[])
        #getting features
        if features:
            feature_block="Key features: "+".".join(features[:6])
            sections.append(feature_block)
        #getting specification: Top 5
        specs = self.content.get("specifications", {})
        if specs:
            spec_items = list(specs.items())[:5]
            spec_block = "Specifications: " + ". ".join(
                [f"{k}: {v}" for k, v in spec_items]
                )
            sections.append(spec_block)
        #combine all sections
        combined=" ".join(sections)
        #safe trimming
        if len(combined) > limit:
            truncated = combined[:limit]
            last_period = truncated.rfind(".")
            if last_period != -1:
                combined = truncated[: last_period + 1]
            else:
                combined = truncated
        return combined
    #==================================================================
    # For Building LLM Context
    #==================================================================
    def build_context(self) -> dict:

        context = {
            "page_identity": {
                "url": self.page.get("url"),
                "title": self.page.get("title"),
                "meta_description": self.page.get("meta_description"),
            },

            "product_summary": {
                "name": self.product.get("name"),
                "brand": self.product.get("brand"),
                "price": self.product.get("price"),
                "currency": self.product.get("currency"),
                "availability": self.product.get("availability"),
                "rating": self.product.get("rating"),
                "review_count": self.product.get("review_count"),
            },

            "content_metrics": {
                "word_count": self.content.get("word_count"),
                "heading_count": len(self.content.get("headings", [])),
                "feature_count": len(self.content.get("features", [])),
                "specification_count": len(self.content.get("specifications", {})),
            },

            "ai_visibility_summary": {
                "final_score": self.score.get("final_score"),
                "max_possible": self.score.get("max_possible"),
                "ai_readiness_pct": self.score.get("ai_readiness_pct"),
                "readiness_band": self.score.get("readiness_band"),
            },

            "section_scores": {
                "schema": self.score.get("schema_score"),
                "entity": self.score.get("entity_score"),
                "content": self.score.get("content_score"),
                "trust": self.score.get("trust_score"),
                "extractability": self.score.get("extractability_score"),
            },

            "priority_order": self.get_priority(),

            "weak_areas": self.identify_weak_areas(),

            "penalties": self.score.get("penalties", {}),

            "content_excerpt": self.get_excerpt()
        }

        return context