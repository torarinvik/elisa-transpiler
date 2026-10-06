union Payload {
    int integer;
    double real;
};

int main(void) {
    return ((union Payload[2]){{.integer = 4}, {.integer = 7}})[1].integer;
}
