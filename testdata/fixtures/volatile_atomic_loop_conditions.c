typedef volatile int VolatileCounter;

static VolatileCounter volatile_counter;

int accept_pointer_to_volatile_value(volatile int *pointer)
{
    while (pointer != 0) {
        break;
    }
    return 0;
}

int reject_volatile_while(void)
{
    while (volatile_counter == 0) {
        break;
    }
    return 0;
}
