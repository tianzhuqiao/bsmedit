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

#ifndef _BSM_BUFFER_INTF_H_
#define _BSM_BUFFER_INTF_H_

class bsm_buf_read_inf
{
public:
    bsm_buf_read_inf(){};
    virtual~bsm_buf_read_inf(){};
public:
    virtual int size() = 0;
    virtual double read(int n) const = 0 ;
public:
    double operator [](int nIndex) const
    {
        return read(nIndex) ;
    }
};

class bsm_buf_write_inf
{
public:
    bsm_buf_write_inf(){};
    virtual~bsm_buf_write_inf(){};
public:
    virtual bool write(double value, int n) = 0;
    virtual bool append(double value) = 0;
};
#endif //!defined(_BSM_BUFFER_INTF_H_)

/* 
 *History:
 *
 * $Log$
 *
 */
