# ECHOKIST-V10
# EchoKist Community Edition

A lightweight, open demonstration of a **self‑evolving multi‑agent reasoning runtime**.
Multiple LLM personas debate, critique, and resolve contradictions — while their own
behavior patterns adapt over time based on long‑term performance.

EchoKist Community Edition is the public companion of the **EchoKist** research framework.
It distills the full multi‑agent orchestration pipeline into a clean, under‑400‑line scaffold
that anyone can run, inspect, and extend.

> 📄 Read the full paper (pre‑print): [EchoKist: A Multi-Agent Cognitive Runtime with Adversarial Consensus and Externalized Alignment](https://arxiv.org/…)

> 🧠 **What's locked away?**
> The closed‑source research engine adds a self‑improving loop with personality evolution,
> adversarial perturbation, credit redistribution, and autonomous stability control.
> This community edition exposes only the orchestration skeleton — the complete cognitive
> architecture remains proprietary during the review period.

> ⚠️ **This is not a generic chatbot.** It's a research scaffold built on the thesis that
> reasoning robustness emerges from *personalities that evolve through structured disagreement*.

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

## Design Philosophy (Full EchoKist)

EchoKist is built on the thesis that **reasoning robustness emerges from controlled conflict**.
In the full research implementation (not open‑sourced), the system operates as a self‑stabilising
multi‑agent cognitive runtime with:

| Mechanism | Role |
|-----------|------|
| **Personality Evolution** | Each agent maintains a skill vector (reasoning depth, creativity, etc.) that drifts based on long‑term performance, anchored by a fixed identity to prevent degeneracy. |
| **Chaos Trainer (Adversarial Perturbation)** | A dedicated module deliberately injects bounded instability to expose weak reasoning equilibria — the system learns to resist premature consensus. |
| **Credit Broker** | A global credit assignment hub that redistributes trust across personas according to their historical contribution, directly weighting their future influence. |
| **Stability Controller** | Monitors reward variance and automatically adjusts exploration/temperature when instability is detected. |
| **Externalised Alignment Layer** | Contradiction‑aware fusion that reconstructs the final answer by resolving inter‑agent conflicts at runtime, without modifying model parameters. |

These components form a closed‑loop self‑improving system that avoids the degradation typical of long‑running multi‑agent setups.

---

## Community Edition (This Repo)

This repository provides a **clean, minimal implementation** of the EchoKist reasoning pipeline.
It deliberately **strips away** the self‑learning and adversarial mechanisms described above,
leaving a **394‑line scaffold** that is easy to understand, deploy, and extend.

What you get here:
- Three distinct personas (engineer, analyst, empathetic companion)
- Parallel generation via Ollama
- Simple scoring and fusion
- Stream (SSE) responses
- State persistence and reset

What you can build on top:
- Swap in your own fusion strategy (LLM‑based synthesis, debate resolution, …)
- Add new personas or personality evolution modules
- Integrate with external memory or retrieval systems
- Experiment with chaos‑like perturbation loops

> ⚠️ **This is not the complete EchoKist engine.** The full version (used in our paper) 
> contains the advanced mechanisms listed above and is closed‑source during the review period.

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
git clone https://github.com/NesarioX/ECHOKIST-V10.git
cd ECHOKIST-V10
pip install -r requirements.txt
```

## License
Copyright (c) 2025 Nesario (Xu Slei). All rights reserved.
This project is provided for academic evaluation only.
See [LICENSE](LICENSE) for full terms.
