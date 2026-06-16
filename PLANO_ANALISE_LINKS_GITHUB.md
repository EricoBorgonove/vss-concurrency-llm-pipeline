# Plano para analise de links do GitHub

Este documento descreve a evolucao do pipeline para permitir que o usuario
informe links de repositorios ou arquivos do GitHub por uma pagina HTML. A
aplicacao devera registrar cada link analisado, executar uma triagem controlada
do codigo, salvar os resultados em CSV e exibir tudo no dashboard HTML.

## Objetivo

Adicionar uma interface simples para entrada de links do GitHub e transformar
esses links em uma fila auditavel de analises. Cada link informado deve gerar
um registro persistente, com status da analise, erros encontrados, ferramentas
executadas e, futuramente, explicacoes geradas pela LLM.

## Principios da implementacao

- Nenhum repositorio externo deve ser misturado com os benchmarks controlados.
- Links analisados devem ficar registrados mesmo quando a analise falhar.
- Resultados devem ser exportados para CSV e aparecer no dashboard HTML.
- A primeira versao deve funcionar localmente e na AWS com Docker.
- A pagina HTML deve ser simples e operacional, sem depender de um framework
  pesado.
- A LLM deve entrar depois que o fluxo de coleta, registro e relatorio estiver
  estavel.

## Fluxo esperado

```text
pagina HTML -> usuario informa link do GitHub -> backend registra link
-> codigo e baixado em area isolada -> arquivos C/C++ sao descobertos
-> triagem automatica executa -> resultados sao salvos em CSV
-> dashboard HTML mostra links, status e erros encontrados
```

## Estrutura de arquivos proposta

```text
web/
  github_input.html

scripts/
  github_link_server.py
  analyze_github_url.py

pipeline_runner/
  github_links.py
  github_analyzer.py

inputs/
  github_repos/

outputs/
  github/

reports/
  github_links.csv
  github_findings.csv
  report.html
```

## Passo 1: definir o modelo dos dados

Criar o formato dos CSVs que vao controlar os links digitados e os problemas
encontrados.

Arquivo `reports/github_links.csv`:

```text
id,
submitted_at,
url,
url_type,
status,
local_path,
error,
started_at,
finished_at
```

Arquivo `reports/github_findings.csv`:

```text
id,
link_id,
tool,
file_path,
line,
category,
severity,
status,
message,
evidence,
created_at
```

Status iniciais para links:

- `pendente`;
- `baixando`;
- `analisando`;
- `concluido`;
- `falhou`.

Status iniciais para achados:

- `suspeito`;
- `detectado`;
- `inconclusivo`;
- `erro de execucao`.

Entregaveis:

- funcoes para criar, ler e atualizar os CSVs;
- testes unitarios para escrita e leitura;
- documentacao dos campos.

Criterio de sucesso:

- um link pode ser registrado no CSV mesmo antes de qualquer analise.

## Passo 2: criar a pagina HTML de entrada

Criar uma pagina simples para o usuario digitar o link do GitHub.

Campos da primeira versao:

- URL do GitHub;
- botao para enviar;
- tabela com links ja registrados;
- status da analise;
- mensagem de erro, quando houver.

Arquivo sugerido:

```text
web/github_input.html
```

Entregaveis:

- formulario HTML;
- tabela de controle;
- validacao basica no navegador;
- layout consistente com o dashboard.

Criterio de sucesso:

- o usuario consegue abrir a pagina no navegador e visualizar a tabela de links.

## Passo 3: criar um backend local simples

Como uma pagina HTML estatica nao consegue gravar CSV sozinha de forma segura,
sera necessario um backend pequeno em Python.

Comando sugerido:

```bash
python3 scripts/github_link_server.py
```

Rotas iniciais:

```text
GET  /
GET  /api/github-links
POST /api/github-links
GET  /api/github-findings
```

Entregaveis:

- servidor HTTP simples usando biblioteca padrao do Python;
- endpoint para registrar links;
- endpoint para listar links;
- endpoint para listar achados;
- testes para as funcoes principais sem precisar subir servidor real.

Criterio de sucesso:

- ao enviar um link pela pagina, ele aparece em `reports/github_links.csv`.

## Passo 4: validar e classificar links do GitHub

A aplicacao deve aceitar, inicialmente:

- repositorio completo: `https://github.com/user/repo`;
- arquivo especifico: `https://github.com/user/repo/blob/branch/path/file.c`;
- diretorio especifico: `https://github.com/user/repo/tree/branch/path`.

Entregaveis:

- parser de URL do GitHub;
- identificacao de tipo: `repo`, `file`, `directory`;
- rejeicao de URLs fora do GitHub;
- mensagens de erro claras.

Criterio de sucesso:

- URLs invalidas entram no CSV com status `falhou` e erro explicativo.

## Passo 5: baixar codigo em area isolada

Repositorios externos devem ser baixados fora de `benchmarks/`, para nao
contaminar o conjunto experimental controlado.

Local sugerido:

```text
inputs/github_repos/<link_id>/
```

Entregaveis:

- clonagem rasa para repositorios;
- download controlado para arquivos especificos;
- limite de tamanho;
- timeout;
- limpeza ou sobrescrita controlada por `link_id`.

Criterio de sucesso:

- um repositorio GitHub valido e baixado em uma pasta isolada e seu caminho fica
  registrado no CSV.

## Passo 6: descobrir arquivos analisaveis

Apos baixar o codigo, o pipeline deve procurar arquivos relevantes.

Extensoes iniciais:

- `.c`;
- `.h`;
- `.cpp`;
- `.hpp`.

Filtros recomendados:

- ignorar `.git`;
- ignorar dependencias vendorizadas quando possivel;
- limitar quantidade maxima de arquivos por rodada;
- registrar quando nenhum arquivo analisavel for encontrado.

Entregaveis:

- funcao de descoberta de arquivos;
- testes com arvore temporaria;
- registro de erro quando nao houver arquivos C/C++.

Criterio de sucesso:

- a aplicacao lista os arquivos candidatos antes de rodar ferramentas.

## Passo 7: executar triagem estatica simples

Antes de compilar codigo externo, a primeira analise deve ser textual e segura.

Padroes iniciais:

- `strcpy`;
- `strcat`;
- `sprintf`;
- `gets`;
- `memcpy` com tamanho suspeito;
- `pthread_mutex_lock`;
- `pthread_create`;
- `assert`;
- acesso por indice em arrays.

Categorias iniciais:

- `memory_corruption`;
- `data_race`;
- `deadlock`;
- `assertion_violation`;
- `unknown`.

Entregaveis:

- analisador textual simples;
- registro dos achados em `reports/github_findings.csv`;
- testes para cada categoria.

Criterio de sucesso:

- arquivos com padroes suspeitos geram linhas em `github_findings.csv`.

## Passo 8: executar ferramentas quando for viavel

Depois da triagem textual, a aplicacao pode tentar executar ferramentas em
arquivos pequenos e potencialmente compilaveis.

Primeira versao recomendada:

- ASAN para arquivos C simples;
- TSAN quando houver `pthread_create`;
- ESBMC quando houver `assert`;
- Deadlock Timeout quando houver uso de mutex.

Cuidados:

- nem todo codigo de GitHub sera compilavel isoladamente;
- falhas de compilacao devem virar `erro de execucao`, nao falha do pipeline;
- cada execucao deve ter timeout;
- logs devem ir para `outputs/github/`.

Entregaveis:

- selecao conservadora de ferramentas;
- execucao isolada;
- registro de resultado por arquivo;
- links para logs no dashboard.

Criterio de sucesso:

- codigo compilavel e analisado; codigo nao compilavel gera erro rastreavel.

## Passo 9: integrar resultados ao dashboard HTML

O `reports/report.html` deve ganhar uma secao para links do GitHub.

Secoes propostas:

- Links analisados;
- Achados por categoria;
- Erros de execucao;
- Logs gerados;
- Futuras analises da LLM.

Filtros desejados:

- status do link;
- categoria;
- severidade;
- ferramenta;
- busca por URL ou arquivo.

Entregaveis:

- leitura de `github_links.csv`;
- leitura de `github_findings.csv`;
- novas tabelas no dashboard;
- links para logs em `outputs/github/`.

Criterio de sucesso:

- o dashboard mostra tanto benchmarks controlados quanto analises de links do
  GitHub, sem misturar os dois tipos de experimento.

## Passo 10: integrar a LLM real

Quando a API estiver configurada, a LLM deve analisar os achados e explicar os
riscos encontrados.

Entrada da LLM:

- URL original;
- arquivo analisado;
- trecho de codigo;
- achados da triagem;
- log da ferramenta, quando existir.

Saida esperada:

```text
issue_type:
confidence:
evidence_summary:
root_cause:
recommended_fix:
risk:
validation_hint:
```

Entregaveis:

- chamada opcional da LLM;
- modo `mock` como padrao;
- arquivo de resposta em `outputs/llm/`;
- link para a analise no dashboard.

Criterio de sucesso:

- sem chave de API, o fluxo continua funcionando;
- com chave de API, achados podem receber uma explicacao da LLM.

## Passo 11: preparar execucao na AWS

A pagina HTML e o backend devem funcionar na instancia Lightsail.

Comandos esperados:

```bash
python3 scripts/github_link_server.py --host 0.0.0.0 --port 8080
```

Cuidados:

- documentar porta usada;
- orientar uso de firewall/security group;
- manter dados em `reports/`, `outputs/` e `inputs/`;
- empacotar resultados junto com `reports-lightsail.tar.gz`.

Entregaveis:

- documentacao para AWS;
- ajuste no script de empacotamento;
- opcionalmente servico Docker/Compose.

Criterio de sucesso:

- o usuario acessa a pagina pelo navegador, digita links, roda analises e baixa
  os resultados depois.

## Ordem recomendada de commits

1. `docs: descreve plano de analise de links github`
2. `feat: adiciona controle csv de links github`
3. `feat: cria pagina html para entrada de links github`
4. `feat: adiciona servidor local para links github`
5. `feat: valida urls do github`
6. `feat: baixa repositorios github em area isolada`
7. `feat: descobre arquivos c e cpp em links github`
8. `feat: registra achados estaticos de codigo github`
9. `feat: integra achados github ao dashboard`
10. `feat: executa ferramentas em arquivos github viaveis`
11. `feat: adiciona analise llm para achados github`
12. `docs: documenta analise github na aws`

## Resultado esperado

Ao final dessa evolucao, o projeto tera duas frentes complementares:

- benchmarks controlados, usados para avaliacao reprodutivel;
- links do GitHub, usados para exploracao de codigo real.

Essa separacao e importante para a metodologia. Os benchmarks controlados
permitem medir comportamento esperado. Os links do GitHub permitem demonstrar a
aplicacao em codigo externo, registrando erros, limitacoes e achados de forma
auditavel.
