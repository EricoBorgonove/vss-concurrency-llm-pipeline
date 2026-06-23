// Caso vulneravel: merge de replicas reduz o epoch publicado.
void __ESBMC_assert(_Bool condition, const char *message);

struct replica { int local_epoch; int remote_epoch; int conflict; };

static int merged_epoch(struct replica r)
{
    if (r.conflict) return r.remote_epoch - 1;
    return r.local_epoch > r.remote_epoch ? r.local_epoch : r.remote_epoch;
}

int main(void)
{
    struct replica r = { .local_epoch = 15, .remote_epoch = 12, .conflict = 1 };
    int epoch = merged_epoch(r);
    __ESBMC_assert(epoch >= r.local_epoch, "merged epoch must be monotonic");
    return 0;
}
