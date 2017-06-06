#ifndef _BSM_OBJECT_H_
#define _BSM_OBJECT_H_

class bsm_object_base
{
protected:
    bsm_object_base() {}
    virtual ~bsm_object_base() {}
public:
    virtual void ins_ref() = 0;
    virtual void dec_ref() = 0;
    virtual int get_ref() = 0;
};
template<class T>
class bsm_object_impl :public T
{
protected:
    bsm_object_impl() : m_nReference(0) {}
    virtual ~bsm_object_impl() {}
public:
    virtual void   ins_ref() { m_nReference++; }
    virtual void      dec_ref()
    {
        m_nReference--;
        if(m_nReference <= 0) delete this;
    }
    virtual int get_ref() { return m_nReference; }
protected:
    int m_nReference;
};
template<class T>
class bsm_object_static_impl :public T
{
protected:
    bsm_object_static_impl() {}
    virtual ~bsm_object_static_impl() {}
public:
    virtual void ins_ref() {}
    virtual void dec_ref() {}
    virtual int get_ref() { return 1; }
};

#endif //!defined(_BSM_OBJECT_H_)
