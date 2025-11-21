from semantic_retriever import SemanticRetriever
from typing import List, Dict, Optional
from datetime import datetime

class ContextBuilder:
    def __init__(self, retriever: Optional[SemanticRetriever] = None):
        self.retriever = retriever if retriever else SemanticRetriever()
    
    def build_date_context(self, start_date: str, end_date: Optional[str] = None, 
                          max_tokens: int = 8000) -> str:
        """Build context from date range."""
        summaries = self.retriever.retrieve_by_date(start_date, end_date)
        return self._format_context(summaries, max_tokens)
    
    def build_semantic_context(self, query: str, top_k: int = 5, 
                              max_tokens: int = 8000) -> str:
        """Build context from semantic search."""
        summaries = self.retriever.retrieve_by_query(query, top_k)
        return self._format_context(summaries, max_tokens)
    
    def build_recent_context(self, n_days: int = 7, max_tokens: int = 8000) -> str:
        """Build context from last N days."""
        summaries = self.retriever.retrieve_last_n_days(n_days)
        return self._format_context(summaries, max_tokens)
    
    def _format_context(self, summaries: List[Dict], max_tokens: int) -> str:
        """Format summaries into LLM-ready context."""
        if not summaries:
            return "No data found for the specified criteria."
        
        dates = [s['date'] for s in summaries]
        date_range = f"{min(dates)} to {max(dates)}" if len(dates) > 1 else dates[0]
        
        context_parts = [
            f"Financial Market Data Summary",
            f"Period: {date_range}",
            f"Number of days: {len(summaries)}",
            "\n---\n"
        ]
        
        total_chars = sum(len(part) for part in context_parts)
        
        for summary in summaries:
            entry = f"\n[{summary['date']}]\n{summary['text']}\n"
            
            # Rough token estimation: 1 token ≈ 4 chars
            estimated_tokens = (total_chars + len(entry)) / 4
            
            if estimated_tokens > max_tokens:
                context_parts.append(f"\n... (truncated at {max_tokens} tokens)")
                break
            
            context_parts.append(entry)
            total_chars += len(entry)
        
        return ''.join(context_parts)
    
    def build_with_metadata(self, summaries: List[Dict]) -> Dict:
        """Return structured context with metadata."""
        if not summaries:
            return {
                'context': "No data found.",
                'metadata': {'count': 0}
            }
        
        dates = [s['date'] for s in summaries]
        
        return {
            'context': self._format_context(summaries, max_tokens=8000),
            'metadata': {
                'count': len(summaries),
                'start_date': min(dates),
                'end_date': max(dates),
                'dates': dates
            }
        }

if __name__ == '__main__':
    builder = ContextBuilder()
    
    # Example: Date-based context
    context = builder.build_date_context('2025-11-01', '2025-11-05')
    print(context[:500])
    
    # Example: Semantic context
    context = builder.build_semantic_context('inflation surprises', top_k=3)
    print("\n" + "="*50)
    print(context[:500])
    
    # Example: Recent context
    context = builder.build_recent_context(n_days=7)
    print("\n" + "="*50)
    print(context[:500])