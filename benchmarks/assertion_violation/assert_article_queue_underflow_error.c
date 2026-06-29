// Caso com erro: dois consumidores decrementam tamanho de fila sem sincronizacao.
#include <assert.h>
#include <pthread.h>

static int tamanho_fila = 1;

static void *consumidor(void *arg)
{
    (void)arg;
    tamanho_fila--;
    return NULL;
}

int main(void)
{
    pthread_t t1;
    pthread_t t2;

    pthread_create(&t1, NULL, consumidor, NULL);
    pthread_create(&t2, NULL, consumidor, NULL);
    pthread_join(t1, NULL);
    pthread_join(t2, NULL);
    assert(tamanho_fila >= 0);
    return 0;
}
