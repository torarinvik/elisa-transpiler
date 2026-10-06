static int side_effect_count;
static volatile int volatile_value;

static int next_value(void)
{
    side_effect_count += 1;
    return 2;
}

static int signed_shift_by_zero(int value)
{
    return value << 0;
}

static unsigned int unsigned_shift_by_zero(unsigned int value)
{
    return value << 0;
}

static int signed_right_shift_by_zero(int value)
{
    return value >> 0;
}

static unsigned int unsigned_right_shift_by_zero(unsigned int value)
{
    return value >> 0;
}

int main(void)
{
    int value = 5;
    int identity = value + 0;
    int folded = 3 + 4;
    int effectful_identity = next_value() * 1;
    int effectful_zero = next_value() * 0;
    int effectful_equal_arms = next_value() ? 6 : 6;
    int volatile_identity = volatile_value + 0;
    int pruned_short_circuit = 0 && next_value();
    int selected_arm = 1 ? 9 : next_value();
    int selected_nested = value + (1 ? 2 : next_value());
    int effectful_condition = next_value() ? value : 0;
    int not_bool = value == 0;
    int signed_shift = signed_shift_by_zero(4);
    unsigned int unsigned_shift = unsigned_shift_by_zero(5u);
    int signed_right_shift = signed_right_shift_by_zero(-8);
    unsigned int unsigned_right_shift = unsigned_right_shift_by_zero(9u);
    return identity == 5 && folded == 7 && effectful_identity == 2 && effectful_zero == 0 && effectful_equal_arms == 6 && volatile_identity == 0 &&
                   pruned_short_circuit == 0 && selected_arm == 9 && selected_nested == 7 && effectful_condition == 5 && side_effect_count == 4 && not_bool == 0 && signed_shift == 4 && unsigned_shift == 5u && signed_right_shift == -8 && unsigned_right_shift == 9u
               ? 0
               : 1;
}
