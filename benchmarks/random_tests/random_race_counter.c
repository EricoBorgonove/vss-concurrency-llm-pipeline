// Codigo aleatorio: deve acionar TSAN por uso de pthread.
#include <pthread.h>
#include <stdio.h>

int counter = 0;

void *increment(void *arg)
{
    (void)arg;
    counter++;
    return NULL;
}

int main(void)
{
    pthread_t first;
    pthread_t second;

    pthread_create(&first, NULL, increment, NULL);
    pthread_create(&second, NULL, increment, NULL);
    pthread_join(first, NULL);
    pthread_join(second, NULL);

    printf("%d\n", counter);
    return 0;
}
