static int add(int left, int right)
{
    return left + right;
}

static const char *spacing(void)
{
    return "left  right";
}

static int static_value(void)
{
    static int count = 1;
    return count;
}

int main(void)
{
    int value = add(20, 22);
    return value;
}
