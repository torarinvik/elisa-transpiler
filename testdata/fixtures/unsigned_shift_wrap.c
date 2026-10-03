static unsigned int shifted(void)
{
    return 0x80000000u << 1;
}

int main(void)
{
    return shifted() == 0u ? 0 : 1;
}
