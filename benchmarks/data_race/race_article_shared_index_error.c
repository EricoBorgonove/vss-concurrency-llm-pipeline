// Caso com erro: threads alteram indice compartilhado usado para escrever no buffer.
#include <pthread.h>

static int buffer[10];
static int indice = 0;

static void *inserir(void *arg)
{
    (void)arg;
    buffer[indice] = 5;
    indice++;
    return NULL;
}

int main(void)
{
    pthread_t t1;
    pthread_t t2;

    pthread_create(&t1, NULL, inserir, NULL);
    pthread_create(&t2, NULL, inserir, NULL);
    pthread_join(t1, NULL);
    pthread_join(t2, NULL);
    return buffer[0] == 0;
}
