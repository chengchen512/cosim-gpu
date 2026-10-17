HIPCC    ?= hipcc
HIPFLAGS ?= --offload-arch=gfx942 -O2
BUILDDIR ?= ../build/tests

SOURCES := $(wildcard kernels/*.cpp)
TARGETS := $(patsubst kernels/%.cpp,$(BUILDDIR)/%,$(SOURCES))

.PHONY: all clean test

all: $(TARGETS)

$(BUILDDIR)/%: kernels/%.cpp common/test_utils.h | $(BUILDDIR)
	$(HIPCC) $(HIPFLAGS) -I. -o $@ $<

$(BUILDDIR):
	mkdir -p $(BUILDDIR)

test: all
	@./run_tests.sh

clean:
	rm -rf $(BUILDDIR)
