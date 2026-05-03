"""
EchoKist Community Edition
--------------------------
A lightweight, extensible multi-agent reasoning engine.
This version showcases the core architecture of EchoKist without 
exposing its proprietary "soul" — the intricate training loops, 
advanced memory hierarchies, and complex arbitration policies.
Feel free to fork, extend, and add your own spark.
"""

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from datetime import datetime
import requests
import json
import os
import re
import threading
import logging
import random

# ------------------------ Configuration ------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("EchoKist-Community")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral:latest")
STATE_FILE = "echokist_community_state.json"
MAX_CONTEXT_MESSAGES = 3

app = FastAPI(title="EchoKist Community")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

# ------------------------ SSE Helpers --------------------------
def sse_event(event_type: str, data: Dict) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {payload}\n\n"

def sse_stream_event(chunk: str) -> str:
    payload = json.dumps({"token": chunk}, ensure_ascii=False)
    return f"data: {payload}\n\n"

# ------------------------ Persistence --------------------------
def save_state(engine_state: Dict) -> None:
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(engine_state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Save state failed: {e}")

def load_state() -> Optional[Dict]:
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Load state failed: {e}")
    return None

# ------------------------ Ollama Client ------------------------
class OllamaClient:
    """Simple synchronous & streaming client for Ollama."""
    def __init__(self):
        self.semaphore = threading.Semaphore(2)  # concurrency guard

    def _clean_output(self, text: str) -> str:
        if not text:
            return text
        # Remove common verbose prefixes
        text = re.sub(r'^(Alright|Here|Listen|Note|Look)\s*[,!]*\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'^(Final answer|Answer|Integrated answer)[：:]\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'【.*?】', '', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip() or "[I'm sorry, the response was empty after cleaning.]"

    def call(self, persona_name: str, prompt: str, system: str = "",
             temperature: float = 0.7, top_p: float = 0.9, max_tokens: int = 500) -> str:
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "top_p": top_p, "num_predict": max_tokens}
        }
        if system:
            payload["system"] = system
        with self.semaphore:
            try:
                r = requests.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=60)
                r.raise_for_status()
                result = r.json().get("response", "[No response]")
            except Exception as e:
                result = f"[Call Error] {str(e)}"
        return self._clean_output(result)

    def stream(self, persona_name: str, prompt: str, system: str = "",
               temperature: float = 0.7, top_p: float = 0.9):
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": True,
            "options": {"temperature": temperature, "top_p": top_p, "num_predict": 500}
        }
        if system:
            payload["system"] = system
        with self.semaphore:
            try:
                with requests.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, stream=True, timeout=120) as r:
                    r.raise_for_status()
                    for line in r.iter_lines():
                        if line:
                            try:
                                data = json.loads(line.decode("utf-8"))
                                if "response" in data:
                                    yield data["response"]
                            except Exception:
                                continue
            except Exception as e:
                yield f"\n[Stream Error] {str(e)}"

# ------------------------ Persona Blueprint --------------------
class PersonaProfile:
    """Defines a persona: identity, style, and dynamic parameters."""
    def __init__(self, name: str, role: str, style: str, temperature: float = 0.7):
        self.name = name
        self.role = role
        self.style = style               # short text influencing prompt
        self.temperature = temperature
        self.top_p = 0.9
        self.bias = 0.5                  # initial selection weight
        self.wins = 0
        self.total = 0

    def system_prompt(self) -> str:
        return f"You are {self.name}, {self.style}. {self.role}"

    def success_rate(self) -> float:
        return self.wins / max(self.total, 1)

    def update_selection_weight(self, global_reward: float):
        self.bias = 0.5 + 0.5 * global_reward * self.success_rate()

    def to_dict(self):
        return {
            "name": self.name,
            "role": self.role,
            "style": self.style,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "bias": self.bias,
            "wins": self.wins,
            "total": self.total
        }

    @classmethod
    def from_dict(cls, data):
        obj = cls(data["name"], data["role"], data["style"], data.get("temperature", 0.7))
        obj.top_p = data.get("top_p", 0.9)
        obj.bias = data.get("bias", 0.5)
        obj.wins = data.get("wins", 0)
        obj.total = data.get("total", 0)
        return obj

# ------------------------ Simple Memory ------------------------
class ConversationMemory:
    """Episodic memory: stores recent interactions for context injection."""
    def __init__(self, max_entries: int = 10):
        self.entries: List[Dict] = []
        self.max_entries = max_entries
        self.lock = threading.Lock()

    def add(self, user_msg: str, assistant_msg: str, score: float = 0.5):
        with self.lock:
            self.entries.append({
                "user": user_msg,
                "assistant": assistant_msg,
                "score": score,
                "timestamp": datetime.now().isoformat()
            })
            if len(self.entries) > self.max_entries:
                self.entries.pop(0)

    def get_context(self, current_query: str, k: int = 3) -> str:
        with self.lock:
            if not self.entries:
                return ""
            recent = self.entries[-k:]
            lines = []
            for e in recent:
                lines.append(f"User: {e['user']}\nAssistant: {e['assistant']}")
            return "\n".join(lines)

# ------------------------ Core Engine --------------------------
class EchoKistCommunityEngine:
    def __init__(self):
        # Load state if exists
        raw = load_state()
        if raw:
            self._init_from_raw(raw)
        else:
            self._init_defaults()

        self.ollama = OllamaClient()
        self.memory = ConversationMemory()
        self.lock = threading.RLock()
        self.total_interactions = 0

    def _init_defaults(self):
        self.personas = {
            "self": PersonaProfile("Self", "practical engineer", "I value efficiency and clear steps.", temperature=0.5),
            "einstein": PersonaProfile("Einstein", "analytical thinker", "I explore logical depth and structure.", temperature=0.7),
            "family": PersonaProfile("Family", "empathetic companion", "I listen deeply and respond with care.", temperature=0.6)
        }
        self.last_dominant = "self"

    def _init_from_raw(self, state):
        personas_raw = state.get("personas", {})
        self.personas = {}
        for k, v in personas_raw.items():
            if isinstance(v, dict):
                self.personas[k] = PersonaProfile.from_dict(v)
            else:
                # fallback
                self.personas[k] = PersonaProfile(k, "agent", "a helpful assistant")
        self.last_dominant = state.get("last_dominant", "self")

    def _to_raw(self):
        return {
            "personas": {k: v.to_dict() for k, v in self.personas.items()},
            "last_dominant": self.last_dominant
        }

    def _infer_domain(self, text: str) -> str:
        """Basic domain detection for context (placeholder)."""
        t = text.lower()
        if any(k in t for k in ["math", "calculate", "equation"]):
            return "math"
        if any(k in t for k in ["emotion", "feel", "anxious", "happy"]):
            return "emotion"
        return "general"

    def _select_personas(self, mode: str, requested: str) -> List[str]:
        if mode == "light":
            return [requested]
        # For demonstration, pick one complementary persona
        others = [p for p in self.personas if p != requested]
        if not others:
            return [requested]
        chosen = random.choices(others, weights=[self.personas[p].bias for p in others], k=1)[0]
        return [requested, chosen]

    def _generate_candidate(self, persona_key: str, user_text: str, context: str) -> str:
        profile = self.personas[persona_key]
        system = profile.system_prompt()
        prompt = f"{context}\n\nUser: {user_text}\n{profile.name}:"
        return self.ollama.call(persona_key, prompt, system,
                                temperature=profile.temperature,
                                top_p=profile.top_p)

    def _fusion(self, candidates: Dict[str, str], user_text: str) -> str:
        """Simple fusion: pick best or concatenate (community placeholder)."""
        # Here we just return the first candidate as a naive demonstration.
        # Community developers can replace with advanced merge strategies.
        if not candidates:
            return "I have no response."
        # Pick the longest for simplicity
        best = max(candidates.items(), key=lambda x: len(x[1]))
        return best[1]

    def _update_personas(self, scores: Dict[str, float], final_score: float):
        winner = max(scores, key=scores.get) if scores else None
        for p, profile in self.personas.items():
            profile.total += 1
            if p == winner:
                profile.wins += 1
            profile.update_selection_weight(final_score)

    def run_interaction(self, requested_persona: str, user_msg: str) -> Dict[str, Any]:
        mode = "medium" if len(user_msg) > 50 else "light"
        domain = self._infer_domain(user_msg)
        context = self.memory.get_context(user_msg, k=3)

        # Select active agents
        active = self._select_personas(mode, requested_persona)

        # Generate answers from each
        candidates = {}
        for p in active:
            candidates[p] = self._generate_candidate(p, user_msg, context)

        # Simple scoring: length + persona bias
        scores = {}
        for p, answer in candidates.items():
            length_bonus = min(10, len(answer)) / 100.0
            scores[p] = self.personas[p].bias + length_bonus

        final_answer = self._fusion(candidates, user_msg)

        # Simulate a global reward (0..1) based on answer length and diversity
        global_reward = min(1.0, (len(final_answer) / 200) * 0.7 + 0.3)

        self._update_personas(scores, global_reward)

        # Store memory
        self.memory.add(user_msg, final_answer, global_reward)

        self.total_interactions += 1
        self.last_dominant = max(scores, key=scores.get) if scores else requested_persona

        save_state(self._to_raw())

        return {
            "response": final_answer,
            "active_personas": active,
            "scores": scores,
            "global_reward": round(global_reward, 3),
            "domain": domain
        }

    def stream_interaction(self, requested_persona: str, user_msg: str):
        # For streaming, we generate tokens from the selected dominant persona (simplified)
        result = self.run_interaction(requested_persona, user_msg)
        final_answer = result["response"]
        yield sse_event("start", {
            "type": "start",
            "persona": self.last_dominant,
            "scores": result["scores"],
            "confidence": result["global_reward"],
            "mode": "community"
        })
        # Stream final_answer in chunks
        chunk_size = 4
        for i in range(0, len(final_answer), chunk_size):
            yield sse_stream_event(final_answer[i:i+chunk_size])
        yield sse_event("done", {})

# ------------------------ API Endpoints ------------------------
engine = EchoKistCommunityEngine()

class ChatRequest(BaseModel):
    persona: str = "self"
    messages: List[str]

@app.post("/chat")
def chat(req: ChatRequest):
    if not req.messages:
        return {"response": "Hello! How can I help you today?"}
    result = engine.run_interaction(req.persona, req.messages[-1])
    return result

@app.post("/chat/stream")
def chat_stream(req: ChatRequest):
    if not req.messages:
        def empty():
            yield sse_event("start", {"type": "start", "persona": "self", "mode": "light"})
            yield sse_event("done", {})
        return StreamingResponse(empty(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "Connection": "keep-alive"})
    return StreamingResponse(
        engine.stream_interaction(req.persona, req.messages[-1]),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )

@app.get("/status")
def status():
    with engine.lock:
        return {
            "last_dominant": engine.last_dominant,
            "personas": {
                p: {"bias": engine.personas[p].bias,
                    "wins": engine.personas[p].wins,
                    "total": engine.personas[p].total}
                for p in engine.personas
            },
            "total_interactions": engine.total_interactions,
            "memory_length": len(engine.memory.entries)
        }

@app.post("/reset")
def reset_state():
    global engine
    engine = EchoKistCommunityEngine()
    engine._init_defaults()
    save_state(engine._to_raw())
    return {"status": "reset"}

# ------------------------ Run --------------------------------
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting EchoKist Community Edition server")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
