// Caso com erro: tres threads formam um ciclo de espera entre tres mutexes.
#include <pthread.h>
#include <unistd.h>

static pthread_mutex_t m1 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t m2 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t m3 = PTHREAD_MUTEX_INITIALIZER;

static void *t1_func(void *arg)
{
    (void)arg;
    pthread_mutex_lock(&m1);
    usleep(1000);
    pthread_mutex_lock(&m2);
    return NULL;
}

static void *t2_func(void *arg)
{
    (void)arg;
    pthread_mutex_lock(&m2);
    usleep(1000);
    pthread_mutex_lock(&m3);
    return NULL;
}

static void *t3_func(void *arg)
{
    (void)arg;
    pthread_mutex_lock(&m3);
    usleep(1000);
    pthread_mutex_lock(&m1);
    return NULL;
}

int main(void)
{
    pthread_t t1;
    pthread_t t2;
    pthread_t t3;

    pthread_create(&t1, NULL, t1_func, NULL);
    pthread_create(&t2, NULL, t2_func, NULL);
    pthread_create(&t3, NULL, t3_func, NULL);
    pthread_join(t1, NULL);
    pthread_join(t2, NULL);
    pthread_join(t3, NULL);
    return 0;
}
