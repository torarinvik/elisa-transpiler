#include "macro_origin_include.h"

void nested_origin(void)
{
    void *target = ADDRESS_LABEL(done);
    goto *target;
done:
    return;
}
