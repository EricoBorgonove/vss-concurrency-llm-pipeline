// Caso com erro: a mesma thread tenta bloquear o mesmo mutex duas vezes.
#include <pthread.h>

static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;

int main(void)
{
    pthread_mutex_lock(&lock);
    pthread_mutex_lock(&lock);
    pthread_mutex_unlock(&lock);
    return 0;
}
