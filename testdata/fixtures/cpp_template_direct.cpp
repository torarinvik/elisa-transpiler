#include "cpp_template_direct.hpp"

int main()
{
    ExternalCell<int> cell;
    ExternalCell<double> floating_cell;
    Alpha::Cell<int> alpha_cell;
    Beta::Cell<int> beta_cell;
    FixedBuffer<2> small_buffer;
    FixedBuffer<3> large_buffer;
    FeatureFlag<true> enabled_flag;
    FeatureFlag<false> disabled_flag;
    IntegralTag<-2> negative_tag;
    DefaultBuffer<> default_buffer;
    DefaultBuffer<4> explicit_default_buffer;
    DefaultBuffer<5> differently_sized_buffer;
    DefaultType<> default_type;
    DefaultType<int> explicit_default_type;
    DefaultType<double> alternate_default_type;
    cell.value = 41;
    floating_cell.value = 1.5;
    alpha_cell.value = 7;
    beta_cell.value = 9;
    small_buffer.values[1] = 11;
    large_buffer.values[2] = 13;
    enabled_flag.value = 17;
    disabled_flag.value = 19;
    negative_tag.value = 23;
    default_buffer.values[3] = 29;
    explicit_default_buffer.values[0] = 31;
    differently_sized_buffer.values[4] = 37;
    default_type.value = 43;
    explicit_default_type.value = 47;
    alternate_default_type.value = 1.25;
    return cell.value == 41 && floating_cell.value == 1.5 && alpha_cell.value == 7 && beta_cell.value == 9 && small_buffer.values[1] == 11 && large_buffer.values[2] == 13 && enabled_flag.value == 17 && disabled_flag.value == 19 && negative_tag.value == 23 && default_buffer.values[3] == 29 && explicit_default_buffer.values[0] == 31 && differently_sized_buffer.values[4] == 37 && default_type.value == 43 && explicit_default_type.value == 47 && alternate_default_type.value == 1.25 ? 0 : 1;
}
