# Geospatial AI Co-Scientist

An AI-powered research assistant for geospatial science, remote sensing, and GIS research. Built on a multi-agent architecture inspired by Google's AI Co-Scientist approach.

## Overview

The Geospatial AI Co-Scientist assists researchers with:

- **Literature Review**: Searching and summarizing relevant remote sensing and GIS literature
- **Hypothesis Generation**: Proposing novel, plausible hypotheses in geospatial science
- **Experiment Design**: Outlining how to test hypotheses with data requirements and methodologies
- **Data Analysis**: Assisting in analyzing geospatial data to validate hypotheses

## Architecture

The system uses a multi-agent architecture with specialized agents:

| Agent | Role |
|-------|------|
| **Supervisor** | Orchestrates workflow and coordinates agents |
| **Generation** | Creates initial hypotheses based on research goals |
| **Reflection** | Reviews hypotheses for quality and novelty |
| **Ranking** | Prioritizes hypotheses using Elo rating system |
| **Proximity** | Analyzes hypothesis similarity and diversity |
| **Evolution** | Refines and improves top hypotheses |
| **Meta-Review** | Synthesizes feedback and compiles final outputs |
| **Experiment Design** | Creates testing plans for hypotheses |

## Installation

### Prerequisites

- Python 3.10+
- OpenAI API key (or Anthropic API key)

### Install from source

```bash
git clone https://github.com/georeason-labs/geospatial-co-scientist.git
cd geospatial-co-scientist
pip install -e ".[dev]"
```

### Configure environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

## Quick Start

### Command Line Interface

```bash
# Run a research session
geo-scientist research "How can satellite imagery detect urban heat islands?"

# Interactive mode with human-in-the-loop
geo-scientist research "Detect deforestation in Amazon" --interactive

# Output to file
geo-scientist research "Monitor coastal erosion" --output results.md
```

### Python API

```python
import asyncio
from geospatial_co_scientist import GeospatialCoScientist

async def main():
    scientist = GeospatialCoScientist()

    result = await scientist.research(
        question="How can satellite thermal imagery detect urban heat islands?",
        domain="remote_sensing",
        constraints=["Use freely available data"],
        keywords=["thermal", "Landsat", "NDVI"]
    )

    # Get markdown report
    print(result.to_markdown())

    # Access specific components
    for hyp in result.hypotheses:
        print(f"- {hyp.title}: {hyp.statement}")

asyncio.run(main())
```

### REST API

Start the server:

```bash
uvicorn geospatial_co_scientist.ui.api:app --host 0.0.0.0 --port 8000
```

Start a research session:

```bash
curl -X POST http://localhost:8000/api/research \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How can satellite imagery detect urban heat islands?",
    "domain": "remote_sensing",
    "max_iterations": 3
  }'
```

Check status:

```bash
curl http://localhost:8000/api/research/{session_id}/status
```

## Docker

```bash
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f co-scientist
```

## Configuration

Key configuration options (via environment variables):

| Variable | Description | Default |
|----------|-------------|---------|
| `GEO_SCIENTIST_LLM_PROVIDER` | LLM provider (openai, anthropic) | openai |
| `GEO_SCIENTIST_MAX_ITERATIONS` | Max generate-refine iterations | 3 |
| `GEO_SCIENTIST_HYPOTHESES_PER_ITERATION` | Hypotheses per iteration | 5 |
| `GEO_SCIENTIST_TOP_HYPOTHESES_TO_EVOLVE` | Top hypotheses to evolve | 3 |

See `.env.example` for all options.

## Workflow

1. **Initialize**: Parse research goal and perform literature review
2. **Generate**: Create initial hypotheses grounded in literature
3. **Reflect**: Review hypotheses for quality and novelty
4. **Rank**: Prioritize using Elo-based tournament ranking
5. **Evolve**: Refine top hypotheses based on feedback
6. **Design**: Create experiment plans for top hypotheses
7. **Synthesize**: Compile final research overview

The workflow iterates through generate-reflect-rank-evolve cycles until convergence or max iterations.

## Project Structure

```
geospatial-co-scientist/
├── src/geospatial_co_scientist/
│   ├── agents/           # Specialized AI agents
│   ├── models/           # Data models
│   ├── orchestration/    # LangGraph workflow
│   ├── tools/            # Literature search, geospatial tools
│   ├── ui/               # FastAPI web interface
│   ├── config.py         # Configuration
│   └── cli.py            # Command-line interface
├── tests/                # Test suite
├── config/               # Configuration files
├── docs/                 # Documentation
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

## Development

### Run tests

```bash
pytest tests/ -v
```

### Code formatting

```bash
black src/ tests/
ruff check src/ tests/
```

### Type checking

```bash
mypy src/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- Inspired by [Google's AI Co-Scientist](https://research.google/blog/accelerating-scientific-breakthroughs-with-an-ai-co-scientist/)
- Built with [LangGraph](https://www.langchain.com/langgraph) and [LangChain](https://www.langchain.com/)
