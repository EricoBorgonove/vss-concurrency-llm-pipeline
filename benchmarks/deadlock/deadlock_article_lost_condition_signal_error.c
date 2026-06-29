// Caso com erro: signal ocorre antes do receptor entrar no wait.
#include <pthread.h>
#include <unistd.h>

static pthread_mutex_t mtx = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t cond = PTHREAD_COND_INITIALIZER;

static void *sinalizador(void *arg)
{
    (void)arg;
    pthread_cond_signal(&cond);
    return NULL;
}

static void *receptor(void *arg)
{
    (void)arg;
    usleep(5000);
    pthread_mutex_lock(&mtx);
    pthread_cond_wait(&cond, &mtx);
    pthread_mutex_unlock(&mtx);
    return NULL;
}

int main(void)
{
    pthread_t t1;
    pthread_t t2;

    pthread_create(&t1, NULL, sinalizador, NULL);
    pthread_create(&t2, NULL, receptor, NULL);
    pthread_join(t1, NULL);
    pthread_join(t2, NULL);
    return 0;
}
