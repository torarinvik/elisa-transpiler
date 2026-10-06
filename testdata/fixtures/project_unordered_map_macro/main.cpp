#include "keyboard.h"

int main()
{
    mark_key_flag(7);
    if (!KEY_FLAG_IS_SET(7))
        return 1;

    KEY_FLAG_CLEAR(7);
    if (KEY_FLAG_IS_SET(7))
        return 2;

    key_flags[9] = -1;
    if (!KEY_FLAG_IS_SET(9))
        return 3;

    return 0;
}
