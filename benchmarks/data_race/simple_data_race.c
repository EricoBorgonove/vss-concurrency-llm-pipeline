// Caso com erro: shared_counter e incrementado por threads sem mutex.
#include <pthread.h>
#include <stdio.h>

int shared_counter = 0;

void *increment(void *arg) {
    (void)arg;
    shared_counter++;
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
    return 0;
}
