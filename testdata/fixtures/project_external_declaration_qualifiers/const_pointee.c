int project_external_pointer_conflict(const int *value);

int project_external_pointer_const(void)
{
    return project_external_pointer_conflict(0);
}
