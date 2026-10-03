#include <stddef.h>

typedef struct internal_hooks
{
    void *(*allocate)(size_t size);
    void (*deallocate)(void *pointer);
} internal_hooks;

typedef struct
{
    const unsigned char *content;
    size_t length;
    size_t offset;
    internal_hooks hooks;
} parse_buffer;

typedef struct
{
    const unsigned char *json;
    size_t position;
} parse_error;

int parse_buffer_sum(const parse_buffer *buffer)
{
    return (int) (buffer->length + buffer->offset + (buffer->hooks.allocate == NULL));
}

int parse_error_position(const parse_error *error)
{
    return (int) (error->position + (error->json == NULL));
}

int anonymous_forward_target(int value);

int anonymous_forward_caller(int value)
{
    return anonymous_forward_target(value) + 1;
}

int anonymous_forward_target(int value)
{
    return value + 1;
}

int anonymous_unused_dependency(int value)
{
    return value + 1;
}

static int unused_include_helper(void)
{
    return anonymous_unused_dependency(7);
}
