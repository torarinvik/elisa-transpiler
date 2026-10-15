int leaf(int value);

int middle(int value)
{
    return leaf(value);
}

int main(void)
{
    return middle(42);
}
