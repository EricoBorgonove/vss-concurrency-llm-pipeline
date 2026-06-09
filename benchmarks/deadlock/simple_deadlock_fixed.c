// Caso correto: ambas as threads usam a mesma ordem de aquisicao dos mutexes.
#include <pthread.h>

pthread_mutex_t first_mutex = PTHREAD_MUTEX_INITIALIZER;
pthread_mutex_t second_mutex = PTHREAD_MUTEX_INITIALIZER;

void *lock_in_order(void *arg) {
    (void)arg;

    pthread_mutex_lock(&first_mutex);
    pthread_mutex_lock(&second_mutex);

    pthread_mutex_unlock(&second_mutex);
    pthread_mutex_unlock(&first_mutex);

    return NULL;
}

int main(void) {
    pthread_t first_thread;
    pthread_t second_thread;

    pthread_create(&first_thread, NULL, lock_in_order, NULL);
    pthread_create(&second_thread, NULL, lock_in_order, NULL);

    pthread_join(first_thread, NULL);
    pthread_join(second_thread, NULL);

    pthread_mutex_destroy(&second_mutex);
    pthread_mutex_destroy(&first_mutex);

    return 0;
}
