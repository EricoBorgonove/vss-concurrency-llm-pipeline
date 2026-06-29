// Caso com erro: thread copia texto maior que o buffer local da pilha.
#include <pthread.h>
#include <string.h>

static char input_global[80] = "TextoMuitoGrandeQueVaiEstourarOBuffereProvocarUmErroDeStack";

static void *processar_string(void *arg)
{
    (void)arg;
    char local_buffer[10];
    strcpy(local_buffer, input_global);
    return NULL;
}

int main(void)
{
    pthread_t t1;

    pthread_create(&t1, NULL, processar_string, NULL);
    pthread_join(t1, NULL);
    return 0;
}
