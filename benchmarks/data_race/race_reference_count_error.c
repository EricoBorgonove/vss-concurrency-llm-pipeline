// Caso vulneravel: referencia global tem contador alterado por caminhos concorrentes.
#include <pthread.h>

struct object_ref {
    int refs;
    int active;
};

static struct object_ref object = {1, 1};

static void *retain_object(void *arg)
{
    (void)arg;
    if (object.active) {
        object.refs += 1;
    }
    return 0;
}

static void *release_object(void *arg)
{
    (void)arg;
    object.refs -= 1;
    if (object.refs == 0) {
        object.active = 0;
    }
    return 0;
}

int main(void)
{
    pthread_t retain_thread;
    pthread_t release_thread;

    pthread_create(&retain_thread, 0, retain_object, 0);
    pthread_create(&release_thread, 0, release_object, 0);
    pthread_join(retain_thread, 0);
    pthread_join(release_thread, 0);

    return object.refs;
}
