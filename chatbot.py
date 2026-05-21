"""
Wyckoff ChatBot Module
Combines RAG retrieval with Fine-tuned LLaMA
"""

import os
import torch
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional

# ============================================
# CONFIGURATION
# ============================================

CONFIG = {
    "model_path": "models/llama_wyckoff_lora",
    "base_model": "meta-llama/Llama-2-7b-hf",
    "embedding_model": "sentence-transformers/paraphrase-MiniLM-L6-v2",
    "qa_data_path": "data/wyckoff_all_labels_combined.csv",
    "embeddings_path": "data/question_embeddings.npy",
    "top_k": 3,
    "max_new_tokens": 300,
    "temperature": 0.7,
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


# ============================================
# VECTOR STORE (RAG)
# ============================================

class VectorStore:
    """Handles embedding and retrieval of Q&A pairs."""
    
    def __init__(self, config: dict = CONFIG):
        self.config = config
        self.embedder = None
        self.questions = []
        self.answers = []
        self.labels = []
        self.embeddings = None
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
            np.save(self.config['embeddings_path'], self.embeddings)
        
        # Build ChromaDB index
        print("🗄️ Building vector index...")
        self.client = chromadb.Client()
        
        try:
            self.client.delete_collection("wyckoff_qa")
        except:
            pass
        
        self.collection = self.client.create_collection("wyckoff_qa")
        self.collection.add(
            embeddings=self.embeddings.tolist(),
            documents=self.questions,
            metadatas=[{"answer": a, "label": l} for a, l in zip(self.answers, self.labels)],
            ids=[f"qa_{i}" for i in range(len(self.questions))]
        )
        
        self.initialized = True
        print(f"✅ Vector store ready with {len(self.questions)} Q&A pairs!")
    
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


# ============================================
# LLM RESPONSE GENERATOR
# ============================================

class LLMGenerator:
    """Handles response generation with fine-tuned LLaMA."""
    
    def __init__(self, config: dict = CONFIG):
        self.config = config
        self.model = None
        self.tokenizer = None
        self.initialized = False
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
    
    def initialize(self):
        """Load fine-tuned model."""
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        from peft import PeftModel
        
        print(f"📦 Loading fine-tuned model on {self.device}...")
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.config['model_path'],
            trust_remote_code=True,
            use_fast=False
        )
        self.tokenizer.pad_token = self.tokenizer.eos_token
        
        if self.device == "cuda":
            # Load with quantization for GPU
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16
            )
            
            base_model = AutoModelForCausalLM.from_pretrained(
                self.config['base_model'],
                quantization_config=bnb_config,
                device_map="auto",
                torch_dtype=torch.float16,
                trust_remote_code=True
            )
        else:
            # CPU loading (slower but works)
            base_model = AutoModelForCausalLM.from_pretrained(
                self.config['base_model'],
                device_map="auto",
                torch_dtype=torch.float32,
                trust_remote_code=True,
                low_cpu_mem_usage=True
            )
        
        # Load LoRA adapters
        self.model = PeftModel.from_pretrained(base_model, self.config['model_path'])
        self.model.eval()
        
        self.initialized = True
        print("✅ Model loaded!")
    
    def generate(self, prompt: str, max_tokens: int = None) -> str:
        """Generate response from prompt."""
        if not self.initialized:
            self.initialize()
        
        max_tokens = max_tokens or self.config['max_new_tokens']
        
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=1024
        ).to(self.model.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=self.config['temperature'],
                top_p=0.9,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id,
                repetition_penalty=1.1
            )
        
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract answer part
        if "### Answer:" in response:
            response = response.split("### Answer:")[-1].strip()
        
        return response


# ============================================
# COMBINED CHATBOT
# ============================================

class WyckoffChatbot:
    """
    Complete Wyckoff Chatbot combining RAG + Fine-tuned LLM.
    """
    
    _initialization_attempted = False  # Class-level flag to prevent repeated attempts
    
    def __init__(self, config: dict = CONFIG):
        self.config = config
        self.vector_store = VectorStore(config)
        self.llm = LLMGenerator(config)
        self.conversation_history = []
        self.initialized = False
        self.llm_available = False
    
    def initialize(self):
        """Initialize all components."""
        if self.initialized or WyckoffChatbot._initialization_attempted:
            return
        
        WyckoffChatbot._initialization_attempted = True
        print("🚀 Initializing Wyckoff Chatbot...")
        
        # Always initialize vector store (RAG)
        self.vector_store.initialize()
        
        # Try to initialize LLM, but don't fail if unavailable
        try:
            self.llm.initialize()
            self.llm_available = True
        except Exception as e:
            print(f" LLM not available (RAG-only mode): {e}")
            self.llm_available = False
        
        self.initialized = True
        print(" Chatbot ready!" + (" (RAG-only mode)" if not self.llm_available else ""))
    
    def _build_prompt(self, question: str, context: List[Dict], use_rag: bool) -> str:
        """Build prompt with optional RAG context."""
        context_str = ""
        
        if use_rag and context:
            context_str = "\n--- Relevant Wyckoff Knowledge ---\n"
            for i, c in enumerate(context, 1):
                context_str += f"\n[{i}] Q: {c['question']}\n    A: {c['answer']}\n"
            context_str += "\n--- End of Context ---\n"
        
        prompt = f"""### Instruction:
You are an expert on Richard Wyckoff's trading methodology with deep knowledge of market phases, price-volume analysis, and institutional trading patterns.{' Use the provided context to enhance your answer.' if use_rag else ''} Provide detailed, practical answers.
{context_str}

### Question:
{question}

### Answer:
"""
        return prompt
    
    def ask(
        self, 
        question: str, 
        use_rag: bool = True, 
        top_k: int = 3
    ) -> Tuple[str, List[Dict]]:
        """
        Ask a question and get response.
        
        Args:
            question: User's question
            use_rag: Whether to use RAG retrieval
            top_k: Number of context items to retrieve
            
        Returns:
            (answer, retrieved_context)
        """
        if not is_in_scope(question):
            return FALLBACK_ANSWER, []

        if not self.initialized:
            self.initialize()
        
        # Retrieve context
        context = []
        if use_rag:
            context = self.vector_store.search(question, top_k=top_k)
        
        # Generate response - use LLM if available, otherwise RAG-only
        if self.llm_available:
            prompt = self._build_prompt(question, context, use_rag)
            answer = self.llm.generate(prompt)
        else:
            # RAG-only fallback: return best matching answer
            if context and context[0]['similarity'] > 0.5:
                answer = context[0]['answer']
                if len(context) > 1 and context[1]['similarity'] > 0.6:
                    answer += f"\n\n{context[1]['answer'][:300]}..."
            else:
                answer = FALLBACK_ANSWER
                context = []
        
        # Store in history
        self.conversation_history.append({
            'question': question,
            'answer': answer,
            'context': context
        })
        
        return answer, context
    
    def ask_simple(self, question: str) -> str:
        """
        Quick answer using only RAG (no LLM generation).
        Returns best matching answer from database.
        """
        if not is_in_scope(question):
            return FALLBACK_ANSWER

        if not self.vector_store.initialized:
            self.vector_store.initialize()
        
        results = self.vector_store.search(question, top_k=1)
        if results:
            return results[0]['answer']
        return "I don't have specific information about that topic."
    
    def get_suggested_questions(self) -> List[str]:
        """Return suggested questions for the user."""
        return [
            "What is a Spring in Wyckoff methodology?",
            "What are Wyckoff's three fundamental laws?",
            "How do I identify the transition from Phase B to Phase C?",
            "What volume patterns indicate accumulation?",
            "When is the best time to enter after a Selling Climax?",
            "What is the difference between a Spring and a Shakeout?",
            "How does the Composite Man concept work?",
            "What are the signs of distribution?",
        ]
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []


# ============================================
# QUICK TEST
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Testing Wyckoff Chatbot")
    print("=" * 60)
    
    bot = WyckoffChatbot()
    
    test_questions = [
        "What is a Spring?",
        "When should I enter after seeing a Selling Climax?",
    ]
    
    for q in test_questions:
        print(f"\n❓ {q}")
        answer, context = bot.ask(q)
        print(f"✅ {answer[:300]}...")
