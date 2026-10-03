typedef _Atomic(int) AtomicCounter;

static AtomicCounter atomic_counter;

int reject_atomic_for(void)
{
    for (; atomic_counter == 0;) {
        break;
    }
    return 0;
}
