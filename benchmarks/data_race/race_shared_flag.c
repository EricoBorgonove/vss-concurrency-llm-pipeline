#include <pthread.h>

static int ready = 0;

static void *set_ready(void *arg)
{
    (void)arg;
    ready = 1;
    return NULL;
}

static void *clear_ready(void *arg)
{
    (void)arg;
    ready = 0;
    return NULL;
}

int main(void)
{
    pthread_t t1;
    pthread_t t2;

    pthread_create(&t1, NULL, set_ready, NULL);
    pthread_create(&t2, NULL, clear_ready, NULL);
    pthread_join(t1, NULL);
    pthread_join(t2, NULL);
    return ready;
}
