#include "HypothesisInterface.h"

#include <assert.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#define BUF_SIZE 200

static const char *fifo_commands = getenv("HYPOTHESISFIFOCOMMANDS");
static const char *fifo_results = getenv("HYPOTHESISFIFORESULTS");

FILE *results_file = NULL;
FILE *commands_file = NULL;

static char outgoing[BUF_SIZE];


static void writeOutgoing(){
  if (commands_file == NULL)
    commands_file = fopen(fifo_commands, "w");
  int n = strlen(outgoing);
  assert(n < 256);
  fputc(n, commands_file);
  fwrite(outgoing, sizeof(char), strlen(outgoing), commands_file);
  fflush(commands_file);
}

static void writeCommand(const char *command) {
  strcpy(outgoing, command);
  writeOutgoing();
}

static int readResult() {
  if (results_file == NULL)
    results_file = fopen(fifo_results, "r");
  assert(results_file != NULL);

  int i = 0;
  int result = 0;
  while(i < 4){
    int c = fgetc(results_file);
    if (c == EOF)
      continue;
    assert(0 <= c && c < 256);
    result <<= 8;
    result |= c;
    i ++;
  }
  fflush(stderr);
  return result;
}

static void getAck() {
  int result = readResult();
  assert(result == 0);
}

unsigned long hypothesisGetRand() {
  writeCommand("RAND");
  return readResult();
}

void hypothesisInitConnection() {}

void hypothesisTerminateConnection() {
  writeCommand("TERMINATE");
  getAck();
  fclose(results_file);
  fclose(commands_file);
}

void hypothesisStartExample(const char *label) {
  sprintf(outgoing, "START %s", label);
  assert(strlen(outgoing) > 0);
  writeOutgoing();
  getAck();
}

void hypothesisEndExample() {
  writeCommand("END");
  getAck();
}
