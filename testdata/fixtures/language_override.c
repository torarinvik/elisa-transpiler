#if !defined(__cplusplus)
#error "compile database -x c++ must override the .c filename"
#endif

#if __cplusplus < 201103L
#error "compile database C++ standard must be preserved"
#endif

#if !defined(TRANSLATOR_LANGUAGE_MARKER)
#error "compile database defines must be preserved"
#endif

int main(void)
{
    return 42;
}
