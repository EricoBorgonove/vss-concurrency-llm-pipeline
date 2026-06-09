#include <pthread.h>

struct config {
    int version;
    int enabled;
};

static struct config config = {1, 0};

static void *reload_config(void *arg)
{
    (void)arg;
    config.version++;
    config.enabled = 1;
    return NULL;
}

static void *read_config(void *arg)
{
    struct config *snapshot = arg;

    snapshot->version = config.version;
    snapshot->enabled = config.enabled;
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
    return snapshot.enabled;
}
