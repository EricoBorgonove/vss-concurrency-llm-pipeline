// Caso vulneravel: duas threads adquirem metrics_lock e exporter_lock em ordem oposta.
#include <pthread.h>
#include <unistd.h>

static pthread_mutex_t metrics_lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t exporter_lock = PTHREAD_MUTEX_INITIALIZER;

static void *first_path(void *arg)
{
    (void)arg;
    pthread_mutex_lock(&metrics_lock);
    usleep(1000);
    pthread_mutex_lock(&exporter_lock);
    pthread_mutex_unlock(&exporter_lock);
    pthread_mutex_unlock(&metrics_lock);
    return 0;
}

static void *second_path(void *arg)
{
    (void)arg;
    pthread_mutex_lock(&exporter_lock);
    usleep(1000);
    pthread_mutex_lock(&metrics_lock);
    pthread_mutex_unlock(&metrics_lock);
    pthread_mutex_unlock(&exporter_lock);
    return 0;
}

int main(void)
{
    pthread_t a, b;
    pthread_create(&a, 0, first_path, 0);
    pthread_create(&b, 0, second_path, 0);
    pthread_join(a, 0);
    pthread_join(b, 0);
    return 0;
}
