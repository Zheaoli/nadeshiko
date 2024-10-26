
CFLAGS=-std=c11 -g -fno-common

TEST_SRCS=$(wildcard test/*.c)
TESTS=$(TEST_SRCS:.c=.exe)

test/%.exe: test/%.c
	$(CC) -o- -E -P -C test/$*.c | python main.py -o test/$*.s -
	$(CC) -o $@ test/$*.s -xc test/common
test: $(TESTS)
	for i in $^; do echo $$i; ./$$i || exit 1; echo; done
	test/driver.sh
clean:
	rm -rf tmp* $(TESTS) test/*.s test/*.exe
	find * -type f '(' -name '*~' -o -name '*.o' ')' -exec rm {} ';'