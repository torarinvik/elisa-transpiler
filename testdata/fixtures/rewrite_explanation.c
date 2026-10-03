static int side_effect_count;
static volatile int volatile_value;

static int next_value(void)
{
    side_effect_count += 1;
    return 2;
}

int main(void)
{
    int value = 5;
    int identity = value + 0;
    int folded = 3 + 4;
    int effectful_identity = next_value() * 1;
    int volatile_identity = volatile_value + 0;
    int pruned_short_circuit = 0 && next_value();
    int selected_arm = 1 ? 9 : next_value();
    int selected_nested = value + (1 ? 2 : next_value());
    int effectful_condition = next_value() ? value : 0;
    int not_bool = value == 0;
    return identity == 5 && folded == 7 && effectful_identity == 2 && volatile_identity == 0 &&
                   pruned_short_circuit == 0 && selected_arm == 9 && selected_nested == 7 && effectful_condition == 5 && side_effect_count == 2 && not_bool == 0
               ? 0
               : 1;
}
