#include <pthread.h>

static int counter = 0;

static void *worker(void *arg)
{
    (void)arg;
    for (int i = 0; i < 1000; i++) {
        counter++;
    }
    return NULL;
}

int main(void)
{
    pthread_t t1;
    pthread_t t2;

    pthread_create(&t1, NULL, worker, NULL);
    pthread_create(&t2, NULL, worker, NULL);
    pthread_join(t1, NULL);
    pthread_join(t2, NULL);
    return counter == 2000 ? 0 : 1;
}
