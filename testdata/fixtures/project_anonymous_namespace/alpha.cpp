namespace {
int project_anonymous_state = 3;

int helper(int increment)
{
    project_anonymous_state += increment;
    return project_anonymous_state;
}
}

int project_anonymous_alpha()
{
    return helper(1);
}
