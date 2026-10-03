static int selected_true_calls;
static int selected_false_calls;
static int second_argument_calls;
static int index_effect_calls;
static int assigned_rhs_true_calls;
static int assigned_rhs_false_calls;
static int short_circuit_effect_calls;
static int indexed_values[2] = {11, 22};

struct IndexedRecord
{
    int value;
};

static struct IndexedRecord indexed_records[2] = {{33}, {44}};

extern int abs(int value);

static int mark_selected_true(void)
{
    ++selected_true_calls;
    return 0;
}

static int mark_selected_false(void)
{
    ++selected_false_calls;
    return 0;
}

static int mark_second_argument(void)
{
    ++second_argument_calls;
    return 0;
}

static int mark_index(void)
{
    ++index_effect_calls;
    return 0;
}

static int mark_assigned_rhs_true(void)
{
    ++assigned_rhs_true_calls;
    return 0;
}

static int mark_assigned_rhs_false(void)
{
    ++assigned_rhs_false_calls;
    return 0;
}

static int mark_short_circuit_effect(void)
{
    ++short_circuit_effect_calls;
    return 0;
}

static int combine(int first, int second)
{
    return first + second;
}

int main(void)
{
    int selector = 1;
    int true_result = combine(
        selector ? (mark_selected_true(), 40) : (mark_selected_false(), 90),
        mark_second_argument() + 2);
    if (true_result != 42 || selected_true_calls != 1 ||
        selected_false_calls != 0 || second_argument_calls != 1) {
        return 1;
    }

    int nested_true_result = combine(
        10 + (selector ? (mark_selected_true(), 30)
                       : (mark_selected_false(), 80)),
        1);
    if (nested_true_result != 41 || selected_true_calls != 2 ||
        selected_false_calls != 0) {
        return 1;
    }

    selector = 0;
    int false_result = combine(
        selector ? (mark_selected_true(), 40) : (mark_selected_false(), 90),
        (mark_second_argument(), 3));
    if (false_result != 93 || selected_true_calls != 2 ||
        selected_false_calls != 1 || second_argument_calls != 2) {
        return 1;
    }

    int nested_false_result = combine(
        10 + (selector ? (mark_selected_true(), 30)
                       : (mark_selected_false(), 80)),
        1);
    if (nested_false_result != 91 || selected_true_calls != 2 ||
        selected_false_calls != 2 || second_argument_calls != 2) {
        return 1;
    }

    int external_result = abs(
        selector ? (mark_selected_true(), -6) : (mark_selected_false(), -7));
    if (external_result != 7 || selected_true_calls != 2 ||
        selected_false_calls != 3 || second_argument_calls != 2) {
        return 1;
    }

    selector = 1;
    int indexed_true_result = indexed_values[
        selector ? (mark_index(), 0) : (mark_index(), 1)];
    if (indexed_true_result != 11 || index_effect_calls != 1) {
        return 1;
    }

    selector = 0;
    int indexed_false_result = indexed_values[
        selector ? (mark_index(), 0) : (mark_index(), 1)];
    if (indexed_false_result != 22 || index_effect_calls != 2) {
        return 1;
    }

    selector = 1;
    int member_true_result = indexed_records[
        selector ? (mark_index(), 0) : (mark_index(), 1)].value;
    if (member_true_result != 33 || index_effect_calls != 3) {
        return 1;
    }

    selector = 0;
    int member_false_result = indexed_records[
        selector ? (mark_index(), 0) : (mark_index(), 1)].value;
    if (member_false_result != 44 || index_effect_calls != 4) {
        return 1;
    }

    selector = 1;
    indexed_records[selector ? (mark_index(), 0) : (mark_index(), 1)].value = 55;
    if (indexed_records[0].value != 55 || index_effect_calls != 5) {
        return 1;
    }

    selector = 0;
    int assigned_member_value =
        (indexed_records[selector ? (mark_index(), 0) : (mark_index(), 1)].value = 66);
    if (assigned_member_value != 66 || indexed_records[1].value != 66 ||
        index_effect_calls != 6) {
        return 1;
    }

    selector = 1;
    int assigned_rhs_value =
        (indexed_records[0].value = selector
            ? (mark_assigned_rhs_true(), 71)
            : (mark_assigned_rhs_false(), 72));
    if (assigned_rhs_value != 71 || indexed_records[0].value != 71 ||
        assigned_rhs_true_calls != 1 || assigned_rhs_false_calls != 0) {
        return 1;
    }

    selector = 0;
    indexed_records[1].value = selector
        ? (mark_assigned_rhs_true(), 81)
        : (mark_assigned_rhs_false(), 82);
    if (indexed_records[1].value != 82 || assigned_rhs_true_calls != 1 ||
        assigned_rhs_false_calls != 1) {
        return 1;
    }

    selector = 0;
    int and_skipped = selector && (mark_short_circuit_effect(), 7);
    if (and_skipped != 0 || short_circuit_effect_calls != 0) {
        return 1;
    }

    selector = 1;
    int and_taken = selector && (mark_short_circuit_effect(), 7);
    if (and_taken != 1 || short_circuit_effect_calls != 1) {
        return 1;
    }

    int nested_and = selector &&
        (selector ? (mark_short_circuit_effect(), 1) : 0);
    if (nested_and != 1 || short_circuit_effect_calls != 2) {
        return 1;
    }

    int or_skipped = selector || (mark_short_circuit_effect(), 0);
    if (or_skipped != 1 || short_circuit_effect_calls != 2) {
        return 1;
    }

    selector = 0;
    int or_taken = selector || (mark_short_circuit_effect(), 0);
    if (or_taken != 0 || short_circuit_effect_calls != 3) {
        return 1;
    }

    int if_result = 0;
    if (selector && (mark_short_circuit_effect(), 1)) {
        if_result = 4;
    }
    if (if_result != 0 || short_circuit_effect_calls != 3) {
        return 1;
    }

    selector = 1;
    if (selector && (mark_short_circuit_effect(), 1)) {
        if_result = 5;
    }
    if (if_result != 5 || short_circuit_effect_calls != 4) {
        return 1;
    }

    if (selector || (mark_short_circuit_effect(), 0)) {
        if_result = 6;
    }
    if (if_result != 6 || short_circuit_effect_calls != 4) {
        return 1;
    }

    selector = 0;
    if (selector || (mark_short_circuit_effect(), 1)) {
        if_result = 7;
    }
    if (if_result != 7 || short_circuit_effect_calls != 5) {
        return 1;
    }

    selector = 2;
    int loop_iterations = 0;
    while (selector && (mark_short_circuit_effect(), --selector)) {
        ++loop_iterations;
        if (loop_iterations == 1) {
            continue;
        }
    }
    if (selector != 0 || loop_iterations != 1 || short_circuit_effect_calls != 7) {
        return 1;
    }

    return 0;
}
