static int nested_in_false_arm(int outer, int inner)
{
    return outer ? 10 : inner ? 20 : 30;
}

static int nested_in_true_arm(int outer, int inner)
{
    return outer ? (inner ? 40 : 50) : 60;
}

static int nested_with_sizeof_conditions(int fallback)
{
    return sizeof(double) == sizeof(float)
        ? fallback
        : sizeof(double) == sizeof(double) ? fallback + 1 : fallback + 2;
}

int main(void)
{
    if (nested_in_false_arm(1, 0) != 10 ||
        nested_in_false_arm(0, 1) != 20 ||
        nested_in_false_arm(0, 0) != 30 ||
        nested_in_true_arm(1, 1) != 40 ||
        nested_in_true_arm(1, 0) != 50 ||
        nested_in_true_arm(0, 1) != 60 ||
        nested_with_sizeof_conditions(8) != (sizeof(double) == sizeof(float) ? 8 : 9))
    {
        return 1;
    }
    return 0;
}
