#include <pthread.h>

pthread_mutex_t first_mutex = PTHREAD_MUTEX_INITIALIZER;
pthread_mutex_t second_mutex = PTHREAD_MUTEX_INITIALIZER;

void *lock_first_then_second(void *arg) {
    (void)arg;

    pthread_mutex_lock(&first_mutex);
    pthread_mutex_lock(&second_mutex);

    pthread_mutex_unlock(&second_mutex);
    pthread_mutex_unlock(&first_mutex);

    return NULL;
}

void *lock_second_then_first(void *arg) {
    (void)arg;

    pthread_mutex_lock(&second_mutex);
    pthread_mutex_lock(&first_mutex);

    pthread_mutex_unlock(&first_mutex);
    pthread_mutex_unlock(&second_mutex);

    return NULL;
}

int main(void) {
    pthread_t first_thread;
    pthread_t second_thread;

    pthread_create(&first_thread, NULL, lock_first_then_second, NULL);
    pthread_create(&second_thread, NULL, lock_second_then_first, NULL);

    pthread_join(first_thread, NULL);
    pthread_join(second_thread, NULL);

    return 0;
}
