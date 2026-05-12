# 🚀 Elite-DA Project: Multi-Agent Corporate Intelligence

Welcome to the **Elite-DA Project**, a unified intelligence system designed to harvest, analyze, and manage Vietnamese corporate data (MST) using cutting-edge AI agents and a modern tech stack.

---

## 🏗 Project Architecture

This repository has been unified into a high-performance multi-module structure:

- **`frontend/`**: A premium React + Vite application for data visualization and interaction.
- **`backend-api/`**: AI-powered CRM & Market Research agents built with Streamlit and LangChain.
- **`data-pipeline/`**: Advanced corporate scrapers using DrissionPage and Cloudflare bypass technologies.

---

## 🛠 Tech Stack

| Component | Technology |
| :--- | :--- |
| **Frontend** | React, Vite, TypeScript, Vanilla CSS |
| **Backend** | Python, Streamlit, LangChain, OpenAI/Gemini/Groq |
| **Database** | Supabase (PostgreSQL) |
| **Crawler** | DrissionPage, curl_cffi, BeautifulSoup4 |
| **DevOps** | Docker, Docker Compose, Windows Batch Scripts |

---

## 🚦 Quick Start

### 1. Configure Environment
Create/Edit the `.env` file in the root directory with your keys:
```env
OPENAI_API_KEY=your_key
GEMINI_API_KEY=your_key
SUPABASE_URL=your_url
SUPABASE_KEY=your_key
```

### 2. Run the System
Execute the unified launch script in your terminal:
```cmd
run_all.bat
```
*This will open separate windows for the Frontend and the AI Backend.*

---

## 📂 Directory Map
```text
elite-da-project/
├── backend-api/     # CRM Agents & Backend Logic
├── frontend/        # React User Interface
├── data-pipeline/   # Corporate Crawlers (MST)
├── docker-compose.yml
├── .env             # Global Configuration
└── run_all.bat      # Unified Execution Script
```

---

## 📈 Roadmap
- [x] Unify repositories into a single structure.
- [x] Configure global environment variables.
- [x] Implement direct Supabase synchronization for AI agents.
- [x] Add real-time data visualization dashboards in the React frontend.
- [ ] Optimize Multi-Agent self-correction logic.
- [ ] Expand crawling coverage to 500K+ enterprises.

---
*Developed with ❤️ for Advanced Corporate Intelligence.*
