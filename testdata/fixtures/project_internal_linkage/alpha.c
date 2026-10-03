#include "shared.h"

static int project_internal_state = 10;

static int helper(int value)
{
    return value + 10;
}

int project_internal_alpha(void)
{
    static int local_state = 2;
    int (*callback)(int) = helper;
    project_internal_state += 1;
    local_state += 1;
    return callback(1) + shared_helper(1) + project_internal_state + local_state;
}
