/**
 *BSMEdit-Systemc Simulation Module Controling
 *Copyright (C) 2009 Tianzhu Qiao <ben.qiao@gmail.com>
 *http://bsmedit.sourceforge.net/
 *http://www.feiyilin.com/
 *
 *This program is free software; you can redistribute it and/or modify
 *it under the terms of the GNU General Public License as published by
 *the Free Software Foundation; either version 2 of the License, or
 *(at your option) any later version.
 *                                    
 *This program is distributed in the hope that it will be useful,
 *but WITHOUT ANY WARRANTY; without even the implied warranty of
 *MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 *GNU General Public License for more details.
 *                                    
 *You should have received a copy of the GNU General Public License along
 *with this program; if not, write to the Free Software Foundation, Inc.,
 *51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
 *http://www.gnu.org/copyleft/gpl.html
 **/



#ifndef DECLARE_REG_TYPE
#define DECLARE_REG_TYPE(type, id)
#endif
#ifndef DECLARE_REG_TYPE2
#define DECLARE_REG_TYPE2(type, id) 
#endif
#ifndef DECLARE_REG_TYPE3
#define DECLARE_REG_TYPE3(type, id) 
#endif

DECLARE_REG_TYPE(bool,               BSM_REG_BOOL)
DECLARE_REG_TYPE(float,              BSM_REG_FLOAT)
DECLARE_REG_TYPE(double,             BSM_REG_DOUBLE)
DECLARE_REG_TYPE(unsigned char,      BSM_REG_UCHAR)
DECLARE_REG_TYPE(unsigned short,     BSM_REG_USHORT)
DECLARE_REG_TYPE(unsigned int,       BSM_REG_UINT)
DECLARE_REG_TYPE(unsigned long,      BSM_REG_ULONG )
DECLARE_REG_TYPE3(unsigned long long, BSM_REG_UINT64 )
DECLARE_REG_TYPE(char,               BSM_REG_CHAR  )
DECLARE_REG_TYPE(short,              BSM_REG_SHORT )
DECLARE_REG_TYPE(int,                BSM_REG_INT   )
DECLARE_REG_TYPE(long,               BSM_REG_LONG  )
DECLARE_REG_TYPE3(long long,          BSM_REG_INT64 )
DECLARE_REG_TYPE3(sc_bit,             BSM_REG_SC_BIT )
DECLARE_REG_TYPE3(sc_logic,           BSM_REG_SC_LOGIC)

DECLARE_REG_TYPE2(std::string ,       BSM_REG_STR)
#undef DECLARE_REG_TYPE
#undef DECLARE_REG_TYPE2
#undef DECLARE_REG_TYPE3
/** 
 *History:
 *
 * $Log: reg_type.h,v $
 * Revision 1.1  2009/02/18 05:14:19  tianzhuqiao
 * initial version
 *
 *
 **/
