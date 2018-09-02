CC = g++
CFLAGS = -Wall -fexceptions -g -W -fPIC -DPURIFY -D_USRDLL

DEPS = waves.h
ODIR=obj
OBJ = main.o
OBJS = $(patsubst %,$(ODIR)/%,$(OBJ))

libwaves: $(OBJS)
	$(CC) -shared  $^ -o $@.so

$(ODIR)/%.o: %.c $(DEPS)
	$(CC) $(CFLAGS) -c $< -o $@

$(OBJS): | $(ODIR)

$(ODIR):
	mkdir -p $(ODIR)

.PHONY: clean

clean:
	rm -f $(ODIR)/*.o *.so
	rm -r $(ODIR)
