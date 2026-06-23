// Caso vulneravel: manifesto consolidado excede a capacidade do veiculo.
void __ESBMC_assert(_Bool condition, const char *message);

struct shipment { int pallets; int cold_boxes; int fragile_boxes; int truck_slots; };

static int required_slots(struct shipment s)
{
    return s.pallets * 2 + s.cold_boxes + (s.fragile_boxes + 1) / 2;
}

int main(void)
{
    struct shipment s = { .pallets = 6, .cold_boxes = 5, .fragile_boxes = 5, .truck_slots = 18 };
    __ESBMC_assert(required_slots(s) <= s.truck_slots, "manifest must fit truck capacity");
    return 0;
}
