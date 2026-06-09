#include <pthread.h>

struct queue {
    int items[4];
    int count;
    pthread_mutex_t lock;
};

static struct queue queue = {{0, 0, 0, 0}, 0, PTHREAD_MUTEX_INITIALIZER};

static void *producer(void *arg)
{
    int value = *(int *)arg;

    pthread_mutex_lock(&queue.lock);
    queue.items[queue.count] = value;
    queue.count++;
    pthread_mutex_unlock(&queue.lock);
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

    return queue.count == 4 ? 0 : 1;
}
