// Caso correto: trylock evita espera circular ao liberar left quando right falha.
#include <pthread.h>
#include <unistd.h>

static pthread_mutex_t left = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t right = PTHREAD_MUTEX_INITIALIZER;

static void *worker(void *arg)
{
    (void)arg;

    for (int attempt = 0; attempt < 100; attempt++) {
        pthread_mutex_lock(&left);
        if (pthread_mutex_trylock(&right) == 0) {
            pthread_mutex_unlock(&right);
            pthread_mutex_unlock(&left);
            return NULL;
        }
        pthread_mutex_unlock(&left);
        usleep(100);
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
    return 0;
}
