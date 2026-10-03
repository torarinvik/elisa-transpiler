int read_first_pointer_to_vla(int count, int (*values)[count]) {
    return (*values)[0];
}
