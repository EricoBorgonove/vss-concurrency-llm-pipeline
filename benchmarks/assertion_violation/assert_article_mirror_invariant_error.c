// Caso com erro: variaveis espelhadas podem ser observadas em estados diferentes.
#include <assert.h>
#include <pthread.h>
#include <unistd.h>

static int x = 0;
static int y = 0;

static void *atualizar(void *arg)
{
    (void)arg;
    x++;
    usleep(5000);
    y++;
    return NULL;
}

static void *checar(void *arg)
{
    (void)arg;
    usleep(1000);
    assert(x == y);
    return NULL;
}

int main(void)
{
    pthread_t t1;
    pthread_t t2;

    pthread_create(&t1, NULL, atualizar, NULL);
    pthread_create(&t2, NULL, checar, NULL);
    pthread_join(t1, NULL);
    pthread_join(t2, NULL);
    return 0;
}
