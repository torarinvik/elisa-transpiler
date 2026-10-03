static int builtin_atomic_counter;

int reject_builtin_atomic_do(void)
{
    do {
        break;
    } while (__atomic_load_n(&builtin_atomic_counter, __ATOMIC_SEQ_CST) == 0);
    return 0;
}
