/*
 *SystemC Simulation General TX-Modules
 *Copyright (C) 2009 Tianzhu Qiao <ben.qiao@gmail.com>
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
 */

#ifndef _XSC_ARRAY_H_
#define _XSC_ARRAY_H_
#include "xsc_property.h"
 /** \class xsc_array
 \ingroup classes
 \brief the property array to set the configuration or display the information of the modules

 \b Usage
 \code
     class MyModule:public sc_module
     {
     public:
          MyModule(sc_module_name name_)
          : sc_module(name_)
          , xscarray_int("xscarray_int")
          {
              //set the value
              xscarray_int[0] = 1;
              xscarray_int[1].write(1);
              //get the value
              int a = xscarray_int[0];
              int b = xscarray_int[1].read();
          }
          xsc_array<int, 5> xscarray_int;
       };
 \endcode
 */
template <class T, int N>
class xsc_array : public sc_object
{
    //call back function pointer
    typedef  void(*xsc_callback)(sc_module* pThis, T value);
public:
    /** Constructor

      the callback function is disabled
     */
    xsc_array()
        : sc_object(sc_gen_unique_name("xsc_array"))
        , m_pCallBlock(NULL)
        , m_pCallback(NULL)
    {
        init();
    }
    /** Constructor
    \param name_ module name

      the callback function is disabled
    */
    explicit xsc_array(const char* name_, sc_module* pCallBlock=NULL,
                       xsc_callback pCallback=NULL)
        : sc_object(name_)
        , m_pCallBlock(pCallBlock)
        , m_pCallback(pCallback)
    {
        init();
    }

    /** Destructor
    */
    virtual ~xsc_array()
    {
        uninit();
    }

    /** return the systemc kind string "xsc_array"
      \return xsc_array
    */
    virtual const char* kind() const { return "xsc_array"; }

    // operator
    /** get the element at index i

    \param i the index of the element to be retrieved
    \return a reference to element at index i
    */
    sc_signal<T>& operator [] (int i)
    {
        sc_assert(i >= 0 && i < N);
        return *m_signal[i];
    }

private:
    void init()
    {
        const char *name_ = basename();
        char bufName[512];
        for(int i = 0; i < N; i++) {
            sprintf(bufName, "%s[%d]", name_, i);
            m_signal[i] = new xsc_property<T>(bufName, m_pCallBlock, m_pCallback);
        }
    }
    void uninit()
    {
        for(int i = 0; i < N; i++) {
            delete  m_signal[i];
            m_signal[i] = NULL;
        }
    }
private:
    sc_module*   m_pCallBlock;
    xsc_callback m_pCallback;
    xsc_property<T>* m_signal[N];

};
#endif //!defined (_XSC_ARRAY_H_)
