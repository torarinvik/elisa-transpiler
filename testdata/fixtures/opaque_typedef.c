typedef struct opaque_handle opaque_handle;
typedef struct opaque_context *opaque_context;

extern opaque_context create_context(void);
extern void use_context(opaque_context context);

int main(void) {
    opaque_context context = create_context();
    use_context(context);
    return context != 0 ? 0 : 1;
}
