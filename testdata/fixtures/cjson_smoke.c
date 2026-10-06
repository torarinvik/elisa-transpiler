#include "../upstream/cJSON/cJSON.c"
#include <stdio.h>

int main(void)
{
    const char *json = "{\"name\":\"elisa\",\"items\":[1,true,null]}";
    cJSON *root = cJSON_Parse(json);
    if (root == NULL)
    {
        return 1;
    }

    if (cJSON_Parse("{\"name\":}") != NULL)
    {
        cJSON_Delete(root);
        return 3;
    }

    char *printed = cJSON_PrintUnformatted(root);
    if (printed == NULL)
    {
        cJSON_Delete(root);
        return 2;
    }

    printf("%s\n", printed);
    cJSON_free(printed);
    cJSON_Delete(root);
    return 0;
}
