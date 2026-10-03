int declaration_index_global_00;
int declaration_index_global_01;
int declaration_index_global_02;
int declaration_index_global_03;
int declaration_index_global_04;
int declaration_index_global_05;
int declaration_index_global_06;
int declaration_index_global_07;
int declaration_index_global_08;
int declaration_index_global_09;
int declaration_index_global_10;
int declaration_index_global_11;
int declaration_index_global_12;
int declaration_index_global_13;
int declaration_index_global_14;
int declaration_index_global_15;
int declaration_index_global_16;
int declaration_index_global_17;
int declaration_index_global_18;
int declaration_index_global_19;
int declaration_index_global_20;
int declaration_index_global_21;
int declaration_index_global_22;
int declaration_index_global_23;
int declaration_index_global_24;
int declaration_index_global_25;
int declaration_index_global_26;
int declaration_index_global_27;
int declaration_index_global_28;
int declaration_index_global_29;
int declaration_index_global_30;
int declaration_index_global_31;
int declaration_index_global_32;
int declaration_index_global_33;
int declaration_index_global_34;
int declaration_index_global_35;

static int declaration_index_identity(int);

static int declaration_index_identity(int value)
{
    return value;
}

int main(void)
{
    declaration_index_global_35 = 41;
    return declaration_index_identity(declaration_index_global_35) == 41 ? 0 : 1;
}
