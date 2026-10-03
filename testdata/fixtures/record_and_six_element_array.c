struct SixFields {
    int first;
    int second;
    int third;
    int fourth;
    int fifth;
    int sixth;
};

struct SixElementArray {
    int values[6];
};

int main(void) {
    struct SixFields fields = {1, 2, 3, 4, 5, 6};
    struct SixElementArray record = {{7, 11, 13, 17, 19, 23}};
    return fields.first == 1 && fields.second == 2 && fields.third == 3 &&
           fields.fourth == 4 && fields.fifth == 5 && fields.sixth == 6 &&
           record.values[0] == 7 && record.values[1] == 11 &&
           record.values[2] == 13 && record.values[3] == 17 &&
           record.values[4] == 19 && record.values[5] == 23 ? 0 : 1;
}
