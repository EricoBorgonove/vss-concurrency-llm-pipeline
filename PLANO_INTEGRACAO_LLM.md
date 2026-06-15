# Plano de integracao da LLM ao pipeline

Este documento descreve, em passos pequenos, como a etapa de LLM sera integrada
ao pipeline experimental. A ideia principal e manter a rastreabilidade do
experimento: a LLM deve explicar e sugerir reparos, mas a validacao continua
sendo feita pelas ferramentas ja integradas ao projeto.

## Objetivo

Adicionar uma etapa de LLM capaz de analisar evidencias geradas pelas
ferramentas, produzir uma explicacao estruturada do problema e sugerir uma
possivel correcao. Em uma etapa posterior, a sugestao podera ser transformada em
patch e validada automaticamente em uma copia controlada do benchmark.

## Principios da implementacao

- A LLM nao deve substituir ASAN, TSAN, ESBMC, AFL++ ou Deadlock Timeout.
- Toda resposta da LLM deve ser salva em arquivo para auditoria.
- Nenhuma chave de API deve ser gravada no repositorio.
- Os testes automatizados devem continuar funcionando sem acesso externo.
- O modo simulado deve continuar existindo para testes e execucoes offline.
- A aplicacao deve diferenciar sugestao textual, patch gerado e patch validado.

## Passo 1: padronizar a saida da LLM

Criar um formato unico para a resposta da LLM, mesmo quando ela estiver em modo
simulado. A resposta deve conter campos como:

```text
issue_type:
confidence:
tool:
benchmark:
evidence_summary:
root_cause:
recommended_fix:
risk:
validation_hint:
```

Entregaveis:

- atualizar `scripts/run_llm_repair.py` para gerar esse formato;
- atualizar os testes da etapa LLM;
- documentar o significado de cada campo.

Criterio de sucesso:

- o arquivo em `outputs/llm/` deve ser compreensivel e sempre conter os mesmos
  campos minimos.

## Passo 2: criar um cliente LLM com dois modos

Criar um modulo dedicado para acesso a LLM, por exemplo:

```text
pipeline_runner/llm_client.py
```

Esse modulo deve suportar:

- `mock`: resposta deterministica, usada em testes e sem internet;
- `openai`: chamada real a API, usada apenas quando configurada.

Variaveis de ambiente previstas:

```text
LLM_PROVIDER=mock|openai
LLM_MODEL=<nome-do-modelo>
OPENAI_API_KEY=<chave>
```

Entregaveis:

- cliente LLM isolado do restante do pipeline;
- testes cobrindo o modo `mock`;
- tratamento claro quando `OPENAI_API_KEY` nao estiver configurada.

Criterio de sucesso:

- a suite de testes deve passar sem depender de rede ou chave de API.

## Passo 3: enriquecer o prompt com contexto experimental

A chamada da LLM deve receber mais do que apenas o texto bruto do log. O prompt
deve incluir:

- ferramenta que gerou a evidencia;
- benchmark analisado;
- categoria do benchmark;
- comportamento esperado;
- expectativa especifica da ferramenta;
- classificacao observada;
- trecho relevante do log;
- codigo-fonte do benchmark, quando for seguro e pequeno o suficiente.

Entregaveis:

- funcao para montar contexto da LLM a partir do log e dos metadados;
- limite de tamanho para evitar prompts grandes demais;
- testes com logs pequenos e controlados.

Criterio de sucesso:

- a LLM deve receber contexto suficiente para explicar o erro sem perder a
  ligacao com os metadados do experimento.

## Passo 4: salvar respostas com rastreabilidade

Cada execucao da LLM deve gerar um arquivo em:

```text
outputs/llm/
```

O arquivo deve registrar:

- data e hora;
- provedor usado;
- modelo usado;
- ferramenta de origem;
- benchmark;
- log usado como evidencia;
- hash ou versao do prompt;
- resposta da LLM;
- status da execucao.

Entregaveis:

- novo formato de arquivo de saida;
- sanitizacao de caminhos absolutos;
- testes garantindo que os metadados minimos sao gravados.

Criterio de sucesso:

- qualquer pessoa deve conseguir abrir o arquivo e entender de onde veio a
  sugestao.

## Passo 5: integrar a LLM ao relatorio HTML

O dashboard deve mostrar quando existe analise de LLM associada a um resultado.
Inicialmente, basta adicionar um link para o arquivo gerado.

Entregaveis:

- leitura dos arquivos em `outputs/llm/`;
- associacao por benchmark, ferramenta e log de origem;
- coluna ou secao no `report.html` com link para a analise.

Criterio de sucesso:

- ao abrir o dashboard, o usuario deve conseguir navegar do resultado detectado
  ate a explicacao da LLM.

## Passo 6: validar sugestoes sem aplicar patch automaticamente

Antes de gerar patches automaticamente, a sugestao textual deve poder ser
validada de forma controlada. O fluxo inicial sera:

```text
log da ferramenta -> analise da LLM -> sugestao textual -> validacao manual ou
benchmark corrigido informado pelo usuario -> ferramenta roda novamente
```

Entregaveis:

- manter e evoluir `scripts/validate_llm_repair.py`;
- registrar a validacao em `outputs/llm/`;
- indicar se a ferramenta confirmou ou rejeitou o reparo.

Criterio de sucesso:

- o relatorio deve diferenciar sugestao nao validada de sugestao validada.

## Passo 7: gerar patch em area isolada

Somente depois da etapa textual estar estavel, a LLM podera gerar patch. Esse
patch nao deve alterar diretamente os benchmarks originais. Ele deve ser salvo
em uma area separada, por exemplo:

```text
outputs/llm/patches/
```

Entregaveis:

- formato de patch auditavel;
- copia temporaria do benchmark para aplicacao;
- validacao automatica com a ferramenta correspondente.

Criterio de sucesso:

- o benchmark original permanece intacto;
- o patch e aplicado e testado em copia isolada;
- o resultado da validacao fica registrado.

## Passo 8: executar na AWS com configuracao explicita

A execucao na AWS deve continuar reprodutivel. A LLM real so deve ser usada
quando o ambiente estiver explicitamente configurado.

Entregaveis:

- documentar variaveis de ambiente no README ou arquivo especifico;
- ajustar Docker/docker-compose para aceitar variaveis;
- manter o modo `mock` como padrao.

Criterio de sucesso:

- sem `OPENAI_API_KEY`, o pipeline continua rodando;
- com `OPENAI_API_KEY`, a etapa LLM real pode ser acionada.

## Passo 9: consolidar metricas da etapa LLM

Depois que a etapa estiver integrada, o relatorio pode incluir metricas como:

- quantidade de analises geradas;
- quantidade de sugestoes por categoria;
- sugestoes validadas;
- sugestoes reprovadas;
- tempo medio da etapa LLM;
- divergencias entre sugestao da LLM e resultado da ferramenta.

Entregaveis:

- CSV especifico para resultados da LLM;
- cards adicionais no dashboard;
- resumo por categoria e ferramenta.

Criterio de sucesso:

- a etapa LLM vira parte mensuravel do experimento, nao apenas um texto solto.

## Ordem recomendada de commits

1. `docs: descreve plano de integracao da llm`
2. `feat: padroniza saida simulada da llm`
3. `feat: adiciona cliente llm com modo mock`
4. `feat: monta contexto experimental para llm`
5. `feat: registra analises llm com rastreabilidade`
6. `feat: exibe analises llm no dashboard`
7. `feat: valida sugestoes llm com ferramentas`
8. `feat: gera patches llm em area isolada`
9. `docs: documenta execucao llm na aws`

## Resultado esperado

Ao final dessa evolucao, o pipeline tera uma etapa LLM auditavel, configuravel e
validada pelas ferramentas. Isso fortalece a proposta experimental porque separa
tres coisas diferentes:

- deteccao automatica feita pelas ferramentas;
- interpretacao e sugestao feita pela LLM;
- validacao objetiva feita novamente pelo pipeline.
