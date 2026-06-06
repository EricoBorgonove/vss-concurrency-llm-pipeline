#include <pthread.h>
#include <unistd.h>

static pthread_mutex_t left = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t right = PTHREAD_MUTEX_INITIALIZER;

static void lock_pair(int reverse)
{
    if (reverse) {
        pthread_mutex_lock(&right);
        usleep(1000);
        pthread_mutex_lock(&left);
    } else {
        pthread_mutex_lock(&left);
        usleep(1000);
        pthread_mutex_lock(&right);
    }
}

static void *worker_left(void *arg)
{
    (void)arg;
    lock_pair(0);
    return NULL;
}

static void *worker_right(void *arg)
{
    (void)arg;
    lock_pair(1);
    return NULL;
}

int main(void)
{
    pthread_t t1;
    pthread_t t2;

    pthread_create(&t1, NULL, worker_left, NULL);
    pthread_create(&t2, NULL, worker_right, NULL);
    pthread_join(t1, NULL);
    pthread_join(t2, NULL);
    return 0;
}
