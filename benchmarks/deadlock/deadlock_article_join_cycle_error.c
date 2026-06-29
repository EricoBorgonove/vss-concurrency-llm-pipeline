// Caso com erro: a thread principal e a thread auxiliar esperam uma pela outra.
#include <pthread.h>

static pthread_t main_thread;

static void *rotina_b(void *arg)
{
    (void)arg;
    pthread_join(main_thread, NULL);
    return NULL;
}

int main(void)
{
    main_thread = pthread_self();
    pthread_t t_b;

    pthread_create(&t_b, NULL, rotina_b, NULL);
    pthread_join(t_b, NULL);
    return 0;
}
