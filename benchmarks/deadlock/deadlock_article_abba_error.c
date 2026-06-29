// Caso com erro: duas threads adquirem os mesmos mutexes em ordens opostas.
#include <pthread.h>
#include <unistd.h>

static pthread_mutex_t mtx_a = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mtx_b = PTHREAD_MUTEX_INITIALIZER;

static void *thread1(void *arg)
{
    (void)arg;
    pthread_mutex_lock(&mtx_a);
    usleep(1000);
    pthread_mutex_lock(&mtx_b);
    pthread_mutex_unlock(&mtx_b);
    pthread_mutex_unlock(&mtx_a);
    return NULL;
}

static void *thread2(void *arg)
{
    (void)arg;
    pthread_mutex_lock(&mtx_b);
    usleep(1000);
    pthread_mutex_lock(&mtx_a);
    pthread_mutex_unlock(&mtx_a);
    pthread_mutex_unlock(&mtx_b);
    return NULL;
}

int main(void)
{
    pthread_t t1;
    pthread_t t2;

    pthread_create(&t1, NULL, thread1, NULL);
    pthread_create(&t2, NULL, thread2, NULL);
    pthread_join(t1, NULL);
    pthread_join(t2, NULL);
    return 0;
}
