// Caso com erro: resource_a e resource_b sao adquiridos em ordens opostas.
#include <pthread.h>
#include <unistd.h>

struct resource_pair {
    pthread_mutex_t resource_a;
    pthread_mutex_t resource_b;
};

static struct resource_pair pair = {
    PTHREAD_MUTEX_INITIALIZER,
    PTHREAD_MUTEX_INITIALIZER
};

static void *use_a_then_b(void *arg)
{
    (void)arg;
    pthread_mutex_lock(&pair.resource_a);
    usleep(1000);
    pthread_mutex_lock(&pair.resource_b);
    return NULL;
}

static void *use_b_then_a(void *arg)
{
    (void)arg;
    pthread_mutex_lock(&pair.resource_b);
    usleep(1000);
    pthread_mutex_lock(&pair.resource_a);
    return NULL;
}

int main(void)
{
    pthread_t t1;
    pthread_t t2;

    pthread_create(&t1, NULL, use_a_then_b, NULL);
    pthread_create(&t2, NULL, use_b_then_a, NULL);
    pthread_join(t1, NULL);
    pthread_join(t2, NULL);
    return 0;
}
