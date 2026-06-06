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
│   ├── deadlock/
│   ├── environment/
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
- Há benchmarks mínimos para assertion violation, buffer overflow, data race e
  deadlock em `benchmarks/`.
- Cada categoria inicial recebeu exemplos adicionais para ampliar a base de
  experimentos controlados.
- Os demais scripts Python ainda são placeholders com tratamento básico de erro.
- Nenhuma dependência externa Python é necessária nesta etapa.

## Como preparar o ambiente

Os scripts Python usam apenas a biblioteca padrão nesta etapa. O
`requirements.txt` documenta essa decisão e pode ser instalado sem adicionar
pacotes externos.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

No macOS, se usar `zsh`, o comando de ativação acima continua válido.

As ferramentas de análise são dependências de sistema. Para AFL++ no macOS com
Homebrew:

```bash
brew install afl++
```

Depois de preparar o ambiente, registre o diagnóstico:

```bash
python3 scripts/check_environment.py
```

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

Para executar a observação de deadlock por timeout:

```bash
python3 scripts/run_deadlock.py benchmarks/deadlock/simple_deadlock.c
```

Para preparar uma execução curta com AFL++:

```bash
python3 scripts/run_afl.py benchmarks/memory_corruption/simple_buffer_overflow.c
```

Para executar uma rodada completa do pipeline:

```bash
python3 run_pipeline.py
```

Esse comando registra o diagnóstico do ambiente, executa os benchmarks
descobertos automaticamente e atualiza `reports/results.csv` e
`reports/summary.csv` usando apenas os logs mais recentes por ferramenta e
benchmark. Ao final, o conteúdo de `reports/summary.csv` também é exibido no
terminal.

O `reports/results.csv` inclui a coluna `execution_date`. O
`reports/summary.csv` inclui `first_execution_date` e `latest_execution_date`
para cada combinação de ferramenta e classificação.

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

Para registrar diagnóstico do ambiente:

```bash
python3 scripts/check_environment.py
```

Para gerar uma sugestão simulada de reparo a partir de um log:

```bash
python3 scripts/run_llm_repair.py outputs/asan/simple_buffer_overflow_20260519-172441.log
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

## Benchmarks iniciais

- `benchmarks/assertion_violation/simple_assert_fail.c`
- `benchmarks/assertion_violation/simple_assert_pass.c`
- `benchmarks/assertion_violation/assert_array_index.c`
- `benchmarks/assertion_violation/assert_counter_overflow.c`
- `benchmarks/assertion_violation/assert_negative_value.c`
- `benchmarks/assertion_violation/assert_state_transition.c`
- `benchmarks/assertion_violation/assert_sum_limit.c`
- `benchmarks/memory_corruption/simple_buffer_overflow.c`
- `benchmarks/memory_corruption/simple_buffer_overflow_fixed.c`
- `benchmarks/memory_corruption/heap_write_overflow.c`
- `benchmarks/memory_corruption/out_of_bounds_read.c`
- `benchmarks/memory_corruption/stack_write_overflow.c`
- `benchmarks/memory_corruption/string_copy_overflow.c`
- `benchmarks/memory_corruption/use_after_free.c`
- `benchmarks/data_race/simple_data_race.c`
- `benchmarks/data_race/simple_data_race_fixed.c`
- `benchmarks/data_race/race_array_cell.c`
- `benchmarks/data_race/race_increment_loop.c`
- `benchmarks/data_race/race_read_write.c`
- `benchmarks/data_race/race_shared_flag.c`
- `benchmarks/data_race/race_struct_field.c`
- `benchmarks/deadlock/simple_deadlock.c`
- `benchmarks/deadlock/simple_deadlock_fixed.c`
- `benchmarks/deadlock/deadlock_conditional_order.c`
- `benchmarks/deadlock/deadlock_resource_pair.c`
- `benchmarks/deadlock/deadlock_self_lock.c`
- `benchmarks/deadlock/deadlock_three_locks_cycle.c`
- `benchmarks/deadlock/deadlock_two_locks_reverse.c`

## Próxima etapa planejada

Ampliar os testes automatizados para validadores e executores.
