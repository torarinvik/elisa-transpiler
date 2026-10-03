struct Node
{
    int value;
};

static int pointer_calls;
static int integer_calls;

static struct Node *choose_node(struct Node *node)
{
    pointer_calls++;
    return node;
}

static int choose_tag(void)
{
    integer_calls++;
    return 5;
}

static int consume(struct Node *node, int tag)
{
    return node->value + tag;
}

int main(void)
{
    struct Node node = { .value = 37 };
    int result = consume(choose_node(&node), choose_tag());
    if (result != 42 || pointer_calls != 1 || integer_calls != 1)
        return 1;
    return 0;
}
