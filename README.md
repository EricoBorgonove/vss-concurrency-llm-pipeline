# Pipeline VSS-LLM

Pipeline experimental para verificar vulnerabilidades concorrentes em programas C,
coletar evidências de ferramentas de análise e preparar uma etapa futura de reparo
assistido por LLM.

O repositório está sendo construído incrementalmente. A base atual já integra
ESBMC, AFL++, AddressSanitizer, ThreadSanitizer, detecção simples de deadlock por
timeout, geração de relatórios e uma etapa simulada de reparo por LLM.

## Objetivo

Desenvolver um pipeline reprodutível para:

- organizar benchmarks C com vulnerabilidades controladas;
- executar ferramentas de verificação e sanitizers;
- salvar logs e artefatos em `outputs/`;
- consolidar resultados em `reports/`;
- futuramente enviar evidências para uma LLM sugerir correções preliminares;
- validar as correções novamente com as ferramentas disponíveis no pipeline.

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
│   ├── deadlock/
│   ├── environment/
│   ├── llm/
│   └── pipeline/
├── reports/ (relatórios consolidados)
├── scripts/ (scripts de automação Python)
├── tests/ (testes automatizados leves)
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
- `scripts/run_deadlock.py` compila e executa um benchmark C usando timeout como
  evidência de possível deadlock, salvando logs em `outputs/deadlock/`.
- `scripts/run_afl.py` compila um benchmark com AFL++ e prepara uma campanha
  curta, salvando logs em `outputs/afl/`.
- `run_pipeline.py` descobre benchmarks `.c` automaticamente nas categorias
  suportadas, registra diagnóstico do ambiente, executa as ferramentas
  implementadas, gera relatórios CSV e salva um resumo em `outputs/pipeline/`.
- `scripts/generate_report.py` consolida logs em `reports/results.csv`, inclui
  data de execução, classificação simples dos resultados e gera
  `reports/summary.csv`, com intervalo de datas e opção para considerar apenas
  os logs mais recentes.
- `scripts/run_llm_repair.py` gera uma sugestão simulada de reparo a partir de
  um log, sem chamar API externa.
- `scripts/validate_llm_repair.py` valida de forma simulada uma sugestão gerada,
  e pode reexecutar uma ferramenta sobre um benchmark reparado controlado.
- `scripts/check_environment.py` registra um diagnóstico básico das ferramentas
  e runtimes disponíveis em `outputs/environment/`.
- A base possui 48 benchmarks C, incluindo casos mínimos, casos mais complexos,
  exemplos vulneráveis e exemplos corretos.
- Os benchmarks possuem comentários iniciais indicando se são casos com erro ou
  casos corretos.
- Os scripts Python possuem tratamento básico de erros e geram saídas em
  `outputs/` ou `reports/`.
- A suíte de testes cobre geração de relatórios, descoberta de benchmarks,
  formatação do resumo, helpers dos executores e validação simulada de reparos.
- Nenhuma dependência externa Python é necessária atualmente.

## Como preparar o ambiente

Os scripts Python usam apenas a biblioteca padrão atualmente. O
`requirements.txt` documenta essa decisão e pode ser instalado sem adicionar
pacotes externos.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

No macOS, se usar `zsh`, o comando de ativação acima continua válido.

As ferramentas de análise são dependências de sistema. O pipeline usa
`clang/gcc`, ESBMC e AFL++. Para AFL++ no macOS com Homebrew:

```bash
brew install afl++
```

O ESBMC deve estar instalado e disponível no `PATH`. Depois de preparar o
ambiente, registre o diagnóstico:

```bash
python3 scripts/check_environment.py
```

## Como executar

O comando principal é:

```bash
python3 run_pipeline.py
```

Ele registra o diagnóstico do ambiente, executa os benchmarks descobertos
automaticamente, atualiza `reports/results.csv` e `reports/summary.csv`, salva um
resumo textual em `outputs/pipeline/` e exibe uma tabela consolidada no terminal.

Os comandos abaixo continuam disponíveis para executar etapas individuais.

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

Para executar a observação de deadlock por timeout:

```bash
python3 scripts/run_deadlock.py benchmarks/deadlock/simple_deadlock.c
```

Para preparar uma execução curta com AFL++:

```bash
python3 scripts/run_afl.py benchmarks/memory_corruption/simple_buffer_overflow.c
```

O `reports/results.csv` inclui `execution_date`, `expected_behavior` e
`expectation_match`. O `reports/summary.csv` inclui essas mesmas dimensões,
além de `first_execution_date` e `latest_execution_date` para cada combinação de
ferramenta, expectativa e classificação.

Novos arquivos `.c` adicionados em `benchmarks/assertion_violation/`,
`benchmarks/memory_corruption/`, `benchmarks/data_race/` e
`benchmarks/deadlock/` entram automaticamente na rodada. Arquivos terminados em
`_fixed.c` ou `_pass.c` são ignorados pelo pipeline principal, pois ficam
reservados para validação de reparos e controles positivos.

Para gerar os relatórios CSV a partir dos logs:

```bash
python3 scripts/generate_report.py
```

Para gerar relatórios filtrando ferramentas:

```bash
python3 scripts/generate_report.py --tools asan,tsan
```

Para gerar relatórios usando apenas o log mais recente por ferramenta e
benchmark:

```bash
python3 scripts/generate_report.py --latest-only
```

Para executar os testes automatizados leves:

```bash
python3 -m unittest
```

Atualmente a suíte cobre testes rápidos sem chamar ferramentas externas pesadas,
usando funções puras, arquivos temporários e mocks quando necessário.

Para registrar diagnóstico do ambiente:

```bash
python3 scripts/check_environment.py
```

Para gerar uma sugestão simulada de reparo a partir de um log:

```bash
python3 scripts/run_llm_repair.py outputs/asan/<arquivo_de_log>.log
```

Para validar uma sugestão simulada de reparo:

```bash
python3 scripts/validate_llm_repair.py outputs/llm/<arquivo_de_reparo>.txt
```

Para validar um benchmark reparado controlado com ASAN:

```bash
python3 scripts/validate_llm_repair.py outputs/llm/<arquivo_de_reparo>.txt --fixed-benchmark benchmarks/memory_corruption/simple_buffer_overflow_fixed.c --tool asan
```

Para validar um benchmark reparado controlado com TSAN:

```bash
python3 scripts/validate_llm_repair.py outputs/llm/<arquivo_de_reparo>.txt --fixed-benchmark benchmarks/data_race/simple_data_race_fixed.c --tool tsan
```

Para validar um benchmark reparado controlado com ESBMC:

```bash
python3 scripts/validate_llm_repair.py outputs/llm/<arquivo_de_reparo>.txt --fixed-benchmark benchmarks/assertion_violation/simple_assert_pass.c --tool esbmc
```

Para validar um benchmark reparado controlado de deadlock:

```bash
python3 scripts/validate_llm_repair.py outputs/llm/<arquivo_de_reparo>.txt --fixed-benchmark benchmarks/deadlock/simple_deadlock_fixed.c --tool deadlock
```

## Benchmarks

A base atual possui exemplos em quatro categorias:

- `benchmarks/assertion_violation/`
- `benchmarks/memory_corruption/`
- `benchmarks/data_race/`
- `benchmarks/deadlock/`

Os benchmarks incluem casos mínimos, casos mais complexos, exemplos com erro e
exemplos corretos nomeados com o sufixo `_safe.c`. Arquivos terminados em
`_fixed.c` ou `_pass.c` ficam reservados para validação de reparos e controles e
não entram na rodada principal.

Nos relatórios, os sufixos são interpretados assim:

- `_error.c`: comportamento esperado `vulneravel`;
- `_safe.c`, `_fixed.c` e `_pass.c`: comportamento esperado `correto`;
- demais nomes: comportamento esperado `nao informado`.

A coluna `expectation_match` indica se o resultado observado ficou `conforme
esperado`, `divergente`, `inconclusivo` ou `nao avaliado`.

## Próxima etapa planejada

Gerar um relatório em formato Markdown ou HTML para facilitar leitura e
apresentação dos resultados.
