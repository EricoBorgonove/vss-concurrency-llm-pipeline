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
│   ├── metadata.csv (metadados auditáveis dos benchmarks)
│   ├── data_race/
│   ├── deadlock/
│   ├── memory_corruption/
│   ├── assertion_violation/
│   └── random_tests/ (códigos exploratórios sem metadados)
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
├── pipeline_runner/ (módulos internos do orquestrador)
├── scripts/ (scripts de automação Python)
├── tests/ (testes automatizados leves)
├── Dockerfile
├── docker-compose.yml
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
  implementadas, gera relatórios CSV, registra métricas de execução e salva um
  resumo em `outputs/pipeline/`. A implementação interna fica dividida em
  módulos menores dentro de `pipeline_runner/`.
- `scripts/generate_report.py` consolida logs em `reports/results.csv`, inclui
  data de execução, classificação simples dos resultados e gera
  `reports/summary.csv` e `reports/report.html`, com intervalo de datas e opção
  para considerar apenas os logs mais recentes.
- `scripts/run_llm_repair.py` gera uma sugestão simulada de reparo a partir de
  um log, sem chamar API externa.
- `scripts/validate_llm_repair.py` valida de forma simulada uma sugestão gerada,
  e pode reexecutar uma ferramenta sobre um benchmark reparado controlado.
- `scripts/check_environment.py` registra um diagnóstico básico das ferramentas
  e runtimes disponíveis em `outputs/environment/`.
- A base controlada possui 48 benchmarks C, incluindo casos mínimos, casos mais
  complexos, exemplos vulneráveis e exemplos corretos.
- `benchmarks/random_tests/` possui 5 códigos exploratórios sem metadados para
  exercitar a inferência automática de ferramentas a partir do conteúdo do
  arquivo C.
- Os benchmarks possuem comentários iniciais indicando se são casos com erro ou
  casos corretos.
- `benchmarks/metadata.csv` registra, para cada benchmark, identificador,
  categoria, caminho, comportamento esperado, expectativa por ferramenta,
  descrição e participação na rodada principal.
- Os scripts Python possuem tratamento básico de erros e geram saídas em
  `outputs/` ou `reports/`.
- A suíte de testes cobre geração de relatórios, descoberta de benchmarks,
  formatação do resumo, helpers dos executores e validação simulada de reparos.
- Nenhuma dependência externa Python é necessária atualmente.

## Como preparar o ambiente reprodutivel

Para resultados de pesquisa, a forma recomendada de execucao e via Docker. O
ambiente Docker usa Ubuntu 24.04 em `linux/amd64`, instala `clang/LLVM`, os
runtimes dos sanitizers, `gcc`, AFL++ e ESBMC, e mantem as variaveis necessarias
para campanhas curtas do AFL++.
A arquitetura `linux/amd64` e usada de proposito porque o pacote do ESBMC no PPA
oficial nao esta disponivel para todas as arquiteturas, como `arm64`.
O `docker-compose.yml` tambem usa `seccomp=unconfined`, necessario para evitar
bloqueio de chamadas usadas pelo ThreadSanitizer dentro do container.

Para construir a imagem:

```bash
docker compose build
```

Para executar a rodada completa:

```bash
docker compose run --rm pipeline
```

Para executar comandos especificos dentro do mesmo ambiente:

```bash
docker compose run --rm pipeline python3 scripts/check_environment.py
docker compose run --rm pipeline python3 -m unittest
docker compose run --rm pipeline python3 scripts/generate_report.py --latest-only
```

Os diretorios do projeto sao montados em `/workspace`, entao `outputs/` e
`reports/` gerados dentro do container aparecem tambem na maquina local.
Em Docker Desktop sobre Apple Silicon, a imagem `linux/amd64` pode executar sob
emulacao. Nesse cenario, o TSAN pode nao observar as corridas mesmo quando a
compilacao funciona; nesses casos o resultado deve ser tratado como divergencia
experimental, nao como erro de execucao. Para avaliar TSAN com mais fidelidade,
prefira Linux `amd64` nativo ou o clang LLVM local descrito abaixo.

Em macOS/Apple Silicon, depois de uma rodada Docker, a etapa TSAN pode ser
refeita nativamente com Homebrew LLVM para substituir os logs emulados por logs
do runtime nativo:

```bash
for f in benchmarks/data_race/*.c benchmarks/random_tests/random_race_counter.c benchmarks/random_tests/random_deadlock_pair.c; do
  python3 scripts/run_tsan.py "$f" --compiler /opt/homebrew/opt/llvm/bin/clang || true
done
python3 scripts/generate_report.py --latest-only
```

## Como preparar o ambiente local

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
automaticamente, atualiza `reports/results.csv`, `reports/summary.csv` e
`reports/report.html`, gera métricas em `reports/benchmark_metrics.csv` e
`reports/category_metrics.csv`, salva um resumo textual em `outputs/pipeline/`
e exibe tabelas consolidadas no terminal.

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

No macOS, o executor de ASAN tambem prefere automaticamente o clang do LLVM
instalado via Homebrew, quando disponivel. Essa preferencia evita timeouts e
comportamentos inconsistentes observados com Apple clang em alguns runtimes de
sanitizer.

Para executar ThreadSanitizer sobre o benchmark de data race:

```bash
python3 scripts/run_tsan.py benchmarks/data_race/simple_data_race.c
```

No macOS, o executor de TSAN prefere automaticamente o clang do LLVM instalado
via Homebrew, quando disponivel em `/opt/homebrew/opt/llvm/bin/clang` ou
`/usr/local/opt/llvm/bin/clang`. Essa preferencia evita falsos negativos
causados por crashes do runtime TSAN observados com Apple clang, que apareciam
nos logs como `returncode: -11` sem relatorio `ThreadSanitizer`.

Para executar a observação de deadlock por timeout:

```bash
python3 scripts/run_deadlock.py benchmarks/deadlock/simple_deadlock.c
```

Para preparar uma execução curta com AFL++:

```bash
python3 scripts/run_afl.py benchmarks/memory_corruption/simple_buffer_overflow.c
```

O executor do AFL++ usa `AFL_USE_ASAN=1` por padrão para transformar violações
de memória em crashes quando a campanha alcança o comportamento problemático.
Campanhas curtas que terminam sem crash são classificadas como `inconclusivo`,
pois ausência de crash em poucos segundos não prova ausência de vulnerabilidade.

O `reports/results.csv` inclui `execution_date`, `expected_behavior` e
`expectation_match`, além de `expected_tool_behavior` e
`tool_expectation_match`. O `reports/summary.csv` inclui essas mesmas dimensões,
além de `first_execution_date` e `latest_execution_date` para cada combinação de
ferramenta, expectativa e classificação. O `reports/report.html` apresenta um
resumo, métricas por categoria, métricas por benchmark e resultados detalhados
em formato mais amigável para leitura.

Quando `python3 run_pipeline.py` é executado, o projeto também gera:

- `reports/benchmark_metrics.csv`: duração de cada tarefa por benchmark,
  categoria, ferramenta e código de retorno;
- `reports/category_metrics.csv`: quantidade de benchmarks executados,
  quantidade de execuções e duração mínima, média, máxima e total por categoria.

Novos arquivos `.c` adicionados em `benchmarks/assertion_violation/`,
`benchmarks/memory_corruption/`, `benchmarks/data_race/` e
`benchmarks/deadlock/` devem ser registrados em `benchmarks/metadata.csv`. O
campo `include_in_pipeline` define se o arquivo entra na rodada principal. O
campo `expected_behavior` registra se o benchmark é `vulneravel` ou `correto`,
enquanto `expected_esbmc`, `expected_asan`, `expected_tsan`,
`expected_deadlock` e `expected_afl` registram a expectativa específica de cada
ferramenta, usando valores como `detectar`, `nao_detectar`, `inconclusivo` e
`nao_aplicavel`.

A descoberta da rodada principal usa esses campos `expected_*` para decidir
quais testes devem ser executados para cada benchmark. Uma ferramenta é
executada quando sua coluna possui uma expectativa aplicável, como `detectar`,
`nao_detectar` ou `inconclusivo`. Quando a coluna está como `nao_aplicavel`, a
ferramenta não é executada para aquele benchmark.

Para uso exploratório, também é possível colocar um arquivo `.c` sem registro em
`metadata.csv`, por exemplo em `benchmarks/random_tests/`. Nesse caso, o
pipeline lê o conteúdo do código e infere uma lista inicial de ferramentas:

- chamadas de `assert` ou `__ESBMC_assert`: ESBMC;
- uso de alocação, `free`, cópias inseguras ou escrita em vetor: ASAN;
- uso de entrada externa ou padrões de memória: AFL++;
- uso de `pthread`: TSAN;
- uso de `pthread_mutex_lock`: detector de deadlock por timeout.

Essa inferência serve para triagem automática. Para resultados de pesquisa, o
recomendado continua sendo registrar o caso em `benchmarks/metadata.csv`, pois
os metadados tornam explícitos o comportamento esperado e a expectativa por
ferramenta.

Os códigos exploratórios atuais em `benchmarks/random_tests/` exercitam essa
decisão automática:

- `random_assert_check.c`: seleciona ESBMC;
- `random_heap_use_after_free.c`: seleciona ASAN e AFL++;
- `random_race_counter.c`: seleciona TSAN;
- `random_deadlock_pair.c`: seleciona TSAN e detector de deadlock;
- `random_plain_program.c`: não seleciona ferramenta, pois não possui sinais
  suficientes para triagem automática.

Esses arquivos não entram em `benchmarks/metadata.csv` de propósito. Eles
servem para validar a capacidade da aplicação de escolher ferramentas para
códigos ainda não catalogados. Depois que `python3 run_pipeline.py` executa as
tarefas inferidas e gera logs em `outputs/`, eles passam a aparecer em
`reports/results.csv`, `reports/summary.csv` e `reports/report.html` na próxima
geração de relatório.

Os sufixos `_error.c`, `_safe.c`, `_fixed.c` e `_pass.c` permanecem como uma
convenção de leitura e como fallback para logs antigos, mas os relatórios e a
descoberta de benchmarks usam os metadados explícitos quando disponíveis.

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

Para escolher outro caminho para o relatório HTML:

```bash
python3 scripts/generate_report.py --html-output reports/meu_relatorio.html
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

## Etapa LLM simulada

A etapa de LLM ainda não integra uma API externa nem envia dados para nenhum
serviço. Ela é uma simulação determinística usada para exercitar o fluxo do
pipeline antes da integração real com uma LLM.

O script `scripts/run_llm_repair.py` lê um log de ferramenta e procura
marcadores simples, como `AddressSanitizer`, `ThreadSanitizer`, `data race`,
`deadlock`, `assert`, `VERIFICATION FAILED` ou `heap-buffer-overflow`. A partir
desses marcadores, ele classifica o tipo provável de problema e grava uma
sugestão textual genérica em `outputs/llm/`.

Essa etapa serve para testar a sequência experimental:

- coletar evidências nos logs;
- gerar uma sugestão preliminar de reparo;
- registrar a sugestão como artefato;
- validar um benchmark reparado controlado com as ferramentas já integradas.

Ela não modifica automaticamente os arquivos `.c` e não substitui uma análise
manual. A integração real com LLM fica para uma etapa futura.

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

A base controlada atual possui exemplos em quatro categorias:

- `benchmarks/assertion_violation/`
- `benchmarks/memory_corruption/`
- `benchmarks/data_race/`
- `benchmarks/deadlock/`

Além dessas categorias, `benchmarks/random_tests/` contém códigos exploratórios
sem metadados usados para validar a escolha automática de ferramentas. Essa
pasta é útil para triagem e demonstração, mas não substitui os metadados quando
o resultado precisa ser auditável.

Os benchmarks incluem casos mínimos, casos mais complexos, exemplos com erro e
exemplos corretos nomeados com o sufixo `_safe.c`. Arquivos terminados em
`_fixed.c` ou `_pass.c` normalmente ficam reservados para validação de reparos e
controles. A decisão efetiva de entrada na rodada principal fica registrada no
campo `include_in_pipeline` de `benchmarks/metadata.csv`.

Nos relatórios, o comportamento esperado vem primeiro de
`benchmarks/metadata.csv`:

- `expected_behavior`: comportamento esperado do benchmark;
- `expected_tool_behavior`: comportamento esperado da ferramenta aplicada;
- `expectation_match`: comparação entre resultado observado e benchmark;
- `tool_expectation_match`: comparação entre resultado observado e ferramenta.

Os sufixos `_error.c`, `_safe.c`, `_fixed.c` e `_pass.c` são usados apenas como
fallback para logs ou benchmarks ainda sem metadados.

## Próxima etapa planejada

Aprimorar o relatório HTML com filtros visuais por ferramenta, categoria e
classificação.
