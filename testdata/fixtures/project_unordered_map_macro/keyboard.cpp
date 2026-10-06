#include "keyboard.h"

std::unordered_map<key_code, key_flag> key_flags;

void mark_key_flag(key_code code)
{
    key_flags[code] = 1;
}
