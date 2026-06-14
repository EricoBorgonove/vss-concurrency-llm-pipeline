// Caso vulneravel: snapshot le contador e soma enquanto outra thread atualiza.
#include <pthread.h>

struct metrics {
    int count;
    int total;
};

static struct metrics shared_metrics = {0, 0};

static void *record_sample(void *arg)
{
    int value = *(int *)arg;
    shared_metrics.count += 1;
    shared_metrics.total += value;
    return 0;
}

static void *read_snapshot(void *arg)
{
    struct metrics *snapshot = (struct metrics *)arg;
    snapshot->count = shared_metrics.count;
    snapshot->total = shared_metrics.total;
    return 0;
}

int main(void)
{
    pthread_t writer;
    pthread_t reader;
    int value = 42;
    struct metrics snapshot = {0, 0};

    pthread_create(&writer, 0, record_sample, &value);
    pthread_create(&reader, 0, read_snapshot, &snapshot);
    pthread_join(writer, 0);
    pthread_join(reader, 0);

    return snapshot.count + snapshot.total;
}
