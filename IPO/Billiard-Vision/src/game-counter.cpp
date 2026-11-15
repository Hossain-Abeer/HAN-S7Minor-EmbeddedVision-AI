#include "game-counter.h"
#include "config.h"
#include <fstream>
#include <ctime>

GameCounter::GameCounter(const std::string& clipStem,
                         const std::string& logPath)
    : m_clipStem(clipStem), m_logPath(logPath) {}

bool GameCounter::update(bool rackDetected) {
    if (rackDetected) {
        m_rackStreak++;
        m_absenceStreak = 0;            // reset glitch tolerance
        m_cooldownStreak = 0;

        if (m_state == State::IDLE && m_rackStreak >= DEBOUNCE_FRAMES) {
            m_state = State::COUNTED;
            m_count++;
            logCount();
            return true;
        }
    } else {
        m_absenceStreak++;
        m_cooldownStreak++;

        // Only reset the rack streak if absence is SUSTAINED (>3 frames).
        // Brief 1-2 frame detection glitches no longer kill a valid rack.
        if (m_absenceStreak > ABSENCE_TOLERANCE) {
            m_rackStreak = 0;
        }

        if (m_state == State::COUNTED && m_cooldownStreak >= COOLDOWN_FRAMES) {
            m_state = State::IDLE;
        }
    }
    return false;
}

void GameCounter::logCount() {
    char timebuf[32];
    time_t t = time(nullptr);
    strftime(timebuf, sizeof(timebuf), "%Y-%m-%dT%H:%M:%S", localtime(&t));

    std::ofstream fs(m_logPath, std::ios::app);
    if (!fs) return;
    fs << timebuf << "," << m_count << "," << m_clipStem << "\n";
    fs.close();
}