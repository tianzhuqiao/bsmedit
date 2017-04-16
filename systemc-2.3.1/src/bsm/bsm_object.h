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

#ifndef _BSM_OBJECT_H_
#define _BSM_OBJECT_H_

class bsm_object_base
{
protected:
    bsm_object_base(){}
    virtual ~bsm_object_base(){}
public:
    virtual void      ins_ref()=0;
    virtual void      dec_ref()=0;
    virtual int       get_ref()=0;
};
template<class T>
class bsm_object_impl:public T
{
protected:
    bsm_object_impl():m_nReference(0){}
    virtual ~bsm_object_impl(){}
public:
    virtual void      ins_ref(){m_nReference++;}
    virtual void      dec_ref()
    {
        m_nReference--;
        if(m_nReference<=0)
            delete this;
    }
    virtual int       get_ref(){return m_nReference;}
protected:
    int m_nReference;
};
template<class T>
class bsm_object_static_impl:public T
{
protected:
    bsm_object_static_impl(){}
    virtual ~bsm_object_static_impl(){}
public:
    virtual void      ins_ref(){}
    virtual void      dec_ref(){}
    virtual int       get_ref(){return 1;}
};

#endif //!defined(_BSM_OBJECT_H_)

/* 
 *History:
 *
 * $Log$
 *
 */
