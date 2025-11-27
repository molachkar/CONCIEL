#!/usr/bin/env python3
import json
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

TEXT_SUMMARIES_FOLDER = Path("daily_summaries")
VECTOR_INDEX_FOLDER = Path("vector_index")
FAISS_INDEX_PATH = VECTOR_INDEX_FOLDER / "faiss.index"
METADATA_PATH = VECTOR_INDEX_FOLDER / "metadata.jsonl"
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_MIN_TOKENS = 500
CHUNK_MAX_TOKENS = 800
BATCH_SIZE = 32


@dataclass
class ChunkMetadata:
    chunk_id: str
    date: str
    sources: List[str]
    original_file: str
    text: str
    token_count: int


class PhaseOneIndexer:
    
    def __init__(self, text_folder: Path = TEXT_SUMMARIES_FOLDER, output_folder: Path = VECTOR_INDEX_FOLDER, model_name: str = EMBEDDING_MODEL_NAME):
        self.text_folder = text_folder
        self.output_folder = output_folder
        self.model_name = model_name
        self.output_folder.mkdir(parents=True, exist_ok=True)
        print(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        self.index: Optional[faiss.Index] = None
        self.metadata: List[ChunkMetadata] = []
    
    def approximate_token_count(self, text: str) -> int:
        return len(text.split())
    
    def detect_sources(self, text: str) -> List[str]:
        sources = []
        text_upper = text.upper()
        if any(kw in text_upper for kw in ["GOLD PRICE ACTION", "XAU/USD", "XAUUSD"]):
            sources.append("market")
        if any(kw in text_upper for kw in ["ECONOMIC EVENTS", "CPI", "NFP", "TREASURY", "FED"]):
            sources.append("macro")
        if any(kw in text_upper for kw in ["NEWS HIGHLIGHTS", "[NEWS]", "[MARKET]"]):
            sources.append("news")
        if any(kw in text_upper for kw in ["SOCIAL SENTIMENT", "REDDIT"]):
            sources.append("reddit")
        if any(kw in text_upper for kw in ["TECHNICAL ANALYSIS", "RSI", "MACD", "BIAS"]):
            sources.append("technical")
        if any(kw in text_upper for kw in ["FUNDAMENTALS", "UNEMPLOYMENT", "INFLATION"]):
            sources.append("fundamentals")
        return sources if sources else ["general"]
    
    def extract_date_from_filename(self, filename: str) -> Optional[str]:
        match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
        return match.group(1) if match else None
    
    def split_into_sentences(self, text: str) -> List[str]:
        text = re.sub(r'\s+', ' ', text).strip()
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def create_chunks(self, text: str, date: str, original_file: str, min_tokens: int = CHUNK_MIN_TOKENS, max_tokens: int = CHUNK_MAX_TOKENS) -> List[ChunkMetadata]:
        sentences = self.split_into_sentences(text)
        chunks = []
        current_chunk = []
        current_tokens = 0
        chunk_counter = 0
        
        for sentence in sentences:
            sentence_tokens = self.approximate_token_count(sentence)
            if current_tokens + sentence_tokens > max_tokens and current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunks.append(ChunkMetadata(
                    chunk_id=f"{date}_chunk_{chunk_counter:04d}",
                    date=date,
                    sources=self.detect_sources(chunk_text),
                    original_file=original_file,
                    text=chunk_text,
                    token_count=current_tokens
                ))
                chunk_counter += 1
                current_chunk = []
                current_tokens = 0
            current_chunk.append(sentence)
            current_tokens += sentence_tokens
        
        if current_chunk and current_tokens >= min_tokens:
            chunk_text = ' '.join(current_chunk)
            chunks.append(ChunkMetadata(
                chunk_id=f"{date}_chunk_{chunk_counter:04d}",
                date=date,
                sources=self.detect_sources(chunk_text),
                original_file=original_file,
                text=chunk_text,
                token_count=current_tokens
            ))
        return chunks
    
    def load_and_chunk_files(self) -> List[ChunkMetadata]:
        if not self.text_folder.exists():
            raise FileNotFoundError(f"Text summaries folder not found: {self.text_folder}")
        text_files = sorted(self.text_folder.glob("*.txt"))
        if not text_files:
            raise FileNotFoundError(f"No .txt files found in {self.text_folder}")
        print(f"\nFound {len(text_files)} text summary files")
        print("Chunking text files...")
        all_chunks = []
        for text_file in tqdm(text_files, desc="Processing files"):
            try:
                with open(text_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                date = self.extract_date_from_filename(text_file.name)
                if not date:
                    print(f"Warning: Could not extract date from {text_file.name}, skipping")
                    continue
                chunks = self.create_chunks(text=content, date=date, original_file=text_file.name)
                all_chunks.extend(chunks)
            except Exception as e:
                print(f"Error processing {text_file.name}: {e}")
        print(f"Created {len(all_chunks)} chunks total")
        return all_chunks
    
    def embed_chunks(self, chunks: List[ChunkMetadata]) -> np.ndarray:
        print("\nEmbedding chunks...")
        texts = [chunk.text for chunk in chunks]
        embeddings = self.model.encode(texts, batch_size=BATCH_SIZE, show_progress_bar=True, convert_to_numpy=True, normalize_embeddings=True)
        return embeddings
    
    def build_faiss_index(self, embeddings: np.ndarray) -> faiss.Index:
        print("\nBuilding FAISS index...")
        index = faiss.IndexFlatIP(self.embedding_dim)
        index.add(embeddings.astype('float32'))
        print(f"FAISS index built with {index.ntotal} vectors")
        return index
    
    def save_index_and_metadata(self, index: faiss.Index, metadata: List[ChunkMetadata]) -> None:
        print("\nSaving index and metadata...")
        faiss.write_index(index, str(FAISS_INDEX_PATH))
        print(f"FAISS index saved to {FAISS_INDEX_PATH}")
        with open(METADATA_PATH, 'w', encoding='utf-8') as f:
            for chunk in metadata:
                f.write(json.dumps(asdict(chunk)) + '\n')
        print(f"Metadata saved to {METADATA_PATH}")
    
    def build_index(self) -> None:
        print("="*70)
        print("PHASE ONE INDEXER - BUILDING VECTOR INDEX")
        print("="*70)
        chunks = self.load_and_chunk_files()
        if not chunks:
            print("No chunks created. Exiting.")
            return
        embeddings = self.embed_chunks(chunks)
        self.index = self.build_faiss_index(embeddings)
        self.metadata = chunks
        self.save_index_and_metadata(self.index, self.metadata)
        print("\n" + "="*70)
        print("INDEX BUILD COMPLETE")
        print(f"Total chunks: {len(chunks)}")
        print(f"Embedding dimension: {self.embedding_dim}")
        print(f"Index location: {FAISS_INDEX_PATH}")
        print(f"Metadata location: {METADATA_PATH}")
        print("="*70)


class VectorRetriever:
    
    def __init__(self, index_path: Path = FAISS_INDEX_PATH, metadata_path: Path = METADATA_PATH, model_name: str = EMBEDDING_MODEL_NAME):
        self.index_path = index_path
        self.metadata_path = metadata_path
        if not index_path.exists():
            raise FileNotFoundError(f"FAISS index not found: {index_path}")
        if not metadata_path.exists():
            raise FileNotFoundError(f"Metadata file not found: {metadata_path}")
        print(f"Loading FAISS index from {index_path}")
        self.index = faiss.read_index(str(index_path))
        print(f"Loading metadata from {metadata_path}")
        self.metadata = self._load_metadata()
        print(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        print(f"Retriever ready: {len(self.metadata)} chunks indexed")
    
    def _load_metadata(self) -> List[ChunkMetadata]:
        metadata = []
        with open(self.metadata_path, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line)
                metadata.append(ChunkMetadata(**data))
        return metadata
    
    def _parse_date(self, date_str: str) -> datetime:
        return datetime.strptime(date_str, "%Y-%m-%d")
    
    def _filter_by_date_range(self, target_date: str, days_back: int) -> List[int]:
        target = self._parse_date(target_date)
        start_date = target - timedelta(days=days_back)
        valid_indices = []
        for idx, chunk in enumerate(self.metadata):
            chunk_date = self._parse_date(chunk.date)
            if start_date <= chunk_date <= target:
                valid_indices.append(idx)
        return valid_indices
    
    def retrieve(self, query: str, date: str, days_back: int = 2, k: int = 10) -> List[Tuple[ChunkMetadata, float]]:
        valid_indices = self._filter_by_date_range(date, days_back)
        if not valid_indices:
            print(f"No chunks found in date range: {date} (looking back {days_back} days)")
            return []
        query_embedding = self.model.encode([query], convert_to_numpy=True, normalize_embeddings=True).astype('float32')
        filtered_embeddings = np.array([self.index.reconstruct(idx) for idx in valid_indices])
        similarities = np.dot(filtered_embeddings, query_embedding.T).flatten()
        top_k_local = min(k, len(valid_indices))
        top_k_indices_local = np.argsort(similarities)[::-1][:top_k_local]
        results = []
        for local_idx in top_k_indices_local:
            global_idx = valid_indices[local_idx]
            chunk = self.metadata[global_idx]
            score = float(similarities[local_idx])
            results.append((chunk, score))
        return results


def retrieve(query: str, date: str, days_back: int = 2, k: int = 10) -> List[Tuple[ChunkMetadata, float]]:
    retriever = VectorRetriever()
    return retriever.retrieve(query, date, days_back, k)


def main():
    indexer = PhaseOneIndexer()
    indexer.build_index()
    print("\n" + "="*70)
    print("TESTING RETRIEVAL")
    print("="*70)
    try:
        retriever = VectorRetriever()
        test_query = "gold price movement"
        test_date = "2025-01-20"
        print(f"\nTest query: '{test_query}'")
        print(f"Target date: {test_date}")
        print(f"Looking back: 2 days")
        results = retriever.retrieve(test_query, test_date, days_back=2, k=3)
        if results:
            print(f"\nTop {len(results)} results:")
            for idx, (chunk, score) in enumerate(results, 1):
                print(f"\n[{idx}] Score: {score:.4f}")
                print(f"Date: {chunk.date}")
                print(f"Sources: {', '.join(chunk.sources)}")
                print(f"Text preview: {chunk.text[:150]}...")
        else:
            print("\nNo results found for test query")
    except FileNotFoundError as e:
        print(f"\nSkipping retrieval test: {e}")
    print("\n" + "="*70)
    print("PHASE ONE INDEXER COMPLETE")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()