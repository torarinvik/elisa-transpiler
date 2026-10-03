#define INLINE inline

INLINE int increment(int value)
{
    return value + 1;
}

int main(void)
{
    return increment(41) == 42 ? 0 : 1;
}
