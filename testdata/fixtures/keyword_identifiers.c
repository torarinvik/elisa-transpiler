static int match(int module)
{
    int value = module + 1;
    return value;
}

int main(void)
{
    int result = match(4);
    return result == 5 ? 0 : 1;
}
