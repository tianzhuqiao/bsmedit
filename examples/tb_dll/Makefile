SYSC_DIR =$(SYSTEMC_ROOT)/include
SYSC_LIB =$(SYSTEMC_ROOT)/lib-macosx64/libsystemc.a

CC = g++ -std=c++17
CFLAGS = -Wall -fexceptions -g -W -fPIC -DSC_INCLUDE_FX -DPURIFY -D_USRDLL -DBSM_DLL_SIM
LDFLAGS = -Wl,-U,_sc_main,-U,___sanitizer_start_switch_fiber,-U,___sanitizer_finish_switch_fiber

DEPS = top.h
ODIR=obj
OBJ = main.o top.o sub.o
OBJS = $(patsubst %,$(ODIR)/%,$(OBJ))

libtbdll: $(OBJS) $(SYSC_LIB)
	g++  -shared $(LDFLAGS) $^ -o $@.so

$(ODIR)/%.o: %.cpp $(DEPS)
	$(CC) $(CFLAGS) -I$(SYSC_DIR) -c $< -o $@

$(OBJS): | $(ODIR)

$(ODIR):
	mkdir -p $(ODIR)

.PHONY: clean

clean:
	rm -f $(ODIR)/*.o *.so
	rm -r $(ODIR)
