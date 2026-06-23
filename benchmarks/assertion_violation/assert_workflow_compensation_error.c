// Caso vulneravel: compensacao de workflow credita duas vezes o mesmo passo.
void __ESBMC_assert(_Bool condition, const char *message);

struct workflow { int debited; int refunded; int compensating_steps; };

static int net_debit(struct workflow wf)
{
    int refund = wf.refunded;
    if (wf.compensating_steps > 1) refund += wf.refunded;
    return wf.debited - refund;
}

int main(void)
{
    struct workflow wf = { .debited = 30, .refunded = 20, .compensating_steps = 2 };
    __ESBMC_assert(net_debit(wf) >= 0, "workflow compensation must not over-refund");
    return 0;
}
