// Caso correto: shared_counter e incrementado dentro de regiao protegida por mutex.
#include <pthread.h>
#include <stdio.h>

int shared_counter = 0;
pthread_mutex_t counter_mutex = PTHREAD_MUTEX_INITIALIZER;

void *increment(void *arg) {
    (void)arg;

    pthread_mutex_lock(&counter_mutex);
    shared_counter++;
    pthread_mutex_unlock(&counter_mutex);

    return NULL;
}

int main(void) {
    pthread_t first_thread;
    pthread_t second_thread;

    pthread_create(&first_thread, NULL, increment, NULL);
    pthread_create(&second_thread, NULL, increment, NULL);

    pthread_join(first_thread, NULL);
    pthread_join(second_thread, NULL);

    printf("%d\n", shared_counter);
    pthread_mutex_destroy(&counter_mutex);
    return 0;
}
