"""
Manage windows (originated from matplotlib).
"""
import gc
import six


class Gcm(object):
    """
    It consists of two class
    attributes (a list and a dictionary), and a set of static
    methods that operate on those attributes, accessing them
    directly as class attributes.

    Attributes:

        *mgrs*:
          dictionary of the form {*num*: *manager*, ...}

        *_activeQue*:
          list of *managers*, with active one at the end

    """
    def __init__(self):
        self._activeQue = []
        self.mgrs = {}

    def get_manager(self, num):
        """
        If manager *num* exists, make it active
        and return the manager; otherwise return *None*.
        """
        manager = self.mgrs.get(num, None)
        if manager is not None:
            self.set_active(manager)
        return manager

    def destroy(self, num):
        """
        Try to remove all traces of manager *num*.

        In the interactive backends, this is bound to the
        window "destroy" and "delete" events.
        """
        if not self.has_num(num):
            return
        manager = self.mgrs[num]

        # There must be a good reason for theg following careful
        # rebuilding of the activeQue; what is it?
        oldQue = self._activeQue[:]
        self._activeQue = []
        for f in oldQue:
            if f != manager:
                self._activeQue.append(f)

        del self.mgrs[num]
        #manager.destroy()
        gc.collect(1)

    def destroy_mgr(self, mgr):
        "*mgr* is a manager instance"
        num = None
        for manager in six.itervalues(self.mgrs):
            if manager == mgr:
                num = manager.num
                break
        if num is not None:
            self.destroy(num)

    def destroy_all(self):
        """remove all the managers"""
        self._activeQue = []
        self.mgrs.clear()
        gc.collect(1)

    def has_num(self, num):
        """
        Return *True* if manager *num* exists.
        """
        return num in self.mgrs

    def get_all_managers(self):
        """
        Return a list of managers.
        """
        return list(self.mgrs.values())

    def get_num_managers(self):
        """
        Return the number of manager being managed.
        """
        return len(self.mgrs)

    def get_active(self):
        """
        Return the manager of the active manager, or *None*.
        """
        if len(self._activeQue) == 0:
            return None
        else:
            return self._activeQue[-1]

    def set_active(self, mgr):
        """
        Make the mgr corresponding to *manager* the active one.
        """
        oldQue = self._activeQue[:]
        self._activeQue = []
        for m in oldQue:
            if m != mgr:
                self._activeQue.append(m)
        self._activeQue.append(mgr)
        self.mgrs[mgr.num] = mgr

    def get_nums(self):
        """return all the occupied nums"""
        return list(self.mgrs.keys())

    def get_next_num(self):
        """return the next available num"""
        allnums = self.get_nums()
        return max(allnums) + 1 if allnums else 1
