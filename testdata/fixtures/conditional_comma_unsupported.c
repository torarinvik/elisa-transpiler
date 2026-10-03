static int touch(void)
{
    return 1;
}

static volatile int volatile_value;

struct Payload
{
    int value;
};

int unsupported_volatile_comma(void)
{
    return (volatile_value, 1);
}

int unsupported_record_conditional_comma(int gate)
{
    struct Payload left = {1};
    struct Payload right = {2};
    struct Payload selected = gate ? (touch(), left) : right;
    return selected.value;
}

static struct Payload make_payload(void)
{
    struct Payload payload = {3};
    return payload;
}

static int consume_payload(struct Payload payload, int marker)
{
    return payload.value + marker;
}

int unsupported_effectful_record_call_argument(void)
{
    return consume_payload(make_payload(), touch());
}
