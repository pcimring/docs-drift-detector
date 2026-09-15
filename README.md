# docs-drift-detector

Portfolio demonstration of docs-drift detection, code-sample testing, and
AI-assisted update drafting — built config-driven against LangChain first,
Arize Phoenix second. See the design spec for full context.

## Local dev

    docker compose up -d
    pip install -r requirements.txt
    cp .env.example .env
    pytest

## Run discovery manually

    python -m discovery.main langchain /path/to/local/langchain-ai-docs-checkout
