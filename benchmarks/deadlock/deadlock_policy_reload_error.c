// Caso vulneravel: duas threads adquirem policy_lock e rules_lock em ordem oposta.
#include <pthread.h>
#include <unistd.h>

static pthread_mutex_t policy_lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t rules_lock = PTHREAD_MUTEX_INITIALIZER;

static void *first_path(void *arg)
{
    (void)arg;
    pthread_mutex_lock(&policy_lock);
    usleep(1000);
    pthread_mutex_lock(&rules_lock);
    pthread_mutex_unlock(&rules_lock);
    pthread_mutex_unlock(&policy_lock);
    return 0;
}

static void *second_path(void *arg)
{
    (void)arg;
    pthread_mutex_lock(&rules_lock);
    usleep(1000);
    pthread_mutex_lock(&policy_lock);
    pthread_mutex_unlock(&policy_lock);
    pthread_mutex_unlock(&rules_lock);
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
