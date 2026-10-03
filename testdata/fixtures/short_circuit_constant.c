static int calls;

static int side_effect(void)
{
    ++calls;
    return 1;
}

int main(void)
{
    if (0 && side_effect()) {
        return 7;
    }
    if (1 || side_effect()) {
        return calls;
    }
    return 9;
}
