// Caso vulneravel: calibracao composta ultrapassa a faixa segura do sensor.
void __ESBMC_assert(_Bool condition, const char *message);

struct calibration { int base; int thermal; int drift; int max_value; };

static int calibrated_value(struct calibration c)
{
    int value = c.base + c.thermal;
    if (c.drift > 4) value += c.drift * 2;
    return value;
}

int main(void)
{
    struct calibration c = { .base = 81, .thermal = 12, .drift = 6, .max_value = 100 };
    __ESBMC_assert(calibrated_value(c) <= c.max_value, "calibrated sensor value must stay in range");
    return 0;
}
