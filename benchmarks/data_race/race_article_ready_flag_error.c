// Caso com erro: uma thread le uma flag enquanto outra escreve sem sincronizacao.
#include <pthread.h>

static int flag_pronto = 0;

static void *escritor(void *arg)
{
    (void)arg;
    flag_pronto = 1;
    return NULL;
}

static void *leitor(void *arg)
{
    (void)arg;
    while (!flag_pronto) {
    }
    return NULL;
}

int main(void)
{
    pthread_t t1;
    pthread_t t2;

    pthread_create(&t1, NULL, leitor, NULL);
    pthread_create(&t2, NULL, escritor, NULL);
    pthread_join(t1, NULL);
    pthread_join(t2, NULL);
    return 0;
}
