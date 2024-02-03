import matplotlib

def get_top_gridspec(ax):
    g = ax.get_gridspec()
    while isinstance(g, matplotlib.gridspec.GridSpecFromSubplotSpec):
        g = g._subplot_spec.get_gridspec()
    return g

def get_gridspec(ax, g):
    # check if subplot ax is in g, if yes, return the gridspec
    ga = ax.get_gridspec()
    while True:
        if isinstance(ga, matplotlib.gridspec.GridSpecFromSubplotSpec):
            if ga._subplot_spec.get_gridspec() == g:
                return ga
            ga = ga._subplot_spec.get_gridspec()
        else:
            return None

def del_subplot(ax):
    # delete ax from the figure
    # get the ax gridspec
    g = ax.get_gridspec()
    # and its positon
    r, c, s, _ = ax.get_subplotspec().get_geometry()

    # delete the ax
    fig = ax.figure
    ax.figure.delaxes(ax)
    g2 = None
    if r > 1:
        if isinstance(g, matplotlib.gridspec.GridSpecFromSubplotSpec):
            # ax is not a top level subplot, get the parent gridspec
            gp =  ax.get_gridspec()._subplot_spec.get_gridspec()
            _, _, sp, _ =  ax.get_gridspec()._subplot_spec.get_geometry()
            if r > 2:
                # regenerate the subgridspec by reducing the size
                g2 = gp[sp].subgridspec(r-1, c)
            else:
                # only 1 left in the subgridspec, no need subgridspec, use
                # the parent grid directly
                g2 = [gp[sp]]
        else:
            # top level subplot
            g2 = matplotlib.gridspec.GridSpec(r-1, c)

        for a in ax.figure.axes:
            if a.get_gridspec() == g:
                # a and ax in the same gridspec, and at same level
                _, _, i, _ = a.get_subplotspec().get_geometry()
                if i > s:
                    i = i - 1
                a.set_subplotspec(g2[i])
            else:
                gp = get_gridspec(a, g)
                if gp:
                    # a and ax in the same griespec, but a is in deeper level
                    _, _, i, _ = gp._subplot_spec.get_geometry()
                    if i > s:
                        i = i - 1
                    gp._subplot_spec = g2[i]
    elif c > 1:
        if isinstance(g, matplotlib.gridspec.GridSpecFromSubplotSpec):
            # ax is not a top level subplot, get the parent gridspec
            gp =  ax.get_gridspec()._subplot_spec.get_gridspec()
            _, _, sp, _ =  ax.get_gridspec()._subplot_spec.get_geometry()
            if c > 2:
                # regenerate the subgridspec by reducing the size
                g2 = gp[sp].subgridspec(r, c-1)
            else:
                # only 1 left in the subgridspec, no need subgridspec, use
                # the parent grid directly
                g2 = [gp[sp]]
        else:
            # top level subplot
            g2 = matplotlib.gridspec.GridSpec(r, c-1)

        for a in ax.figure.axes:
            if a.get_gridspec() == g:
                # a and ax in the same gridspec, and at same level
                _, _, i, _ = a.get_subplotspec().get_geometry()
                if i>s:
                    i = i-1
                a.set_subplotspec(g2[i])
            else:
                gp = get_gridspec(a, g)
                if gp:
                    # a and ax in the same griespec, but a is in deeper level
                    _, _, i, _ = gp._subplot_spec.get_geometry()
                    if i>s:
                        i = i-1
                    gp._subplot_spec = g2[i]

    while isinstance(g2, matplotlib.gridspec.GridSpec) and g2.ncols == 1 and g2.nrows == 1:
        if len(fig.axes) <= 1:
            # allow GridSpec(1, 1) only if there is one axes left
            break
        # g2 is toplevel and only one item left, find its only child
        gc = get_gridspec(fig.axes[0], g2)
        if isinstance(gc, matplotlib.gridspec.GridSpec):
            # g2 has one child, and it is axes, done
            break
        g3 = matplotlib.gridspec.GridSpec(gc.nrows, gc.ncols)
        for a in ax.figure.axes:
            if a.get_gridspec() == gc:
                # a is in g directly
                _, _, i, _ = a.get_subplotspec().get_geometry()
                a.set_subplotspec(g3[i])
            else:
                ga = get_gridspec(a, gc)
                if ga:
                    _, _, i, _ = ga._subplot_spec.get_geometry()
                    ga._subplot_spec = g3[i]
        g2 = g3

    fig.subplots_adjust()

def get_subplot_grid(ax, direction='bottom', edge=False):
    def _update_grid(s, g, g2):
        for a in ax.figure.axes:
            # update all the subplot in the same gridspac as ax
            if a.get_gridspec() == g:
                # a is in g directly
                _, _, i, _ = a.get_subplotspec().get_geometry()
                if direction in ['bottom', 'right'] and i > s:
                    # insert after position s
                    i = i+1
                elif direction in ['top', 'left'] and i >= s:
                    # insert before position s
                    i += 1
                a.set_subplotspec(g2[i])
            else:
                ga = get_gridspec(a, g)
                if ga:
                    # a is in g, but in deeper level
                    _, _, i, _ = ga._subplot_spec.get_geometry()
                    if direction in ['bottom', 'right'] and i > s:
                        i += 1
                    elif direction in ['top', 'left'] and i >= s:
                        i += 1
                    ga._subplot_spec = g2[i]

        # the gridspec for the new subplot
        if direction in ['bottom', 'right']:
            ax_new_gs = g2[s+1]
        else:
            ax_new_gs = g2[s]
        return ax_new_gs

    # add subplot after ax
    g = ax.get_gridspec()
    r, c, s, _ = ax.get_subplotspec().get_geometry()
    ax_new_gs = None
    vert = direction in ['top', 'bottom']
    if edge:
        # find the top level grid
        while isinstance(g, matplotlib.gridspec.GridSpecFromSubplotSpec):
            g = g._subplot_spec.get_gridspec()
        r, c = g.get_geometry()
        if (vert and c != 1) or (not vert and r != 1):
            # g is not in excepted shape, create the except shape, and
            # add g as child
            if vert:
                g2 = matplotlib.gridspec.GridSpec(2, 1)
            else:
                g2 = matplotlib.gridspec.GridSpec(1, 2)
            if direction in ['left', 'top']:
                si, gi = 0, 1 # index of the added axes and g
            else:
                si, gi = 1, 0
            g2_1 = g2[gi].subgridspec(g.nrows, g.ncols)
            for a in ax.figure.axes:
                if a.get_gridspec() == g:
                    # a is in g directly
                    _, _, i, _ = a.get_subplotspec().get_geometry()
                    a.set_subplotspec(g2_1[i])
                else:
                    ga = get_gridspec(a, g)
                    if ga:
                        _, _, i, _ = ga._subplot_spec.get_geometry()
                        ga._subplot_spec = g2_1[i]
            return g2[si]

        if direction in ['left', 'top']:
            # add to begin
            s = 0
        else:
            # add to the end
            s = r*c-1

    if vert:
        # add subplot below ax
        if c == 1:
            # ax is in a vertical gridspec
            if isinstance(g, matplotlib.gridspec.GridSpecFromSubplotSpec):
                # ax is not a top level subplot, get its parent gridspec
                gp =  ax.get_gridspec()._subplot_spec.get_gridspec()
                _, _, sp, _ =  ax.get_gridspec()._subplot_spec.get_geometry()
                # increase the size of the gridspec ax is in
                g2 = gp[sp].subgridspec(r+1, c)
            else:
                # ax is a top level subplot, increase the gridspec size
                g2 = matplotlib.gridspec.GridSpec(r+1, c)
            ax_new_gs = _update_grid(s, g, g2)
        else:
            gs20 = g[s].subgridspec(2, 1)
            if direction == 'bottom':
                ax.set_subplotspec(gs20[0])
                ax_new_gs = gs20[1]
            else:
                ax.set_subplotspec(gs20[1])
                ax_new_gs = gs20[0]
    else:
        if r == 1:
            if isinstance(g, matplotlib.gridspec.GridSpecFromSubplotSpec):
                gp =  ax.get_gridspec()._subplot_spec.get_gridspec()
                _, _, sp, _ =  ax.get_gridspec()._subplot_spec.get_geometry()
                g2 = gp[sp].subgridspec(r, c+1)
            else:
                g2 = matplotlib.gridspec.GridSpec(r, c+1)
            ax_new_gs = _update_grid(s, g, g2)
        else:
            gs20 = g[s].subgridspec(1, 2)
            if direction == 'right':
                ax.set_subplotspec(gs20[0])
                ax_new_gs = gs20[1]
            else:
                ax.set_subplotspec(gs20[1])
                ax_new_gs = gs20[0]
    return ax_new_gs

def add_subplot(ax, vert=True, sharex=None, sharey=None):
    ax_new_gs = get_subplot_grid(ax, "bottom" if vert else "right")
    ax_new = None
    if ax_new_gs:
        if sharex:
            sharex = ax
        else:
            sharex = None
        if sharey:
            sharey = ax
        else:
            sharey = None
        ax_new = ax.figure.add_subplot(ax_new_gs, sharex=sharex, sharey=sharey)
        ax.figure.subplots_adjust()
    return ax_new

def add_axes(ax, target, direction, edge=False):
    if ax is None:
        return
    if target is None:
        return
    ax_new_gs = get_subplot_grid(target, direction, edge=edge)
    ax.set_subplotspec(ax_new_gs)
    target.figure.add_axes(ax)
    ax.figure.subplots_adjust()

def move_axes(ax, target, direction, edge=False):
    if ax is None:
        return
    del_subplot(ax)
    add_axes(ax, target, direction, edge=edge)
