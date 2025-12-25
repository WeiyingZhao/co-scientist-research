# UI Design Plan: Geospatial AI Co-Scientist

## 1. Design Concept: "Orbital Command"
**Esthetic**: Premium, Dark Mode, Scientific, Data-Dense but Clean.
**Inspiration**: SpaceX Mission Control, Sci-Fi HUDs (The Expanse), Palantir Gotham.
**Typography**: Inter (UI), JetBrains Mono (Code/Data), Orbitron (Headers - sparing use).
**Palette**:
- **Background**: Deep Space Blue/Black (`#0B0E14`)
- **Surface**: Translucent Glass Panels (`rgba(30, 41, 59, 0.7)`) with blur (`backdrop-filter`)
- **Accents**:
    - *Generation Agent*: Cyan (`#06B6D4`)
    - *Reflection Agent*: Amber (`#F59E0B`)
    - *Ranking Agent*: Purple (`#8B5CF6`)
    - *Error/Critical*: Rose (`#F43F5E`)
    - *Success*: Emerald (`#10B981`)

## 2. Technology Stack
To support real-time updates and complex visualizations:

- **Frontend**:
    - **Framework**: Next.js 14 (App Router)
    - **Styling**: Tailwind CSS + Shadcn UI (Customized)
    - **Animation**: Framer Motion (layout transitions)
    - **Visualization**: React Flow (Agent Graph), Recharts (Elo Scores)
    - **Markdown**: `react-markdown` with GFM support

- **Backend**:
    - **API**: FastAPI (Python) - Wraps `GeospatialCoScientist` classes.
    - **Communication**: Server-Sent Events (SSE) for real-time agent status streaming.
    - **Database**: SQLite (local) or Postgres (production) for session state persistence.

## 3. Core User Flows & Screens

### A. Launchpad (Home / New Mission)
*Goal: Inspire the user to start research.*

- **Hero Section**: Centered, large input field: *"Enter your research goal..."* (e.g., "Detecting urban heat islands in Mumbai using Sentinel-2").
- **Configuration Drawer**: Collapsible panel for advanced settings:
    - Domain Selection (Dropdown)
    - Max Iterations (Slider: 1-10)
    - Model Selection (GPT-4 / Claude 3)
- **Recent Missions**: Grid of cards showing previous sessions with status status indicators (e.g., "In Progress", "Completed", "Review Needed").

### B. Mission Control (Active Session)
*Goal: Visualize the "Co-Scientist" thinking process.*

**Layout**: Three-Pane "Holy Grail"
1.  **Left: The Narrative (Stream)**
    - A linear chat-like interface.
    - Shows System messages, Agent thoughts (collapsed by default), and Key Decisions.
    - **Human-in-the-Loop**: When the system pauses for feedback, the input box appears here.

2.  **Center: The Neural Graph (Live viz)**
    - A dynamic node-graph using **React Flow**.
    - Nodes represent Agents (`Generation`, `Reflection`, `Poximity`).
    - **Animation**: Active nodes pulse; edges flow with "data packets" showing information transfer.
    - Clicking a node shows its detailed context/state in a popover.

3.  **Right: The Artifact (Live Draft)**
    - Real-time preview of the `ResearchOverview`.
    - Updates as hypotheses are generated and ranked.
    - **Tabs**:
        - *Hypotheses*: Ranked list cards.
        - *Experiments*: Design plans.
        - *Literature*: Summary of found papers.

### C. Discovery Deck (Results & Deep Dive)
*Goal: Review and Export final findings.*

- **Hypothesis Cards**: High-fidelity cards showing:
    - Title & Statement.
    - **Elo Score Badge**: Visual gauge of the hypothesis strength.
    - **Novelty/Feasibility Radar Chart**: Small visualization of scores.
- **Experiment Blueprint**:
    - Detailed view for selected experiments.
    - "Copy Code" button for generated Python/GEE scripts.
- **Export**:
    - "Download Report" (Markdown/PDF).
    - "Export to Jupyter" (Creates a .ipynb starter notebook).

## 4. Component Details (Design System)

### Atoms
- **GlassCard**: `bg-slate-900/50 backdrop-blur-md border border-white/10 rounded-xl shadow-2xl`
- **NeonButton**: `bg-cyan-500/10 text-cyan-400 border border-cyan-500/50 hover:bg-cyan-500/20 hover:shadow-[0_0_20px_rgba(6,182,212,0.3)] transition-all`
- **StatusDot**: Pulsing CSS animation for active agents.

### Molecules
- **AgentBadge**: Icon + Label + Status Color (e.g., 🤖 Generation [Active]).
- **CitationPill**: Small interactive chip linking to Semantic Scholar/DOI.

## 5. Implementation Roadmap
1.  **API Layer**: Create `src/ui/server/main.py` (FastAPI) to expose `GeospatialCoScientist` via REST/SSE.
2.  **Frontend Shell**: Initialize Next.js project.
3.  **Graph Viz**: Implement React Flow component mapped to `orchestration/nodes.py`.
4.  **Real-time Link**: Connect SSE to Frontend state management (Zustand).
5.  **Polish**: Apply the "Orbital" aesthetics.
