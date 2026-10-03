#include "shared.h"

static int project_internal_state = 20;

static int helper(int value)
{
    return value + 20;
}

int project_internal_beta(void)
{
    static int local_state = 2;
    project_internal_state += 1;
    local_state += 1;
    return helper(2) + shared_helper(2) + project_internal_state + local_state;
}
