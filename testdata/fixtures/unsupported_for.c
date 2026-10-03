int main(void)
{
    void *target = &&done;
    goto *target;
done:
    return 0;
}
