static int shared_state = 3;

static inline int shared_helper(int value)
{
    shared_state += value;
    return value + shared_state;
}
