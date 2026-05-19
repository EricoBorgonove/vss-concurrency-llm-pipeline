# Pipeline VSS-LLM

Pipeline experimental para verificar vulnerabilidades concorrentes em programas C,
coletar evidências de ferramentas de análise e preparar uma etapa futura de reparo
assistido por LLM.

O repositório está sendo construído incrementalmente. A integração com AFL++,
AddressSanitizer, ThreadSanitizer e LLM ainda será adicionada em etapas futuras.

## Objetivo

Desenvolver um pipeline reprodutível para:

- organizar benchmarks C com vulnerabilidades controladas;
- executar ferramentas de verificação e sanitizers;
- salvar logs e artefatos em `outputs/`;
- consolidar resultados em `reports/`;
- futuramente enviar evidências para uma LLM sugerir correções preliminares;
- validar as correções novamente com ESBMC e sanitizers.

## Estrutura do projeto

```text
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
│   ├── llm/
│   └── pipeline/
├── reports/ (relatórios consolidados)
├── scripts/ (scripts de automação Python)
├── run_pipeline.py (orquestrador)
├── requirements.txt
├── .gitignore
└── README.md
```

## Estado atual

- Estrutura inicial criada.
- Diretórios vazios preservados com `.gitkeep`.
- `scripts/run_esbmc.py` executa o ESBMC sobre um arquivo `.c` e salva logs em
  `outputs/esbmc/`.
- `scripts/run_asan.py` compila e executa um benchmark C com AddressSanitizer,
  salvando logs em `outputs/asan/`.
- `scripts/run_tsan.py` compila e executa um benchmark C com ThreadSanitizer,
  salvando logs em `outputs/tsan/`.
- `scripts/run_afl.py` compila um benchmark com AFL++ e prepara uma campanha
  curta, salvando logs em `outputs/afl/`.
- `run_pipeline.py` executa uma rodada básica das ferramentas implementadas e
  salva um resumo em `outputs/pipeline/`.
- `scripts/generate_report.py` consolida logs em `reports/results.csv` e inclui
  uma classificação simples dos resultados.
- Há benchmarks mínimos para assertion violation, buffer overflow, data race e
  deadlock em `benchmarks/`.
- Os demais scripts Python ainda são placeholders com tratamento básico de erro.
- Nenhuma dependência externa Python é necessária nesta etapa.

## Como preparar o ambiente

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

No macOS, se usar `zsh`, o comando de ativação acima continua válido.

## Como executar nesta etapa

Para executar o ESBMC sobre o benchmark mínimo:

```bash
python3 scripts/run_esbmc.py benchmarks/assertion_violation/simple_assert_fail.c
```

O script também gera um log em `outputs/esbmc/` quando o ESBMC não está instalado,
registrando o erro de ambiente de forma reprodutível.

Para executar AddressSanitizer sobre o benchmark de buffer overflow:

```bash
python3 scripts/run_asan.py benchmarks/memory_corruption/simple_buffer_overflow.c
```

Para executar ThreadSanitizer sobre o benchmark de data race:

```bash
python3 scripts/run_tsan.py benchmarks/data_race/simple_data_race.c
```

Para preparar uma execução curta com AFL++:

```bash
python3 scripts/run_afl.py benchmarks/memory_corruption/simple_buffer_overflow.c
```

Para executar a rodada básica do pipeline:

```bash
python3 run_pipeline.py
```

Para gerar o relatório CSV a partir dos logs:

```bash
python3 scripts/generate_report.py
```

## Benchmarks iniciais

- `benchmarks/assertion_violation/simple_assert_fail.c`
- `benchmarks/memory_corruption/simple_buffer_overflow.c`
- `benchmarks/data_race/simple_data_race.c`
- `benchmarks/deadlock/simple_deadlock.c`

## Próxima etapa planejada

Criar etapa simulada de LLM em `scripts/run_llm_repair.py`, sem chamar API
externa ainda.
