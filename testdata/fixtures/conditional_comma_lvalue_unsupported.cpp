static int side_effects;
static int left_value;
static int right_value;

static int side_effect()
{
    side_effects += 1;
    return 0;
}

int conditional_lvalue_with_comma(int gate)
{
    return gate ? (side_effect(), left_value) : right_value;
}
