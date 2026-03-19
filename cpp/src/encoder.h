#pragma once
#include <chrono>
#include <optional>

namespace fp {

class EncoderFilter {
public:
    std::optional<int> process(int pitchBendValue);

private:
    static constexpr double DEBOUNCE_S = 0.010;
    static constexpr double HYSTERESIS_WINDOW_S = 0.100;
    static constexpr int HYSTERESIS_COUNT = 3;

    using Clock = std::chrono::steady_clock;
    using TimePoint = Clock::time_point;

    TimePoint lastTime_{};
    int lastDirection_ = 0;
    int consecutive_ = 0;
    TimePoint windowStart_{};
    bool firstEvent_ = true;
};

} // namespace fp
