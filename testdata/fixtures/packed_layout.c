#include <stdint.h>

#pragma pack(push, 1)
typedef struct PackedLayout {
    uint16_t a;
    uint32_t b;
} PackedLayout;
#pragma pack(pop)

int main(void) {
    PackedLayout value = {7, 11};
    return sizeof(PackedLayout) == 6 && value.a == 7 && value.b == 11 ? 0 : 1;
}
