#include <pthread.h>

static int shared_value = 0;

static void *reader(void *arg)
{
    int *snapshot = arg;

    *snapshot = shared_value;
    return NULL;
}

static void *writer(void *arg)
{
    (void)arg;
    shared_value = 99;
    return NULL;
}

int main(void)
{
    pthread_t t1;
    pthread_t t2;
    int snapshot = 0;

    pthread_create(&t1, NULL, reader, &snapshot);
    pthread_create(&t2, NULL, writer, NULL);
    pthread_join(t1, NULL);
    pthread_join(t2, NULL);
    return snapshot;
}
