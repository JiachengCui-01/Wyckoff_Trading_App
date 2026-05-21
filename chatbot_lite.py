"""
Wyckoff ChatBot - Lightweight Version (RAG Only)
Use this if you don't have GPU locally.
Uses only retrieval (no LLM generation) for fast responses.
"""

import os
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple

# ============================================
# CONFIGURATION
# ============================================

CONFIG = {
    "embedding_model": "sentence-transformers/paraphrase-MiniLM-L6-v2",
    "qa_data_path": "data/wyckoff_all_labels_combined.csv",
    "embeddings_path": "data/question_embeddings.npy",
    "top_k": 3,
}

FALLBACK_ANSWER = (
    "I could not find a high-confidence match in the Wyckoff knowledge base. "
    "Try asking about Springs, Selling Climax, accumulation, distribution, "
    "volume confirmation, or Phase A-E."
)

STRONG_DOMAIN_TERMS = {
    "wyckoff", "accumulation", "distribution", "spring", "shakeout", "phase",
    "volume", "price", "support", "resistance", "entry", "exit", "risk",
    "markup", "markdown", "range", "climax", "selling", "buying", "sos",
    "sow", "lps", "lpsy", "upthrust", "absorption", "demand", "supply",
    "effort", "result", "cause", "effect", "chart", "breakout", "breakdown",
    "test", "law", "laws", "creek", "ice", "composite", "operator",
}


def is_in_scope(question: str) -> bool:
    """Return True when the question is likely covered by the Wyckoff KB."""
    normalized = " ".join(str(question).lower().split())
    if normalized in {
        "hi", "hello", "hey", "yo", "thanks", "thank you", "ok", "okay",
        "test", "testing", "good morning", "good afternoon", "good evening",
    }:
        return False
    return any(term in normalized for term in STRONG_DOMAIN_TERMS)


class WyckoffChatbotLite:
    """
    Lightweight chatbot using only RAG retrieval.
    No LLM generation - returns best matching answers from database.
    Fast and works on any CPU.
    """
    
    def __init__(self, config: dict = CONFIG):
        self.config = config
        self.embedder = None
        self.questions = []
        self.answers = []
        self.labels = []
        self.embeddings = None
        self.collection = None
        self.initialized = False
    
    def initialize(self):
        """Load embedder and build index."""
        from sentence_transformers import SentenceTransformer
        import chromadb
        
        print("📦 Loading embedding model...")
        self.embedder = SentenceTransformer(self.config['embedding_model'])
        
        # Load Q&A data
        print("📊 Loading Q&A data...")
        df = pd.read_csv(self.config['qa_data_path'])
        self.questions = df['Questions'].tolist()
        self.answers = df['Answers'].tolist()
        self.labels = df['Label'].tolist() if 'Label' in df.columns else ['General'] * len(df)
        
        # Load or generate embeddings
        if os.path.exists(self.config['embeddings_path']):
            print("📥 Loading pre-computed embeddings...")
            self.embeddings = np.load(self.config['embeddings_path'])
        else:
            print("🔨 Generating embeddings...")
            self.embeddings = self.embedder.encode(self.questions, show_progress_bar=True)
            os.makedirs(os.path.dirname(self.config['embeddings_path']), exist_ok=True)
            np.save(self.config['embeddings_path'], self.embeddings)
        
        # Build ChromaDB index
        print("🗄️ Building vector index...")
        client = chromadb.Client()
        
        try:
            client.delete_collection("wyckoff_qa")
        except:
            pass
        
        self.collection = client.create_collection("wyckoff_qa")
        self.collection.add(
            embeddings=self.embeddings.tolist(),
            documents=self.questions,
            metadatas=[{"answer": a, "label": l} for a, l in zip(self.answers, self.labels)],
            ids=[f"qa_{i}" for i in range(len(self.questions))]
        )
        
        self.initialized = True
        print(f"✅ Chatbot ready with {len(self.questions)} Q&A pairs!")
    
    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        """Search for similar Q&As."""
        if not self.initialized:
            self.initialize()
        
        query_embedding = self.embedder.encode([query])[0]
        
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k
        )
        
        output = []
        for i in range(len(results['documents'][0])):
            output.append({
                'question': results['documents'][0][i],
                'answer': results['metadatas'][0][i]['answer'],
                'label': results['metadatas'][0][i].get('label', 'General'),
                'similarity': 1 - results['distances'][0][i]
            })
        
        return output
    
    def ask(self, question: str, top_k: int = 3) -> Tuple[str, List[Dict]]:
        """
        Ask a question using semantic search.
        Returns the best matching answer + all context.
        """
        if not is_in_scope(question):
            return FALLBACK_ANSWER, []

        if not self.initialized:
            self.initialize()
        
        context = self.search(question, top_k=top_k)
        
        if context and context[0]['similarity'] > 0.5:
            # Good match - return the answer
            answer = context[0]['answer']
            
            # If similarity is very high, just return the answer
            # Otherwise, combine top answers
            if context[0]['similarity'] < 0.8 and len(context) > 1:
                # Combine insights from multiple matches
                answer = context[0]['answer']
                if context[1]['similarity'] > 0.6:
                    answer += f"\n\n{context[1]['answer'][:200]}..."
        else:
            answer = FALLBACK_ANSWER
            context = []
        
        return answer, context
    
    def get_suggested_questions(self) -> List[str]:
        """Return suggested questions."""
        return [
            "What is a Spring in Wyckoff methodology?",
            "What are Wyckoff's three fundamental laws?",
            "How do I identify accumulation?",
            "What volume patterns indicate distribution?",
            "When is the best time to enter after a Selling Climax?",
            "What is the difference between Phase B and Phase C?",
        ]


# For easy import in app.py
# Just change the import to use this instead:
# from chatbot_lite import WyckoffChatbotLite as WyckoffChatbot


if __name__ == "__main__":
    print("🧪 Testing Lite Chatbot (RAG only)...")
    
    bot = WyckoffChatbotLite()
    
    questions = [
        "What is a Spring?",
        "When should I buy?",
        "What are the three laws?",
    ]
    
    for q in questions:
        print(f"\n❓ {q}")
        answer, context = bot.ask(q)
        print(f"✅ {answer[:200]}...")
        print(f"   (Similarity: {context[0]['similarity']:.2f})")
