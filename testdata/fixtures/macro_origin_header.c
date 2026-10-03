#include "macro_origin.h"

void first(void)
{
    void *target = ADDRESS_LABEL(done);
    goto *target;
done:
    return;
}

int main(void)
{
    void *target = ADDRESS_LABEL(done);
    goto *target;
done:
    return 0;
}
