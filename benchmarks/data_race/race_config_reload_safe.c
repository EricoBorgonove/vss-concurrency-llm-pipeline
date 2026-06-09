#include <pthread.h>

struct config {
    int version;
    int enabled;
};

static struct config config = {1, 0};
static pthread_mutex_t config_lock = PTHREAD_MUTEX_INITIALIZER;

static void *reload_config(void *arg)
{
    (void)arg;
    pthread_mutex_lock(&config_lock);
    config.version++;
    config.enabled = 1;
    pthread_mutex_unlock(&config_lock);
    return NULL;
}

static void *read_config(void *arg)
{
    struct config *snapshot = arg;

    pthread_mutex_lock(&config_lock);
    *snapshot = config;
    pthread_mutex_unlock(&config_lock);
    return NULL;
}

int main(void)
{
    pthread_t reader;
    pthread_t writer;
    struct config snapshot = {0, 0};

    pthread_create(&reader, NULL, read_config, &snapshot);
    pthread_create(&writer, NULL, reload_config, NULL);
    pthread_join(reader, NULL);
    pthread_join(writer, NULL);
    return snapshot.version < 0;
}
