int project_external_pointer_conflict(int *value);

int project_external_pointer_mutable(void)
{
    return project_external_pointer_conflict(0);
}
