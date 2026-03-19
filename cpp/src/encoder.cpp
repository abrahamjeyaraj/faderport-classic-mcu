#include "encoder.h"

namespace fp {

std::optional<int> EncoderFilter::process(int pitchBendValue) {
    auto now = Clock::now();

    if (firstEvent_) {
        firstEvent_ = false;
        lastTime_ = now;
        windowStart_ = now;
        lastDirection_ = (pitchBendValue >= 8192) ? -1 : 1;
        return lastDirection_;
    }

    double elapsed = std::chrono::duration<double>(now - lastTime_).count();
    if (elapsed < DEBOUNCE_S)
        return std::nullopt;

    int direction = (pitchBendValue >= 8192) ? -1 : 1;

    if (direction == lastDirection_) {
        lastTime_ = now;
        return direction;
    }

    double windowElapsed = std::chrono::duration<double>(now - windowStart_).count();
    if (windowElapsed > HYSTERESIS_WINDOW_S) {
        windowStart_ = now;
        consecutive_ = 1;
        return std::nullopt;
    }

    consecutive_++;
    if (consecutive_ >= HYSTERESIS_COUNT) {
        lastDirection_ = direction;
        lastTime_ = now;
        consecutive_ = 0;
        return direction;
    }

    return std::nullopt;
}

} // namespace fp
