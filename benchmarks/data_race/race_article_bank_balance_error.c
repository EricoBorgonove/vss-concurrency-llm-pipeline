// Caso com erro: duas operacoes read-modify-write alteram saldo sem lock.
#include <pthread.h>

static float saldo = 100.0f;

static void *sacar(void *arg)
{
    (void)arg;
    float local = saldo;
    saldo = local - 10.0f;
    return NULL;
}

int main(void)
{
    pthread_t t1;
    pthread_t t2;

    pthread_create(&t1, NULL, sacar, NULL);
    pthread_create(&t2, NULL, sacar, NULL);
    pthread_join(t1, NULL);
    pthread_join(t2, NULL);
    return saldo < 0.0f;
}
