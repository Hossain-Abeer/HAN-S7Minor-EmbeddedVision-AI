#include "classify.h"
#include "config.h"

BallType classifyBall(const BallCandidate& ball) {
    float wr = ball.white_ratio;
    float ed = ball.edge_density;

    if (wr > RATIO_CUE) {
        return BallType::CUE;
    } else if (wr > UNCERTAIN_WHITE_HI) {
        return BallType::UNCERTAIN; // Extreme glare (between 0.60 and 0.65)
    } else if (wr >= RATIO_STRIPE_LO) {
        return BallType::STRIPE;
    } else if (wr >= SOLID_WHITE_LO && ed > EDGE_SOLID_MIN) {
        return BallType::SOLID;
    } else {
        // Anything with wr < 0.15 is a Solid (including the dark 8-ball)
        return BallType::SOLID; 
    }
}