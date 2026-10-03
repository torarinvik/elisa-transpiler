#include <stdint.h>

int main(void) {
    uint64_t value = 0;
    switch (value) {
    case UINT64_MAX:
        return 42;
    default:
        return 0;
    }
}
