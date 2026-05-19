# Pipeline VSS-LLM (experimental)

Objetivo

Este repositório contém um pipeline experimental para detectar, interpretar e (futuramente) reparar vulnerabilidades concorrentes em programas C. A ideia é integrar ferramentas como ESBMC, AFL++, AddressSanitizer e ThreadSanitizer, com uma etapa posterior que usa uma LLM para sugerir correções.

Estrutura do projeto

pipeline-vss-llm/
├── benchmarks/ (benchmarks C categorizados)
│   ├── data_race/
│   ├── deadlock/
│   ├── memory_corruption/
│   └── assertion_violation/
├── seeds/ (seeds para AFL++)
├── outputs/ (logs e artefatos gerados pelas ferramentas)
│   ├── esbmc/
│   ├── afl/
│   ├── asan/
│   ├── tsan/
│   └── llm/
├── reports/ (relatórios consolidados)
├── scripts/ (scripts de automação Python)
├── run_pipeline.py (orquestrador)
├── requirements.txt
├── .gitignore
└── README.md

Primeira etapa

Criei a estrutura inicial do projeto com arquivos e placeholders mínimos. Próxima etapa planejada: implementar `scripts/run_esbmc.py` para executar ESBMC sobre um benchmark de exemplo e gravar logs em `outputs/esbmc/`.

Como usar

1. Navegue até a pasta do projeto e crie um ambiente Python (opcional):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Aguardar a próxima etapa para começar a executar ferramentas.

Contribuição

Siga as regras do desenvolvimento incremental no arquivo de issue correspondente. Após revisar, peça "próxima etapa" para eu implementar a automação inicial do ESBMC.
