// Caso vulneravel: ledger de alocacao perde bytes reservados no rollback parcial.
void __ESBMC_assert(_Bool condition, const char *message);

struct ledger { int reserved; int committed; int released; };

static int outstanding_bytes(struct ledger ledger)
{
    int outstanding = ledger.reserved + ledger.committed;
    if (ledger.released > ledger.committed) outstanding -= ledger.released;
    return outstanding;
}

int main(void)
{
    struct ledger ledger = { .reserved = 16, .committed = 10, .released = 40 };
    __ESBMC_assert(outstanding_bytes(ledger) >= 0, "allocator ledger must not become negative");
    return 0;
}
