## ****************************************************************************
##
##  The following code is derived, directly or indirectly, from the SystemC
##  source code Copyright (c) 1996-2005 by all Contributors.
##  All Rights reserved.
##
##  The contents of this file are subject to the restrictions and limitations
##  set forth in the SystemC Open Source License Version 2.4 (the "License");
##  You may not use this file except in compliance with such restrictions and
##  limitations. You may obtain instructions on how to receive a copy of the
##  License at http://www.systemc.org/. Software distributed by Contributors
##  under the License is distributed on an "AS IS" basis, WITHOUT WARRANTY OF
##  ANY KIND, either express or implied. See the License for the specific
##  language governing rights and limitations under the License.
##
## ****************************************************************************
##
##  src/bsm/Makefile.am --
##  Process this file with automake to produce a Makefile.in file.
##
##  Original Author: Martin Janssen, Synopsys, Inc., 2001-05-21
##
## ****************************************************************************
##
##  MODIFICATION LOG - modifiers, enter your name, affiliation, date and
##  changes you are making here.
##
##      Name, Affiliation, Date:
##  Description of Modification:
##
## ****************************************************************************

include $(top_srcdir)/config/Make-rules.sysc

noinst_LTLIBRARIES = libbsm.la

H_FILES = \
          bsm_sysc.h \
		  reg_type.h \
		  bsm_object.h \
		  bsm_buffer_intf.h \
		  bsm_sim_context.h \
		  bsm_sim_context_impl.h \
          sc_bsm_trace.h \
          sc_bsm_trace_buf.h

localincludedir = $(includedir)/sysc/bsm
nobase_localinclude_HEADERS = $(H_FILES)

CXX_FILES = \
	bsm_sim_context_impl.cpp \
    sc_bsm_trace.cpp \
    sc_bsm_trace_buf.cpp


NO_CXX_FILES =

libbsm_la_SOURCES = $(H_FILES) $(CXX_FILES)

## Taf!
