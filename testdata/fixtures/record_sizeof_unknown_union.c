union UnknownRecordLayout {
    int integer_value;
    double floating_value;
};

int main(void) {
    return (int)sizeof(union UnknownRecordLayout);
}
