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
- constroi a imagem Docker;
- executa o pipeline completo;
- mostra o resumo do TSAN;
- empacota `reports/`, `outputs/environment/` e `outputs/pipeline/`.

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
