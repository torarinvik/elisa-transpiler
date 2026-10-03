#if defined(_DEFAULT_SOURCE)
#error "translator must not inject _DEFAULT_SOURCE"
#endif

#if defined(_FORTIFY_SOURCE) && _FORTIFY_SOURCE == 0
#error "translator must not disable fortify by injecting _FORTIFY_SOURCE=0"
#endif

int main(void)
{
    return 42;
}
