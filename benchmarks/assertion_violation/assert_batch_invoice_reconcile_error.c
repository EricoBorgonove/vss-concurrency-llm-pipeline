// Caso vulneravel: reconciliacao de lotes deixa total aprovado acima do limite.
void __ESBMC_assert(_Bool condition, const char *message);

struct invoice_batch { int approved; int pending; int disputed; int limit; };

static int reconcile(struct invoice_batch batch)
{
    int recovered = batch.pending - batch.disputed;
    if (recovered > 0) {
        batch.approved += recovered;
    }
    return batch.approved;
}

int main(void)
{
    struct invoice_batch batch = { .approved = 92, .pending = 18, .disputed = 3, .limit = 100 };
    int approved = reconcile(batch);
    __ESBMC_assert(approved <= batch.limit, "approved invoices must stay inside the batch limit");
    return 0;
}
