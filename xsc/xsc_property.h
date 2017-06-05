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

#ifndef _XSC_PROPERTY_H_
#define _XSC_PROPERTY_H_

 /** \class xsc_property
 \ingroup classes
 \brief the property to set the configuration of the modules

 \b Usage
 \code
     class MyModule:public tx_module
     {
     public:
          MyModule(sc_module_name name_):
          tx_module(name_)
          ,xscprop_double("xscprop_double", this, xsc_callback_fun)
          ,xscprop_int("xscprop_int", this, xsc_callback_fun)
          ,xscprop_scint10("xscprop_scint10")
          {
              //set the value and call the callback function
              xscprop_double.write(1.0);
              //set the value and don't call the callback function
              xscprop_int.write_nc(128);
              //set the value and don't call the callback function
              xscprop_scint10.write(256);
          }
          // Declaration in some module
          xsc_property<double>      xscprop_double;
          xsc_property<int>         xscprop_int;
          xsc_property<sc_int<10> > xscprop_scint10;
          static void xsc_callback_fun(sc_module* pThis, double value);
       };
 \endcode
 */
template <class T>
class xsc_property : public sc_signal<T>
{
    //call back function pointer
    typedef  void(*xsc_callback)(sc_module* pThis, T value);
public:
    /** Constructor

      the callback function is disabled
     */
    xsc_property() :
        sc_signal<T>(sc_gen_unique_name("xsc_property"))
        , m_pCallBlock(NULL)
        , m_pCallback(NULL)
    {}

    /** Constructor
    \param name_ module name
    \param pCallBlock the parent module
    \param pCallback the callback function
    */
    explicit xsc_property(const char* name_, sc_module* pCallBlock=NULL,
                          xsc_callback pCallback=NULL)
        : sc_signal<T>(name_)
        , m_pCallBlock(pCallBlock)
        , m_pCallback(pCallback)
    {}

    /** Destructor
    */
    virtual ~xsc_property()
    {}
    /** return the systemc kind string "xsc_property"
      \return xsc_property
    */
    virtual const char* kind() const { return "xsc_property"; }

    /** write the new value to the property with the callback function

    the new value will be updated without any delay.\n
    if the callback function is available, it will be called.

    \param value_ the new value
    */
    void write(const T& value_)
    {
        sc_signal<T>::write(value_);
        sc_signal<T>::m_cur_val = sc_signal<T>::m_new_val;

        //call back function
        if(m_pCallback) m_pCallback(m_pCallBlock, value_);
    }

    /** write the new value to the property without the callback function

    the new value will be updated without any delay.\n
    the callback function is disabled

    \param value_ the new value
    */
    void write_nc(const T& value_)
    {
        sc_signal<T>::write(value_);
        sc_signal<T>::m_cur_val = sc_signal<T>::m_new_val;
    }

private:
    sc_module*   m_pCallBlock;
    xsc_callback m_pCallback;
};
#endif //!defined (_XSC_PROPERTY_H_)
