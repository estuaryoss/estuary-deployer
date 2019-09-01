#!/bin/sh

cd /tmp

#simulates test run. here you can have a bunch of maven/make/other commands
sleep 5 #modify in test too if this is modified for istestfinished

#you must signal your test is finished. for standardization purpuse send it in /tmp/is_test_finished with the keyword finished/FINISHED
echo finished > /tmp/is_test_finished