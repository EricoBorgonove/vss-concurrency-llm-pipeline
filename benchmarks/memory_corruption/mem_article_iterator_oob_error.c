// Caso com erro: indice capturado antes da reducao do limite acessa item invalido.
#include <pthread.h>
#include <stdlib.h>
#include <unistd.h>

static int *dados;
static int limite = 5;

static void *leitor(void *arg)
{
    (void)arg;
    int limite_local = limite;
    usleep(5000);
    int soma = 0;
    for (int i = 0; i < limite_local; i++) {
        soma += dados[i];
    }
    return (void *)(long)soma;
}

static void *modificador(void *arg)
{
    (void)arg;
    limite = 2;
    int *reduzido = realloc(dados, (size_t)limite * sizeof(*dados));
    if (reduzido != NULL) {
        dados = reduzido;
    }
    return NULL;
}

int main(void)
{
    dados = malloc((size_t)limite * sizeof(*dados));
    if (dados == NULL) {
        return 1;
    }
    for (int i = 0; i < limite; i++) {
        dados[i] = i + 1;
    }

    pthread_t t1;
    pthread_t t2;
    pthread_create(&t1, NULL, leitor, NULL);
    pthread_create(&t2, NULL, modificador, NULL);
    pthread_join(t1, NULL);
    pthread_join(t2, NULL);
    free(dados);
    return 0;
}
