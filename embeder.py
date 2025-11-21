import os
import json
from pathlib import Path
from sentence_transformers import SentenceTransformer
import numpy as np

def generate_embeddings(summaries_dir='daily_summaries', output_file='embeddings.json'):
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    summaries_path = Path(summaries_dir)
    if not summaries_path.exists():
        raise FileNotFoundError(f"{summaries_dir} not found")
    
    txt_files = sorted(summaries_path.glob('*.txt'))
    if not txt_files:
        raise FileNotFoundError(f"No .txt files in {summaries_dir}")
    
    embeddings_data = []
    
    for txt_file in txt_files:
        with open(txt_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        if not content:
            continue
        
        embedding = model.encode(content)
        
        embeddings_data.append({
            'date': txt_file.stem,
            'file_path': str(txt_file),
            'embedding': embedding.tolist(),
            'text': content
        })
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(embeddings_data, f, indent=2)
    
    return len(embeddings_data)

if __name__ == '__main__':
    count = generate_embeddings()
    print(f"Processed {count} summaries")