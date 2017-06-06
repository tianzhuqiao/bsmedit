#ifndef _BSM_BUFFER_INTF_H_
#define _BSM_BUFFER_INTF_H_

class bsm_buf_read_inf
{
public:
    bsm_buf_read_inf() {};
    virtual~bsm_buf_read_inf() {};
public:
    virtual int size() = 0;
    virtual double read(int n) const = 0;
public:
    double operator [](int nIndex) const
    {
        return read(nIndex);
    }
};

class bsm_buf_write_inf
{
public:
    bsm_buf_write_inf() {};
    virtual~bsm_buf_write_inf() {};
public:
    virtual bool write(double value, int n) = 0;
    virtual bool append(double value) = 0;
};
#endif //!defined(_BSM_BUFFER_INTF_H_)
