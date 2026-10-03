template<int N = 2 + 2>
struct ComputedDefaultBuffer {
    int values[N];
};

int main()
{
    ComputedDefaultBuffer<> buffer;
    buffer.values[3] = 53;
    return buffer.values[3] == 53 ? 0 : 1;
}
