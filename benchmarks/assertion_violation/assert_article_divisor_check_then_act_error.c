// Caso com erro: divisor pode virar zero entre a checagem e o uso.
#include <assert.h>
#include <pthread.h>
#include <unistd.h>

static int divisor = 5;
static int resultado = 0;

static void *zerar(void *arg)
{
    (void)arg;
    usleep(1000);
    divisor = 0;
    return NULL;
}

static void *calcular(void *arg)
{
    (void)arg;
    assert(divisor != 0);
    usleep(5000);
    resultado = 100 / divisor;
    return NULL;
}

int main(void)
{
    pthread_t t1;
    pthread_t t2;

    pthread_create(&t1, NULL, calcular, NULL);
    pthread_create(&t2, NULL, zerar, NULL);
    pthread_join(t1, NULL);
    pthread_join(t2, NULL);
    return resultado == 0;
}
