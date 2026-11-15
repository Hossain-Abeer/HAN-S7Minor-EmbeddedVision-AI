#pragma once
#include <string>

class GameCounter {
public:
    GameCounter(const std::string& clipStem, const std::string& logPath);
    bool update(bool rackDetected);   // true only on the counted-event frame
    int  getCount() const { return m_count; }

private:
    void logCount();

    enum class State { IDLE, COUNTED };
    State       m_state          = State::IDLE;
    int         m_count          = 0;
    int         m_rackStreak     = 0;
    int         m_absenceStreak  = 0;   // <-- NEW
    int         m_cooldownStreak = 0;
    std::string m_clipStem;
    std::string m_logPath;
};