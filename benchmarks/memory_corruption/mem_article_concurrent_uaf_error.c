// Caso com erro: uma thread libera ponteiro global enquanto outra escreve nele.
#include <pthread.h>
#include <stdlib.h>
#include <unistd.h>

static int *ptr_global;

static void *leitor_usa(void *arg)
{
    (void)arg;
    usleep(5000);
    *ptr_global = 42;
    return NULL;
}

static void *liberador(void *arg)
{
    (void)arg;
    free(ptr_global);
    return NULL;
}

int main(void)
{
    ptr_global = malloc(sizeof(*ptr_global));
    if (ptr_global == NULL) {
        return 1;
    }

    pthread_t t1;
    pthread_t t2;
    pthread_create(&t1, NULL, leitor_usa, NULL);
    pthread_create(&t2, NULL, liberador, NULL);
    pthread_join(t1, NULL);
    pthread_join(t2, NULL);
    return 0;
}
