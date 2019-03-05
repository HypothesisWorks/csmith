#ifndef HYPOTHESIS_INTERFACE
#define HYPOTHESIS_INTERFACE

void hypothesisBeginInterval();

void hypothesisEndInterval();

void hypothesisInitConnection();

void hypothesisTerminateConnection();
void hypothesisStartExample(const char* label);
void hypothesisEndExample();

unsigned long hypothesisGetRand();

#define HYPOTHESIS_DRAW(cls, args...) ({  hypothesisStartExample(#cls); auto result = cls::make_random(args); hypothesisEndExample(); result; })
#endif //HYPOTHESIS_INTERFACE
