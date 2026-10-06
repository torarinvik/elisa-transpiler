#pragma once

#include <cstdint>
#include <unordered_map>

using key_code = int;
using key_flag = std::int8_t;

extern std::unordered_map<key_code, key_flag> key_flags;

#define KEY_FLAG_IS_SET(code) (key_flags[(code)] != 0)
#define KEY_FLAG_CLEAR(code) (key_flags[(code)] = 0)

void mark_key_flag(key_code code);
