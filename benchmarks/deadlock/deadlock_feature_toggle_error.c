// Caso vulneravel: caminho por flag adquire os mesmos locks em ordem invertida.
#include <pthread.h>
#include <unistd.h>

static pthread_mutex_t config_lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t audit_lock = PTHREAD_MUTEX_INITIALIZER;

static void update_config(int enable_audit)
{
    pthread_mutex_lock(&config_lock);
    usleep(1000);
    if (enable_audit) {
        pthread_mutex_lock(&audit_lock);
        pthread_mutex_unlock(&audit_lock);
    }
    pthread_mutex_unlock(&config_lock);
}

static void write_audit(int reload_config)
{
    pthread_mutex_lock(&audit_lock);
    usleep(1000);
    if (reload_config) {
        pthread_mutex_lock(&config_lock);
        pthread_mutex_unlock(&config_lock);
    }
    pthread_mutex_unlock(&audit_lock);
}

static void *worker_config(void *arg)
{
    update_config(*(int *)arg);
    return 0;
}

static void *worker_audit(void *arg)
{
    write_audit(*(int *)arg);
    return 0;
}

int main(void)
{
    pthread_t t1;
    pthread_t t2;
    int enabled = 1;

    pthread_create(&t1, 0, worker_config, &enabled);
    pthread_create(&t2, 0, worker_audit, &enabled);
    pthread_join(t1, 0);
    pthread_join(t2, 0);
    return 0;
}
