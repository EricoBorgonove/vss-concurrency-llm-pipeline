// Caso com erro: duas threads incrementam o mesmo contador global sem mutex.
#include <pthread.h>

static int contador = 0;

static void *incrementar(void *arg)
{
    (void)arg;
    for (int i = 0; i < 10000; i++) {
        contador++;
    }
    return NULL;
}

int main(void)
{
    pthread_t t1;
    pthread_t t2;

    pthread_create(&t1, NULL, incrementar, NULL);
    pthread_create(&t2, NULL, incrementar, NULL);
    pthread_join(t1, NULL);
    pthread_join(t2, NULL);
    return contador == 0;
}
