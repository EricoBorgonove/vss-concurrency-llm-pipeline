// Caso com erro: inicializacao preguicosa de global_service ocorre sem lock.
#include <pthread.h>
#include <stdlib.h>

struct service {
    int ready;
};

static struct service *global_service = NULL;

static void *get_service(void *arg)
{
    (void)arg;
    if (global_service == NULL) {
        global_service = malloc(sizeof(*global_service));
        global_service->ready = 1;
    }
    return NULL;
}

int main(void)
{
    pthread_t t1;
    pthread_t t2;

    pthread_create(&t1, NULL, get_service, NULL);
    pthread_create(&t2, NULL, get_service, NULL);
    pthread_join(t1, NULL);
    pthread_join(t2, NULL);

    free(global_service);
    return 0;
}
