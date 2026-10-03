namespace first_scope {
    typedef unsigned int word;
}

namespace second_scope {
    using word = unsigned long long;
}

first_scope::word first_word(first_scope::word value) {
    return value;
}

second_scope::word second_word(second_scope::word value) {
    return value;
}

int main() {
    return first_word(17) != 17 || second_word(19) != 19;
}
