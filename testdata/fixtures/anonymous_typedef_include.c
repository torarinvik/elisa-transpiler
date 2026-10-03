#include "anonymous_typedef_include_impl.c"

int main(void)
{
    parse_buffer buffer = { NULL, 40, 2, { NULL, NULL } };
    parse_error error = { NULL, 4 };
    return parse_buffer_sum(&buffer) + parse_error_position(&error) - 48 + anonymous_forward_caller(0);
}
