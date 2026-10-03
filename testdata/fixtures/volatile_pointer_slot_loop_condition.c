static int * volatile volatile_pointer_slot;

int reject_volatile_pointer_slot(void)
{
    while (volatile_pointer_slot != 0) {
        break;
    }
    return 0;
}
