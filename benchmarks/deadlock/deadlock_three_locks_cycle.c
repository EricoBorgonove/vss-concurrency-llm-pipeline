#include <pthread.h>
#include <unistd.h>

static pthread_mutex_t lock_a = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t lock_b = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t lock_c = PTHREAD_MUTEX_INITIALIZER;

static void *worker_ab(void *arg)
{
    (void)arg;
    pthread_mutex_lock(&lock_a);
    usleep(1000);
    pthread_mutex_lock(&lock_b);
    return NULL;
}

static void *worker_bc(void *arg)
{
    (void)arg;
    pthread_mutex_lock(&lock_b);
    usleep(1000);
    pthread_mutex_lock(&lock_c);
    return NULL;
}

static void *worker_ca(void *arg)
{
    (void)arg;
    pthread_mutex_lock(&lock_c);
    usleep(1000);
    pthread_mutex_lock(&lock_a);
    return NULL;
}

int main(void)
{
    pthread_t t1;
    pthread_t t2;
    pthread_t t3;

    pthread_create(&t1, NULL, worker_ab, NULL);
    pthread_create(&t2, NULL, worker_bc, NULL);
    pthread_create(&t3, NULL, worker_ca, NULL);
    pthread_join(t1, NULL);
    pthread_join(t2, NULL);
    pthread_join(t3, NULL);
    return 0;
}
