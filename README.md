# Pipeline VSS-LLM

Este projeto organiza e executa um pipeline experimental para avaliar
vulnerabilidades em programas C. A ideia principal e reunir, em um unico fluxo,
benchmarks controlados, ferramentas de verificacao, sanitizers, logs e
relatorios, de forma que o experimento possa ser repetido e auditado.

O projeto nasceu no contexto de uma pesquisa de mestrado. Por isso, a prioridade
nao e apenas "rodar ferramentas", mas produzir evidencias que possam ser
explicadas: qual benchmark foi executado, qual comportamento era esperado, qual
ferramenta foi aplicada, qual foi o resultado observado e onde estao os logs.

## O que o pipeline faz

O pipeline executa programas C pequenos, chamados aqui de benchmarks. Alguns
benchmarks contem vulnerabilidades conhecidas; outros representam casos corretos
usados como controle.

As ferramentas integradas atualmente sao:

- `ESBMC`: verificacao de propriedades e asserts;
- `AddressSanitizer` ou `ASAN`: deteccao de corrupcao de memoria;
- `ThreadSanitizer` ou `TSAN`: deteccao de condicoes de corrida;
- `AFL++`: fuzzing para explorar entradas e provocar crashes;
- detector simples de deadlock por timeout;
- uma etapa simulada de reparo por LLM, ainda sem chamada a API externa.

Depois de executar as ferramentas, o projeto gera relatorios em CSV e HTML. Os
relatorios ficam na pasta `reports/`, e os logs brutos ficam em `outputs/`.

## Por que isso e util

Em experimentos com ferramentas de analise, e comum que o resultado dependa do
ambiente: sistema operacional, compilador, arquitetura, runtime dos sanitizers e
versao das ferramentas. Este repositorio tenta reduzir essa incerteza com tres
decisoes:

- uso de Docker para criar um ambiente Linux reproduzivel;
- arquivo de metadados para declarar o comportamento esperado de cada benchmark;
- logs individuais por ferramenta, para permitir auditoria posterior.

Assim, quando uma ferramenta detecta ou deixa de detectar um problema, o
resultado nao fica solto. Ele pode ser comparado com a expectativa registrada em
`benchmarks/metadata.csv`.

## Estrutura do projeto

```text
pipeline-vss-llm/
├── benchmarks/
│   ├── metadata.csv
│   ├── assertion_violation/
│   ├── data_race/
│   ├── deadlock/
│   ├── memory_corruption/
│   └── random_tests/
├── outputs/
├── reports/
├── pipeline_runner/
├── scripts/
├── tests/
├── Dockerfile
├── docker-compose.yml
├── run_pipeline.py
└── README.md
```

As pastas principais sao:

- `benchmarks/`: programas C usados no experimento;
- `benchmarks/metadata.csv`: metadados e expectativas dos benchmarks;
- `outputs/`: logs gerados pelas ferramentas;
- `reports/`: resultados consolidados;
- `scripts/`: executores das ferramentas e utilitarios;
- `pipeline_runner/`: codigo interno do orquestrador;
- `tests/`: testes automatizados do proprio pipeline.

## Benchmarks e metadados

Os benchmarks estao separados por categoria:

- `assertion_violation`: violacoes de propriedades verificadas por assert;
- `memory_corruption`: erros de memoria, como buffer overflow e use-after-free;
- `data_race`: acessos concorrentes sem sincronizacao adequada;
- `deadlock`: programas com possibilidade de espera circular;
- `random_tests`: codigos exploratorios usados para testar inferencia automatica.

Alem dos casos minimos, a base tambem inclui benchmarks mais dificeis, com erro
dependente de estado composto, ramos condicionais, aliasing, indices derivados e
ordem de locks definida em funcoes auxiliares. Esses casos ajudam a avaliar se a
ferramenta encontra problemas menos obvios do que exemplos didaticos muito
diretos.

O arquivo `benchmarks/metadata.csv` e uma parte importante do experimento. Ele
registra, para cada benchmark controlado:

- `id`: identificador do benchmark;
- `path`: caminho do arquivo C;
- `category`: categoria do problema;
- `expected_behavior`: se o programa e `vulneravel` ou `correto`;
- `expected_esbmc`, `expected_asan`, `expected_tsan`, `expected_deadlock`,
  `expected_afl`: expectativa especifica para cada ferramenta;
- `include_in_pipeline`: se o benchmark entra na rodada principal;
- `description`: descricao resumida do caso.

Essa decisao evita depender apenas do nome do arquivo. Os sufixos como
`_error.c`, `_safe.c`, `_fixed.c` e `_pass.c` continuam existindo como
convencao, mas a fonte principal de verdade para o experimento e o arquivo de
metadados.

## Como o pipeline escolhe as ferramentas

Quando um benchmark esta registrado em `benchmarks/metadata.csv`, o pipeline usa
as colunas `expected_*` para decidir quais ferramentas devem ser executadas.
Uma ferramenta entra na rodada quando sua expectativa e aplicavel, por exemplo:

- `detectar`;
- `nao_detectar`;
- `inconclusivo`.

Quando a expectativa esta como `nao_aplicavel`, a ferramenta nao e executada
para aquele benchmark.

Para arquivos sem metadados, como alguns exemplos de `benchmarks/random_tests/`,
o pipeline tenta inferir as ferramentas a partir do codigo:

- uso de `assert` ou `__ESBMC_assert`: seleciona ESBMC;
- uso de alocacao, `free`, copia insegura ou acesso a vetor: seleciona ASAN;
- uso de entrada externa ou padroes de memoria: seleciona AFL++;
- uso de `pthread`: seleciona TSAN;
- uso de `pthread_mutex_lock`: seleciona detector de deadlock.

Essa inferencia e util para triagem, mas nao substitui os metadados quando o
objetivo e pesquisa cientifica.

## Ambiente recomendado

Para gerar resultados finais, o ambiente recomendado e Linux `amd64` nativo com
Docker. Esse ambiente evita a emulacao do Docker Desktop em Apple Silicon, que
pode afetar principalmente o ThreadSanitizer.

O projeto ja inclui:

- `Dockerfile`: imagem Ubuntu 24.04 com as ferramentas necessarias;
- `docker-compose.yml`: configuracao da execucao;
- `scripts/setup_lightsail_ubuntu.sh`: preparacao de uma VM Ubuntu na AWS;
- `scripts/install_aws_toolchain.sh`: instalacao local de `clang`, `gcc`,
  `g++`, `build-essential`, headers/runtimes do Clang e `esbmc`, usados pelo
  painel web nas validacoes;
- `scripts/run_lightsail_report.sh`: execucao completa e empacotamento dos
  relatorios;
- `scripts/install_aws_web_service.sh`: instalacao do painel web como servico
  `systemd`, com Nginx como proxy HTTP.

## Execucao rapida com Docker

Em uma maquina com Docker instalado:

```bash
docker compose build
docker compose run --rm pipeline
```

Ao final, consulte:

```text
reports/results.csv
reports/summary.csv
reports/report.html
reports/benchmark_metrics.csv
reports/category_metrics.csv
```

O arquivo mais amigavel para leitura e apresentacao e:

```text
reports/report.html
```

## Execucao recomendada na AWS Lightsail

Para a instancia usada no experimento, foi considerada uma AWS Lightsail com
Ubuntu 24.04, 2 GB de RAM e 2 vCPU. Como a memoria e limitada, o script de
preparacao cria swap antes da construcao da imagem Docker. A execucao em Linux
`amd64` nativo e preferivel para a rodada final, pois reduz efeitos de emulacao
em ferramentas como o ThreadSanitizer.

Na instancia:

```bash
sudo apt update
sudo apt install -y git
git clone https://github.com/EricoBorgonove/vss-concurrency-llm-pipeline.git
cd vss-concurrency-llm-pipeline
./scripts/setup_lightsail_ubuntu.sh
```

Se o script adicionar o usuario ao grupo `docker`, saia e entre novamente na
sessao SSH, ou rode:

```bash
newgrp docker
```

Depois execute:

```bash
cd ~/vss-concurrency-llm-pipeline
./scripts/run_lightsail_report.sh
```

Para zerar o historico local de benchmarks antes de uma nova rodada, sem apagar
os repositorios GitHub clonados em `inputs/github_repos/`, use:

```bash
./scripts/clean_benchmark_history.sh
./scripts/run_lightsail_report.sh
```

Tambem e possivel pedir essa limpeza junto com a rodada:

```bash
CLEAN_BENCHMARK_HISTORY=1 ./scripts/run_lightsail_report.sh
```

Essa rodada tambem gera os artefatos da analise de links GitHub:

- `reports/github_llm_queue.csv`: candidatos priorizados para analise por LLM;
- `reports/github_tool_validations.csv`: validacoes dos achados por ferramentas;
- `reports/report.html`: dashboard atualizado com essas secoes.

Na tela local de links GitHub (`/github`), o botao **Rodar testes dos links**
executa a validacao global em background e grava o status em
`reports/github_validation_run_latest.log`. Por padrao, ele tenta validar todos
os candidatos; defina `GITHUB_VALIDATION_LIMIT` para limitar a rodada, ou use
`GITHUB_VALIDATION_LIMIT=all` para deixar explicito que todos devem ser
processados. O timeout por ferramenta usa `GITHUB_VALIDATION_TIMEOUT`.

Por padrao, a validacao de achados GitHub e limitada a 25 execucoes para
preservar a instancia pequena. Para ajustar ou desativar:

```bash
GITHUB_VALIDATION_LIMIT=50 GITHUB_VALIDATION_TIMEOUT=15 ./scripts/run_lightsail_report.sh
GITHUB_VALIDATE_FINDINGS=0 ./scripts/run_lightsail_report.sh
```

O script gera um pacote chamado:

```text
reports-lightsail.tar.gz
```

Para baixar os relatorios para a maquina local:

```bash
scp ubuntu@IP_DA_INSTANCIA:~/vss-concurrency-llm-pipeline/reports-lightsail.tar.gz .
tar -xzf reports-lightsail.tar.gz
```

Para deixar o painel web ativo na instancia, instale o servico:

```bash
./scripts/install_aws_web_service.sh
```

O script cria:

- o arquivo `/etc/vss-pipeline-web.env`, com as variaveis do painel;
- o servico `systemd` `vss-pipeline-web`;
- uma configuracao Nginx que publica o painel em `http://IP_DA_INSTANCIA/`.

Por padrao, o painel usa os usuarios `erico`, `brenda`, `alberjan` e `lucas`,
todos com a senha `vss123`.

Na Lightsail, libere a porta TCP `80` no firewall da instancia. Para usar um
dominio, informe o nome antes de instalar:

```bash
SERVER_NAME="exemplo.seudominio.com" ./scripts/install_aws_web_service.sh
```

Com o painel instalado, os comandos uteis na instancia sao:

```bash
sudo systemctl status vss-pipeline-web
sudo systemctl restart vss-pipeline-web
sudo journalctl -u vss-pipeline-web -f
```

Se um modal de log mostrar que o arquivo nao foi encontrado, o relatorio esta
apontando para um arquivo em `outputs/` que nao existe na instancia atual. Isso
normalmente acontece depois de atualizar `reports/` pelo Git sem regenerar os
logs locais. Regere os relatorios e logs juntos:

```bash
./scripts/run_lightsail_report.sh
sudo systemctl restart vss-pipeline-web
```

Os relatorios em `reports/` e logs em `outputs/` sao artefatos locais. Eles nao
sao versionados para evitar conflitos durante `git pull` na AWS. Os clones de
repositorios analisados ficam em `inputs/github_repos/` e nao sao apagados pelos
scripts de limpeza do historico de benchmarks.

Se uma validacao mostrar `Compilador C nao encontrado`, `Executavel ESBMC nao
encontrado` ou `fatal error: 'stddef.h' file not found`, instale as ferramentas
locais do painel e reinicie o servico:

```bash
./scripts/install_aws_toolchain.sh
sudo systemctl restart vss-pipeline-web
```

## Execucao local sem Docker

Tambem e possivel executar partes do pipeline localmente. Os scripts Python usam
apenas a biblioteca padrao.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

Para executar o pipeline diretamente:

```bash
python3 run_pipeline.py
```

Para executar testes automatizados do projeto:

```bash
python3 -m unittest
```

Para gerar relatorios a partir dos logs ja existentes:

```bash
python3 scripts/generate_report.py --latest-only
```

Para registrar o diagnostico do ambiente local:

```bash
python3 scripts/check_environment.py
```

Na execucao local registrada em 2026-06-23, o diagnostico encontrou `clang`,
`gcc`, `esbmc` 8.2.0, `afl-clang-fast` e `afl-fuzz` disponiveis. O arquivo
gerado fica em `outputs/environment/` e deve ser usado para contextualizar os
resultados, porque versoes e arquitetura influenciam sanitizers e verificadores.

## Interface local e relatorio HTML

O servidor local de links GitHub expoe uma tela em `/github`. Ela permite:

- adicionar links de repositorios GitHub;
- baixar o repositorio;
- listar arquivos C/C++;
- gerar achados por triagem estatica;
- revisar achados em modal;
- testar todos os achados de um link;
- testar somente um achado especifico;
- rodar testes globais dos links em background;
- acompanhar progresso com texto e barra visual;
- abrir logs das ferramentas em modal.

Antes de acessar o painel, o servidor mostra a tela `/login`. As credenciais
padrao de desenvolvimento sao:

- `erico` / `vss123`;
- `brenda` / `vss123`;
- `alberjan` / `vss123`;
- `lucas` / `vss123`.

Na AWS, o script `scripts/install_aws_web_service.sh` grava esses mesmos
usuarios no arquivo de ambiente do servico.

A tela `/validacoes` concentra a auditoria dos testes dos achados GitHub. Ela
mostra resumo, filtros, tabela de achados, status da ultima validacao, botao
para testar novamente um achado, botao para rodar testes globais e modal para
abrir o log da ferramenta.

O relatorio HTML em `reports/report.html` tambem e interativo:

- possui filtros por ferramenta, categoria, classificacao e expectativa;
- mostra metricas por categoria antes do resumo;
- permite abrir o codigo do benchmark em modal;
- permite abrir a saida/log da ferramenta em modal;
- inclui botao para rodar benchmarks;
- inclui botao para voltar para a tela de links;
- usa larguras ajustadas na tabela de resultados detalhados.

## Execucao individual das ferramentas

Cada ferramenta tambem pode ser chamada separadamente.

ESBMC:

```bash
python3 scripts/run_esbmc.py benchmarks/assertion_violation/simple_assert_fail.c
```

ASAN:

```bash
python3 scripts/run_asan.py benchmarks/memory_corruption/simple_buffer_overflow.c
```

TSAN:

```bash
python3 scripts/run_tsan.py benchmarks/data_race/simple_data_race.c
```

Deadlock por timeout:

```bash
python3 scripts/run_deadlock.py benchmarks/deadlock/simple_deadlock.c
```

AFL++:

```bash
python3 scripts/run_afl.py benchmarks/memory_corruption/simple_buffer_overflow.c
```

## Como interpretar os resultados

O relatorio detalhado fica em `reports/results.csv`. As colunas mais importantes
sao:

- `tool`: ferramenta executada;
- `benchmark`: benchmark analisado;
- `expected_behavior`: comportamento esperado do programa;
- `expected_tool_behavior`: expectativa especifica para a ferramenta;
- `classification`: resultado observado;
- `expectation_match`: comparacao entre resultado observado e comportamento
  esperado;
- `tool_expectation_match`: comparacao entre resultado observado e expectativa
  da ferramenta;
- `log_file`: log usado para produzir aquela linha.

As classificacoes principais sao:

- `detectado`: a ferramenta encontrou evidencia do problema;
- `nao detectado`: a ferramenta executou, mas nao encontrou evidencia;
- `inconclusivo`: o resultado nao permite concluir;
- `erro de execucao`: houve falha operacional;
- `ferramenta indisponivel`: a ferramenta nao estava instalada ou acessivel.

O resumo fica em `reports/summary.csv`. Ele agrega resultados por ferramenta,
expectativa e classificacao.

## Observacao sobre TSAN e Apple Silicon

O ThreadSanitizer depende bastante do runtime e da arquitetura. Em Docker
Desktop sobre Apple Silicon, a imagem `linux/amd64` roda sob emulacao. Nesse
cenario, o TSAN pode compilar o programa, mas terminar com codigo `66` sem
produzir diagnostico `ThreadSanitizer`.

Quando isso acontece, o pipeline classifica o caso como `inconclusivo`. Essa e
uma escolha metodologica: o ambiente nao produziu evidencia confiavel nem para
confirmar nem para negar a corrida.

Para resultados finais, prefira Linux `amd64` nativo, como a execucao na AWS
Lightsail. Em macOS, uma alternativa para desenvolvimento local e rodar TSAN com
LLVM instalado via Homebrew:

```bash
for f in benchmarks/data_race/*.c benchmarks/random_tests/random_race_counter.c benchmarks/random_tests/random_deadlock_pair.c; do
  python3 scripts/run_tsan.py "$f" --compiler /opt/homebrew/opt/llvm/bin/clang || true
done
python3 scripts/generate_report.py --latest-only
```

## AFL++ e campanhas curtas

O AFL++ e usado aqui em campanhas curtas. Por isso, ausencia de crash em poucos
segundos nao deve ser interpretada como prova de seguranca. Nesses casos, o
pipeline pode classificar o resultado como `inconclusivo`.

Quando o AFL++ usa `AFL_USE_ASAN=1`, algumas violacoes de memoria aparecem logo
no dry run. O pipeline trata esse crash inicial como deteccao, pois o binario
falhou durante uma execucao controlada do fuzzer.

## Etapa LLM simulada

O projeto possui uma etapa simulada de reparo por LLM. Ela ainda nao chama uma
API externa e nao altera automaticamente os arquivos C.

O objetivo atual dessa etapa e exercitar o fluxo experimental:

- ler um log de ferramenta;
- identificar marcadores simples de erro;
- gerar uma sugestao textual generica;
- registrar essa sugestao em `outputs/llm/`;
- permitir uma validacao posterior com benchmarks corrigidos.

Exemplo:

```bash
python3 scripts/run_llm_repair.py outputs/asan/<arquivo_de_log>.log
```

Para validar uma sugestao simulada:

```bash
python3 scripts/validate_llm_repair.py outputs/llm/<arquivo_de_reparo>.txt
```

## Testes do projeto

A suite de testes verifica a parte interna do pipeline sem depender das
ferramentas externas pesadas. Ela cobre, por exemplo:

- descoberta de benchmarks;
- interpretacao de logs;
- classificacao de resultados;
- geracao de resumo;
- helpers dos executores;
- validacao simulada de reparos.

Execute:

```bash
python3 -m unittest
```

## Limitacoes conhecidas

Este e um pipeline experimental. Algumas limitacoes importantes sao:

- resultados de sanitizers podem variar conforme compilador, sistema e
  arquitetura;
- AFL++ em campanhas curtas nao garante ausencia de vulnerabilidade;
- o detector de deadlock por timeout e simples e pode produzir resultados
  dependentes de escalonamento;
- TSAN dentro de Docker emulado no Apple Silicon pode ficar inconclusivo;
- a etapa LLM ainda e simulada e nao substitui uma analise manual.

Essas limitacoes nao invalidam o experimento. Pelo contrario: elas ficam
registradas para que os resultados sejam interpretados com cuidado.

## Proximas etapas

As melhorias de interface do relatorio HTML ja foram incorporadas. As proximas
evolucoes mais relevantes sao:

- executar uma rodada final em Linux `amd64` nativo, preferencialmente na AWS
  Lightsail, para reduzir efeitos de emulacao;
- revisar casos `inconclusivo`, especialmente retornos de ferramenta como `6`,
  olhando os logs diretamente pelo modal;
- decidir se os CSVs gerados em `reports/` serao versionados como artefatos da
  rodada final ou mantidos apenas localmente;
- integrar uma LLM real para sugerir reparos a partir dos logs coletados.
