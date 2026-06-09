// Caso com erro: producers atualizam queue.count e items sem mutex.
#include <pthread.h>

struct queue {
    int items[4];
    int count;
};

static struct queue queue = {{0, 0, 0, 0}, 0};

static void *producer(void *arg)
{
    int value = *(int *)arg;

    queue.items[queue.count] = value;
    queue.count++;
    return NULL;
}

int main(void)
{
    pthread_t threads[4];
    int values[4] = {1, 2, 3, 4};

    for (int i = 0; i < 4; i++) {
        pthread_create(&threads[i], NULL, producer, &values[i]);
    }
    for (int i = 0; i < 4; i++) {
        pthread_join(threads[i], NULL);
    }

    return queue.count;
}
