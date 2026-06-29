// Caso com erro: leitura inicial do ponteiro global ocorre fora do mutex.
#include <pthread.h>
#include <stdlib.h>

static int *ptr = NULL;
static pthread_mutex_t mtx = PTHREAD_MUTEX_INITIALIZER;

static void *inicializar(void *arg)
{
    (void)arg;
    if (ptr == NULL) {
        pthread_mutex_lock(&mtx);
        if (ptr == NULL) {
            ptr = malloc(sizeof(*ptr));
            if (ptr != NULL) {
                *ptr = 1;
            }
        }
        pthread_mutex_unlock(&mtx);
    }
    return NULL;
}

int main(void)
{
    pthread_t t1;
    pthread_t t2;

    pthread_create(&t1, NULL, inicializar, NULL);
    pthread_create(&t2, NULL, inicializar, NULL);
    pthread_join(t1, NULL);
    pthread_join(t2, NULL);

    free(ptr);
    return 0;
}
