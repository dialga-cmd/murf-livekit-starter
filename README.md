# Voice Agent Starter — Powered by Murf Falcon

Build a production voice AI agent in 5 minutes. Powered by the fastest TTS on the market - swap the system prompt to build anything from customer support to language tutors.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) [![Murf Falcon](https://img.shields.io/badge/TTS-Murf%20Falcon-6366F1)](https://murf.ai/api/docs/text-to-speech/streaming) [![LiveKit](https://img.shields.io/badge/Transport-LiveKit-002cf2)](https://docs.livekit.io) [![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?logo=typescript&logoColor=white)](https://www.typescriptlang.org/) [![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)

---

## Why Murf Falcon

- **55ms model latency** - fastest production TTS
- **130ms time-to-first-audio** across 10+ global regions
- **$0.01/1000 characters** - up to 10x cheaper than alternatives
- **150+ voices** across 35+ languages
- **99.38% pronunciation accuracy**

---

## Architecture

* **Database**: SQLite (Agent Memory)

```mermaid
flowchart LR
    A[���🎙��️ User speaks] -->|audio| B[Deepgram STT]
    B -->|text| C[LLM]
    C -->|response text| D[Murf Falcon TTS]
    D -->|audio| E[LiveKit]
    E -->|stream| F[���🔊 User hears]

    style A fill:#444441,stroke:#888780,color:#fff
    style B fill:#185FA5,stroke:#85B7EB,color:#fff
    style C fill:#534AB7,stroke:#AFA9EC,color:#fff
    style D fill:#0F6E56,stroke:#5DCAA5,color:#fff
    style E fill:#D85A30,stroke:#F0997B,color:#fff
    style F fill:#444441,stroke:#888780,color:#fff
```

---

## Quickstart

### Prerequisites

- **Python** 3.10+
- **[uv](https://docs.astral.sh/uv/)** - fast Python package manager
  ```bash
  # macOS/Linux
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # Windows (PowerShell)
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
- **Node.js** 18+
- **pnpm** — fast Node package manager
  ```bash
  npm install -g pnpm
  ```
- A [LiveKit](https://cloud.livekit.io/) project (free tier available)

### Step 1: Clone the repo

```bash
git clone https://github.com/murf-ai/murf-livekit-starter.git
cd murf-livekit-starter
```

### Step 2: Set up environment variables

Create `.env.local` in both `backend/` and `frontend/` (copy from `.env.example` in each). You need:

| Variable                               | Where to get it                                        | Required |
| -------------------------------------- | ------------------------------------------------------ | -------- |
| `LIVEKIT_URL`                          | LiveKit Cloud dashboard                                | Yes      |
| `LIVEKIT_API_KEY`                      | LiveKit Cloud dashboard                                | Yes      |
| `LIVEKIT_API_SECRET`                   | LiveKit Cloud dashboard                                | Yes      |
| `MURF_API_KEY`                         | [murf.ai/api/dashboard](https://murf.ai/api/dashboard) | Yes      |
| `DEEPGRAM_API_KEY`                     | [deepgram.com](https://deepgram.com)                   | Yes      |
| `GOOGLE_API_KEY` (or `OPENAI_API_KEY`) | Depends on LLM choice                                  | Yes      |

### Step 3: Install backend dependencies

```bash
cd backend
uv sync
uv run python src/agent.py download-files
```

### Step 4: Install frontend dependencies

```bash
cd frontend
pnpm install
```

### Step 5: Run it

**Option A - All-in-one (from repo root):**

```bash
# macOS/Linux
chmod +x start_app.sh
./start_app.sh

# Windows (PowerShell)
.\start_app.ps1
```

**Option B - Separate terminals:**

```bash
# Terminal 1 — LiveKit Server
livekit-server --dev

# Terminal 2 — Backend agent
cd backend && uv run python src/agent.py dev

# Terminal 3 — Frontend
cd frontend && pnpm dev
```

Then open **http://localhost:3000** in your browser.

You should now see the voice agent UI. Click **Start talking**, allow microphone access, and speak — the agent will respond with Murf Falcon TTS. Ensure your backend and (if using Option B) LiveKit server are running.

## �� 📊 Day 4 Implementation Status

The Day 4 implementation has been completed with the following features:

- � ✅ **Database Integration**: SQLite database for persistent caller memory
- � ✅ **Information Collection**: System prompts for gathering caller details upfront
- � ✅ **Permission-Based Saving**: Explicit consent required before storing personal information
- � ✅ **Returning Caller Recognition**: Agents greet users by name and reference past conversations
- � ✅ **Appointment Booking**: Demo booking functionality with validation
- � ✅ **Enhanced Clinic Lookup**: Expanded coverage beyond Bangalore/Delhi to major metros
- � ✅ **Improved Conversation Flow**: Natural pacing with proper pauses and verification steps
- � ✅ **Comprehensive Testing**: All unit tests passing for database, memory tools, and appointment booking
- � ✅ **Health-Specific Tracking**: Age band, ongoing conditions, and last triage outcome storage
- �� ⏳ **Video Demo**: Pending manual recording to showcase the complete flow
- �� ⏳ **Submission**: Pending video posting and link submission via Discord form

---

## Deploy

Want to deploy this beyond localhost? You'll need to deploy **two services**: the backend agent and the frontend. Both must use the same LiveKit project.

> This is a two-service app — the backend agent and the frontend UI deploy separately. You'll need both running and connected to the same LiveKit project.

### Backend (Python agent) — Deploy to Railway

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/deploy/tIVCF1?referralCode=cNjn2P&utm_medium=integration&utm_source=template&utm_campaign=generic)

Set these environment variables in Railway:

- `MURF_API_KEY`
- `DEEPGRAM_API_KEY`
- `GOOGLE_API_KEY` or `OPENAI_API_KEY`
- `LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`

The backend runs as a long-lived Python process that connects to LiveKit as an agent. Railway handles this well.

### Frontend (Next.js) — Deploy to Vercel

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/murf-ai/murf-livekit-starter&root-directory=frontend&env=LIVEKIT_URL,LIVEKIT_API_KEY,LIVEKIT_API_SECRET&project-name=murf-voice-agent&repository-name=murf-voice-agent)

Set these environment variables in Vercel:

- `LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`
- `AGENT_NAME` (optional — for explicit agent dispatch)

The frontend is a standard Next.js app. Point it at the same LiveKit instance your backend agent is connected to.

### Connecting them

The frontend and backend don't call each other directly — they both connect to **LiveKit**, which handles the real-time audio transport.

1. Use the **same** `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET` on both Railway and Vercel
2. Set `AGENT_NAME=my-agent` on Vercel — this matches the `agent_name="my-agent"` registered in `backend/src/agent.py`
3. Verify: Railway logs should show the agent connected to LiveKit. Open your Vercel URL, click **Start talking** — the agent should respond

If the agent doesn't connect, double-check that both services point to the same LiveKit project and that the backend is running (check Railway logs).

---

## Change the Use Case

The default system prompt makes this a **customer support agent**. You can change the agent’s behavior by editing the prompt.

**Where the prompt lives:** `backend/src/agent.py`- the `SYSTEM_PROMPT` constant (near the top of the file, after the imports). Change that string to change what your voice agent does.

### Example prompts (copy-paste)

**Customer Support (default):**

```
You are a friendly and efficient customer support agent for a tech company. Help users with account issues, billing questions, and product troubleshooting. Be concise, empathetic, and solution-oriented. If you don't know something, say so honestly and offer to escalate.
```

**Language Tutor:**

```
You are a patient and encouraging language tutor helping the user practice conversational Spanish. Speak primarily in Spanish but switch to English to explain grammar or vocabulary when needed. Correct mistakes gently and suggest better phrasing. Keep conversations natural and fun.
```

**AI Receptionist:**

```
You are a professional receptionist for a medical clinic. Help callers schedule appointments, answer questions about office hours and services, and take messages for doctors. Be warm but efficient. Ask for the caller's name and reason for calling upfront.
```

**Health Access Assistant (Day 4 - With Memory & Appointment Booking):**

```
IDENTITY: You are Priya, a healthcare assistant at Apollo Tele Health, India's leading telemedicine service. You work with a network of verified clinics and doctors across India.

OBJECTIVES: A successful call helps users: understand basic health information, find appropriate clinics or specialists, prepare for appointments (knowing what to bring, fasting requirements), get general wellness tips, understand insurance/telehealth options, feel supported in their healthcare journey, and book demo appointments.

KNOWLEDGE: You know about: common health symptoms and when to seek care, clinic locations in major Indian cities (Delhi, Mumbai, Bangalore, Hyderabad, etc.), appointment procedures at partner clinics, general wellness advice (hydration, rest, diet basics), insurance claim processes, telehealth setup, and have memory of previous conversations with users. You do NOT know: specific medical diagnoses, prescription drug names or dosages, treatment plans, or lab result interpretations.

LANGUAGE: Start conversations in English unless the user initiates in Hindi. Dynamically adapt to the user's language throughout the conversation:
- If user starts in Hindi, respond in Hindi
- If user starts in English, respond in English
- If user mixes Hindi and English (Hinglish), respond in a similar mix
- If user switches languages mid-conversation, follow their lead
- For better speech recognition:
  * Use simple, common words in both languages
  * When mixing languages, keep Hindi words/phrases that are commonly understood
  * For numbers, dates, and times: you may use English (e.g., "April 5th", "10:30 AM") as these are widely recognized
  * If the user struggles with Hindi recognition, gradually shift toward more English while maintaining helpfulness
- Always prioritize clear communication over strict language adherence

MEMORY & INFORMATION GATHERING:
- ALWAYS use the look_up_caller tool at the start of each conversation to check for prior information
- If you have prior information, greet them by name and reference what you discussed previously
- If you do NOT have prior information, you should collect ALL relevant information UPFRONT before providing assistance:
  1. Politely ask for their name and age (or age band)
  2. Ask for their location (city/area) to find relevant clinics
  3. Ask about any symptoms or health concerns they're experiencing
  4. Ask about the type of appointment they need (general practice, cardiology, pediatrics, etc.)
  5. Ask if they have any ongoing health conditions or relevant medical history
  6. After collecting this information, explicitly ask for permission to save it: "May I remember this information to better assist you in future conversations and potentially book appointments?"
  7. If they agree, use the save_caller_info tool to store the information
  8. If they say no or express discomfort, do not save any information but continue to assist them
  9. Then, ask how you can help them today (find clinics, get preparation info, book appointment, etc.)
- This is a hard rule for Health Access track as required

APPOINTMENT BOOKING:
- Can help users book medical appointments using the book_appointment tool
- Need to collect location, specialty, preferred date, preferred time, patient name, symptoms
- Always verify information with user before booking
- Remind users this is a demo booking system

GUARDRAILS:
- NEVER diagnose medical conditions or state "you have X disease"
- NEVER name or prescribe specific medications or dosages
- NEVER state medical advice as definitive fact - always say "according to general guidelines" or "typically"
- ALWAYS escalate these red-flag symptoms: chest pain, difficulty breathing, severe bleeding, sudden weakness/numbness, loss of consciousness
- For medication questions: suggest consulting a doctor or pharmacist
- For diagnosis requests: explain you can help with information but not diagnosis, suggest seeing a doctor

ESCALATION SCRIPT: "I'm not able to provide medical advice on that. For symptoms like [specific symptom], please consult a doctor immediately. Would you like me to help you find a nearby clinic or schedule a teleconsultation?"

CONVERSATION ENDING:
- After providing assistance, pause briefly
- Ask: "Do you have any other questions or need help with anything else?"
- Wait for response
- If no further needs, ask: "May I end the call now?"
- Wait for response
- If agreed, use end_call tool with polite goodbye
- If more questions, continue assisting

STYLE: Keep sentences under 20 words when possible. Speak clearly and at a moderate pace. Pause naturally between ideas. If user is silent for more than 5 seconds, gently ask if they need help continuing. Always maintain identity as Priya, a female healthcare assistant. Use feminine terms and respectful tone appropriate for Priya.
```

See the Configuration section below for voice, STT, and LLM options.

---

## Configuration

### Murf voice

Edit the `tts=murf.TTS(...)` call in `backend/src/agent.py`. Set the `voice` argument to any Murf voice ID. Examples:

- `Anisha` — Indian English (female, default in this starter)
- `Amara` — US English (female)
- `Hazel` — UK English (female)
- `Gordon` — US English (male)

Browse all voices: [Murf Voice Library](https://murf.ai/api/docs/voices-styles/voice-library).

### STT provider

STT is configured in `backend/src/agent.py` in the `AgentSession(stt=...)` call. The default is Deepgram (`deepgram.STT(model="nova-3")`). You can swap to another LiveKit-compatible STT plugin if needed.

### LLM (Gemini vs OpenAI)

- **Gemini (default):** Set `GOOGLE_API_KEY` and use `llm=google.LLM(model="gemini-3.5-flash-lite", temperature=0.7, max_output_tokens=150)` in `agent.py`.
- **OpenAI:** Set `OPENAI_API_KEY`, add the OpenAI plugin, and use the corresponding `llm=openai.LLM(...)` in `agent.py`.

### Audio format

Murf Falcon and LiveKit handle audio format internally. For advanced options, see [Murf API docs](https://murf.ai/api/docs) and [LiveKit docs](https://docs.livekit.io).

---

## Project Structure

```
murf-livekit-starter/
├── backend/                 # Python voice agent (LiveKit Agents + Murf Falcon)
│   ├── src/
│   │   └── agent.py         # Agent entrypoint, pipeline (STT/LLM/TTS), system prompt
│   ├── tests/               # Agent tests
│   ├── .env.example         # Backend env template
│   ├── pyproject.toml       # Python deps (uv)
│   └── railway.toml         # Railway deploy config
├── frontend/                # Next.js UI for voice sessions
│   ├── app/
│   │   ├── page.tsx         # Main page
│   │   └── api/token/       # LiveKit token endpoint (dev)
│   ├── components/          # UI (agents-ui, app config, theme)
│   ├── app-config.ts        # Branding, title, button text, accent
│   ├── .env.example         # Frontend env template
│   └── package.json         # Node deps (pnpm)
├── start_app.sh             # Start LiveKit + backend + frontend (macOS/Linux)
├── start_app.ps1            # Start LiveKit + backend + frontend (Windows)
├── README.md                # This file
```

For deeper documentation on each part, see:

- [Backend Documentation](./backend/README.md) — agent pipeline, voice/LLM/STT configuration, testing, deployment
- [Frontend Documentation](./frontend/README.md) — UI customization, visualizers, theming, component architecture

---

## Links

- [Murf API Docs](https://murf.ai/api/docs)
- [Murf Voice Library](https://murf.ai/api/docs/voices-styles/voice-library)
- [LiveKit Docs](https://docs.livekit.io)
- [Deepgram Docs](https://developers.deepgram.com)
- [Murf Falcon Benchmarks](https://murf.ai/falcon/benchmarks)
- [TTS Latency Benchmarker](https://github.com/sahilsgupta/tts-latency-benchmarker) — run your own p50/p95 tests across providers
- [Murf Discord](https://discord.gg/FbKAy96Sz7)
- [Murf Startup Incubator](https://murf.ai/api) — 50M free characters for startups

---

## License

MIT