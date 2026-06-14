// Caso vulneravel: rebalanceamento pode deixar estoque negativo em um deposito.
void __ESBMC_assert(_Bool condition, const char *message);

struct warehouse {
    int primary;
    int reserve;
    int demand;
};

static void rebalance(struct warehouse *item)
{
    int deficit = item->demand - item->primary;
    if (deficit > 0) {
        item->primary += deficit;
        item->reserve -= deficit;
    }
}

int main(void)
{
    struct warehouse item = { .primary = 2, .reserve = 3, .demand = 7 };

    rebalance(&item);

    __ESBMC_assert(item.reserve >= 0, "reserve stock must not be negative");
    return 0;
}
