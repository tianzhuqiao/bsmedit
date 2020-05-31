"""copy the docstring"""
import inspect
import textwrap


def copy(source, dropSelf=True):
    """return the function to copy the docstring"""
    def do_copy(target):
        """do the real copy"""
        if source.__doc__:
            argspec = inspect.formatargspec(*inspect.getargspec(source))
            if dropSelf:
                # The first parameter to a method is a reference to an
                # instance, usually coded as "self", and is usually passed
                # automatically by Python; therefore we want to drop it.
                temp = argspec.split(',')
                if len(temp) == 1:  # No other arguments.
                    argspec = '()'
                elif temp[
                        0][:2] == '(*':  # first param is like *args, not self
                    pass
                else:  # Drop the first argument.
                    argspec = '(' + ','.join(temp[1:]).lstrip()

            docstring = textwrap.dedent(source.__doc__)
            if target.__doc__:
                docstring += textwrap.dedent(target.__doc__)

            target.__doc__ = docstring
        return target

    return do_copy


def copy_docstring(source, dropSelf=True):
    """copy the docstring to target, used as decorator"""
    return lambda target: copy(source, dropSelf)(target)


def copy_docstring_raw(source, target, dropSelf=True):
    """copy the docstring to target"""
    if source.__doc__:
        argspec = inspect.formatargspec(*inspect.getargspec(source))
        if dropSelf:
            # The first parameter to a method is a reference to an
            # instance, usually coded as "self", and is usually passed
            # automatically by Python; therefore we want to drop it.
            temp = argspec.split(',')
            if len(temp) == 1:  # No other arguments.
                argspec = '()'
            elif temp[0][:2] == '(*':  # first param is like *args, not self
                pass
            else:  # Drop the first argument.
                argspec = '(' + ','.join(temp[1:]).lstrip()
        docstring = '\n' + source.__name__ + argspec + '\n'
        docstring += '\n' + textwrap.dedent(source.__doc__).strip() + '\n'

        target.__doc__ = docstring
    return target
