#define ADDRESS_LABEL(label) &&label

int main(void)
{
    void *target = ADDRESS_LABEL(done);
    goto *target;
done:
    return 0;
}
