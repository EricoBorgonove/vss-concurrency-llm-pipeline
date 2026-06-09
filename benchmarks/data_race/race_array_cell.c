// Caso com erro: duas threads escrevem em values[0] sem sincronizacao.
#include <pthread.h>

static int values[2] = {0, 0};

static void *write_one(void *arg)
{
    (void)arg;
    values[0] = 1;
    return NULL;
}

static void *write_two(void *arg)
{
    (void)arg;
    values[0] = 2;
    return NULL;
}

int main(void)
{
    pthread_t t1;
    pthread_t t2;

    pthread_create(&t1, NULL, write_one, NULL);
    pthread_create(&t2, NULL, write_two, NULL);
    pthread_join(t1, NULL);
    pthread_join(t2, NULL);
    return values[0];
}
