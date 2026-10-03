#pragma once

template<typename T>
struct ExternalCell {
    T value;
};

namespace Alpha {
template<typename T>
struct Cell {
    T value;
};
}

namespace Beta {
template<typename T>
struct Cell {
    T value;
};
}

template<int N>
struct FixedBuffer {
    int values[N];
};

template<bool Enabled>
struct FeatureFlag {
    int value;
};

template<int N>
struct IntegralTag {
    int value;
};

template<int N = 4>
struct DefaultBuffer {
    int values[N];
};

template<typename T = int>
struct DefaultType {
    T value;
};
