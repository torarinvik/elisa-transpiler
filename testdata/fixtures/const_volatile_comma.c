static const volatile int const_volatile_value = 5;

int main(void)
{
    return (const_volatile_value, 1);
}
