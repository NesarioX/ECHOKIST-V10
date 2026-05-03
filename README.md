# ECHOKIST-V10
# EchoKist Community Edition

A lightweight, extensible multi-agent reasoning runtime that demonstrates how multiple LLM personas can collaborate to generate more robust answers.

EchoKist Community Edition is the public companion of the **EchoKist** research framework. It provides a clean, minimal implementation of the multi-agent reasoning pipeline, leaving plenty of hooks for the community to experiment, extend, and contribute.

> 📄 Read the full paper (pre‑print): [EchoKist: A Multi-Agent Cognitive Runtime with Adversarial Consensus and Externalized Alignment](https://arxiv.org/…)  
> 🧠 Private research version (closed‑source) contains advanced training loops, personality drift control, adversarial chaos training, and hierarchical memory. This community edition exposes the **core orchestration skeleton** in under 400 lines of Python.

## Table of Contents
- [Architecture Overview](#architecture-overview)
- [Quick Start](#quick-start)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Starting the server](#starting-the-server)
- [Configuration](#configuration)
- [API Endpoints](#api-endpoints)
  - [POST /chat](#post-chat)
  - [POST /chat/stream](#post-chatstream)
  - [GET /status](#get-status)
  - [POST /reset](#post-reset)
- [Extending the System](#extending-the-system)
- [Roadmap (Community Contributions)](#roadmap-community-contributions)
- [Citation](#citation)
- [License](#license)

## Architecture Overview

EchoKist Community Edition organizes reasoning around three built‑in personas:

| Persona | Role | Style |
|---------|------|-------|
| **Self** | Practical engineer | Efficiency, clear steps, direct answers |
| **Einstein** | Analytical thinker | Logical depth, structured reasoning |
| **Family** | Empathetic companion | Emotional warmth, caring tone |

A request flows through the following stages:

1. **Router** decides the interaction **mode** (`light` or `medium`) based on query complexity.
2. **Persona selection** picks one or more active agents according to their current selection weights.
3. **Parallel generation** – each chosen persona independently generates a candidate answer using a local LLM (via Ollama).
4. **Scoring** ranks the candidates using a simple heuristic (persona bias + answer length).
5. **Fusion** merges the candidates into a final response (the default implementation picks the longest answer as a demonstration; this is the most important extension point for contributors).
6. The final answer is returned (or streamed) to the client, and internal persona statistics are updated for future selections.

> ⚠️ **Note:** This community version does **not** include the adversarial chaos training, credit assignment, or persona drift control present in the full EchoKist engine. Those components are part of the proprietary research codebase.

## Quick Start

### Prerequisites
- Python 3.9+
- [Ollama](https://ollama.com) running locally (default URL: `http://localhost:11434`)
- A model pulled inside Ollama (default `mistral:latest`; you can override via environment variables)

### Installation
```bash
git clone https://github.com/YOUR_USER/echokist-community.git
cd echokist-community
pip install -r requirements.txt
