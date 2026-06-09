// Codigo aleatorio: deve acionar TSAN e detector de deadlock por mutexes.
#include <pthread.h>

pthread_mutex_t first_lock = PTHREAD_MUTEX_INITIALIZER;
pthread_mutex_t second_lock = PTHREAD_MUTEX_INITIALIZER;

void *first_worker(void *arg)
{
    (void)arg;
    pthread_mutex_lock(&first_lock);
    pthread_mutex_lock(&second_lock);
    pthread_mutex_unlock(&second_lock);
    pthread_mutex_unlock(&first_lock);
    return NULL;
}

void *second_worker(void *arg)
{
    (void)arg;
    pthread_mutex_lock(&second_lock);
    pthread_mutex_lock(&first_lock);
    pthread_mutex_unlock(&first_lock);
    pthread_mutex_unlock(&second_lock);
    return NULL;
}

int main(void)
{
    pthread_t first;
    pthread_t second;

    pthread_create(&first, NULL, first_worker, NULL);
    pthread_create(&second, NULL, second_worker, NULL);
    pthread_join(first, NULL);
    pthread_join(second, NULL);
    return 0;
}
