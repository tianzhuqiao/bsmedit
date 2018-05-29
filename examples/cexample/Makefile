CC = g++
CFLAGS = -Wall -fexceptions -g -W -fPIC -DPURIFY -D_USRDLL

DEPS = cexample.h
ODIR=obj
OBJ = main.o
OBJS = $(patsubst %,$(ODIR)/%,$(OBJ))

libcexample: $(OBJS)
	g++ -shared  $^ -o $@.so

$(ODIR)/%.o: %.c $(DEPS)
	g++ $(CFLAGS) -c $< -o $@

$(OBJS): | $(ODIR)

$(ODIR):
	mkdir -p $(ODIR)

.PHONY: clean

clean:
	rm -f $(ODIR)/*.o *.so
	rm -r $(ODIR)
