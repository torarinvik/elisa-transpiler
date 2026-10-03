namespace {
int project_anonymous_state = 10;

int helper(int increment)
{
    project_anonymous_state += increment;
    return project_anonymous_state;
}
}

int project_anonymous_beta()
{
    return helper(2);
}
