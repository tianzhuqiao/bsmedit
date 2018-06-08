CC = g++
CFLAGS = -Wall -fexceptions -g -W -fPIC -DPURIFY -D_USRDLL

DEPS = wave.h
ODIR=obj
OBJ = main.o
OBJS = $(patsubst %,$(ODIR)/%,$(OBJ))

libwave: $(OBJS)
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
