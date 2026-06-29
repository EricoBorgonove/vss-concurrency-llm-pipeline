// Caso com erro: transferencia temporariamente quebra invariante de soma total.
#include <assert.h>
#include <pthread.h>
#include <unistd.h>

static int conta_a = 100;
static int conta_b = 100;

static void *transferir(void *arg)
{
    (void)arg;
    conta_a -= 20;
    usleep(5000);
    conta_b += 20;
    return NULL;
}

static void *verificar_invariante(void *arg)
{
    (void)arg;
    usleep(1000);
    assert((conta_a + conta_b) == 200);
    return NULL;
}

int main(void)
{
    pthread_t t1;
    pthread_t t2;

    pthread_create(&t1, NULL, transferir, NULL);
    pthread_create(&t2, NULL, verificar_invariante, NULL);
    pthread_join(t1, NULL);
    pthread_join(t2, NULL);
    return 0;
}
