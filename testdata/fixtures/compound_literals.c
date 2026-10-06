struct Point {
    int x;
    int y;
};

int main(void) {
    struct Point *first = &(struct Point){.x = 3, .y = 5};
    struct Point *second = &(struct Point){.x = 3, .y = 5};
    if (first == second) return 1;

    first->x = 9;
    if (first->x != 9 || second->x != 3) return 2;

    struct Point copy = (struct Point){.y = 8, .x = 6};
    if (copy.x != 6 || copy.y != 8) return 3;

    const struct Point *readonly = &(const struct Point){.x = 2, .y = 7};
    if (readonly->x != 2 || readonly->y != 7) return 6;

    int scalar = (int){11};
    if (scalar != 11) return 7;

    if (((int[3]){2, 4, 6})[1] != 4) return 4;

    for (int index = 0; index < 3; index++) {
        int *item = (int[1]){index};
        if (item[0] != index) return 5;
    }
    return 0;
}
