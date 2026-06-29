// Caso com erro: a thread tenta travar o mesmo mutex normal duas vezes.
#include <pthread.h>

static pthread_mutex_t mtx = PTHREAD_MUTEX_INITIALIZER;

static void *rotina(void *arg)
{
    (void)arg;
    pthread_mutex_lock(&mtx);
    pthread_mutex_lock(&mtx);
    pthread_mutex_unlock(&mtx);
    pthread_mutex_unlock(&mtx);
    return NULL;
}

int main(void)
{
    pthread_t t1;

    pthread_create(&t1, NULL, rotina, NULL);
    pthread_join(t1, NULL);
    return 0;
}
