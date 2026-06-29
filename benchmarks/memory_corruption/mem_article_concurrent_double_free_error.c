// Caso com erro: duas threads podem liberar o mesmo recurso global.
#include <pthread.h>
#include <stdlib.h>
#include <unistd.h>

static int *recurso;

static void *limpar(void *arg)
{
    (void)arg;
    if (recurso != NULL) {
        usleep(1000);
        free(recurso);
        recurso = NULL;
    }
    return NULL;
}

int main(void)
{
    recurso = malloc(sizeof(*recurso));
    if (recurso == NULL) {
        return 1;
    }

    pthread_t t1;
    pthread_t t2;
    pthread_create(&t1, NULL, limpar, NULL);
    pthread_create(&t2, NULL, limpar, NULL);
    pthread_join(t1, NULL);
    pthread_join(t2, NULL);
    return 0;
}
