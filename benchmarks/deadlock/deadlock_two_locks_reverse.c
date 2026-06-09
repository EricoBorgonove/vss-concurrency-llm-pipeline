// Caso com erro: duas threads adquirem first e second em ordem inversa.
#include <pthread.h>
#include <unistd.h>

static pthread_mutex_t first = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t second = PTHREAD_MUTEX_INITIALIZER;

static void *worker_a(void *arg)
{
    (void)arg;
    pthread_mutex_lock(&first);
    usleep(1000);
    pthread_mutex_lock(&second);
    pthread_mutex_unlock(&second);
    pthread_mutex_unlock(&first);
    return NULL;
}

static void *worker_b(void *arg)
{
    (void)arg;
    pthread_mutex_lock(&second);
    usleep(1000);
    pthread_mutex_lock(&first);
    pthread_mutex_unlock(&first);
    pthread_mutex_unlock(&second);
    return NULL;
}

int main(void)
{
    pthread_t t1;
    pthread_t t2;

    pthread_create(&t1, NULL, worker_a, NULL);
    pthread_create(&t2, NULL, worker_b, NULL);
    pthread_join(t1, NULL);
    pthread_join(t2, NULL);
    return 0;
}
