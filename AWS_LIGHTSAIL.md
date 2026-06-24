# Execucao na AWS Lightsail

Guia rapido para gerar os relatorios finais em uma instancia AWS Lightsail com
Ubuntu 24.04, 2 GB de RAM e 2 vCPU.

## 1. Acessar a instancia

Na sua maquina local:

```bash
ssh ubuntu@IP_DA_INSTANCIA
```

## 2. Clonar o projeto

Na instancia:

```bash
sudo apt update
sudo apt install -y git
git clone https://github.com/EricoBorgonove/vss-concurrency-llm-pipeline.git
cd vss-concurrency-llm-pipeline
```

## 3. Preparar Ubuntu, Docker e swap

```bash
./scripts/setup_lightsail_ubuntu.sh
```

Se o script informar que adicionou o usuario ao grupo `docker`, saia e entre
novamente no SSH, ou rode:

```bash
newgrp docker
```

## 4. Gerar relatorios

```bash
cd ~/vss-concurrency-llm-pipeline
./scripts/run_lightsail_report.sh
```

Esse comando:

- mostra diagnostico rapido da instancia;
- move logs e relatorios antigos para `antigos/rodada-antiga-<data>/`;
- constroi a imagem Docker;
- executa o pipeline completo;
- gera `reports/github_llm_queue.csv` com candidatos para LLM;
- valida uma amostra dos achados GitHub por ferramentas locais;
- gera `reports/github_tool_validations.csv`;
- atualiza o dashboard HTML com fila LLM e validacoes;
- mostra o resumo do TSAN;
- empacota `reports/`, `outputs/environment/` e `outputs/pipeline/`.

Por padrao, a validacao GitHub executa no maximo 25 achados, com timeout de 10
segundos por ferramenta. Para mudar:

```bash
GITHUB_VALIDATION_LIMIT=50 GITHUB_VALIDATION_TIMEOUT=15 ./scripts/run_lightsail_report.sh
```

Para pular essa etapa:

```bash
GITHUB_VALIDATE_FINDINGS=0 ./scripts/run_lightsail_report.sh
```

Se for necessario manter os logs antigos no lugar e gerar o relatorio misturando
historico anterior, execute com:

```bash
ARCHIVE_OLD_RESULTS=0 ./scripts/run_lightsail_report.sh
```

## 5. Verificar TSAN

Na instancia:

```bash
grep '^tsan' reports/summary.csv
```

Em Linux `amd64` nativo, o esperado e que o TSAN deixe de ficar inconclusivo por
emulacao. Se ainda ficar inconclusivo, o problema passa a ser investigado no
runtime/benchmark, nao no Apple Silicon.

## 6. Baixar relatorios

Na sua maquina local:

```bash
scp ubuntu@IP_DA_INSTANCIA:~/vss-concurrency-llm-pipeline/reports-lightsail.tar.gz .
tar -xzf reports-lightsail.tar.gz
```

Arquivo principal para apresentacao:

```text
reports/report.html
```

Arquivos CSV principais:

```text
reports/results.csv
reports/summary.csv
reports/benchmark_metrics.csv
reports/category_metrics.csv
```

## 7. Atualizar o projeto na instancia

Se novas correcoes forem enviadas para o GitHub:

```bash
cd ~/vss-concurrency-llm-pipeline
git pull
./scripts/run_lightsail_report.sh
```

## 8. Servir o painel web com login

Antes de expor o painel, configure credenciais diferentes do padrao de
desenvolvimento:

```bash
export VSS_AUTH_USERS="erico:senha-forte,brenda:senha-forte,alberjan:senha-forte,lucas:senha-forte"
python3 scripts/github_link_server.py --host 0.0.0.0 --port 8080
```

As telas principais ficam protegidas por login:

- `/login`: entrada do usuario;
- `/github`: cadastro, triagem e revisao de links;
- `/validacoes`: acompanhamento e auditoria das validacoes;
- `/reports/report.html`: relatorio consolidado.
