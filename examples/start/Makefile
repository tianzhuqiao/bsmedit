SYSC_DIR =../../systemc-2.3.1/src
SYSC_LIB =../../systemc-2.3.1/lib-linux64/libsystemc.a
XSC_DIR = ../../xsc
CC = g++
CFLAGS = -Wall -fexceptions -g -W -fPIC -DSC_INCLUDE_FX -DPURIFY -D_USRDLL

DEPS = top.h
ODIR=obj
OBJ = main.o top.o bsm.o
OBJS = $(patsubst %,$(ODIR)/%,$(OBJ))

libstart: $(OBJS) $(SYSC_LIB)
	g++ -shared  $^ -o $@.so

$(ODIR)/bsm.o: ../../xsc/bsm.cpp ../../xsc/bsm.h
	g++ $(CFLAGS) -I$(SYSC_DIR) -I$(XSC_DIR) -c $< -o $@

$(ODIR)/%.o: %.cpp $(DEPS)
	g++ $(CFLAGS) -I$(SYSC_DIR) -I$(XSC_DIR) -c $< -o $@

$(OBJS): | $(ODIR)

$(ODIR):
	mkdir -p $(ODIR)

.PHONY: clean

clean:
	rm -f $(ODIR)/*.o *.so
	rm -r $(ODIR)
