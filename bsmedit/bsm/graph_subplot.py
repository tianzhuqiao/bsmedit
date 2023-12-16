import matplotlib

def get_gridspec(ax, g):
    # check if subplot ax is in g, if yes, return the gridspec
    ga = ax.get_gridspec()
    while True:
        if isinstance(ga, matplotlib.gridspec.GridSpecFromSubplotSpec):
            if ga._subplot_spec.get_gridspec() == g:
                return ga
            ga = ga._subplot_spec
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
    if r>1:
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
            if r > 2:
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
    fig.subplots_adjust()

def add_subplot(ax, vert=True, sharex=None, sharey=None):
    # add subplot after ax
    g = ax.get_gridspec()
    r, c, s, _ = ax.get_subplotspec().get_geometry()
    ax_new_gs = None
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
            for a in ax.figure.axes:
                # update all the subplot in the same gridspac as ax
                if a.get_gridspec() != g:
                    continue
                _, _, i, _ = a.get_subplotspec().get_geometry()
                if i>s:
                    i = i+1
                a.set_subplotspec(g2[i])
            # the gridspec for the new subplot
            ax_new_gs = g2[s+1]
        else:
            gs20 = g[s].subgridspec(2, 1)
            ax.set_subplotspec(gs20[0])
            ax_new_gs = gs20[1]
    else:
        if r == 1:
            if isinstance(g, matplotlib.gridspec.GridSpecFromSubplotSpec):
                gp =  ax.get_gridspec()._subplot_spec.get_gridspec()
                _, _, sp, _ =  ax.get_gridspec()._subplot_spec.get_geometry()
                g2 = gp[sp].subgridspec(r, c+1)
            else:
                g2 = matplotlib.gridspec.GridSpec(r, c+1)
            for a in ax.figure.axes:
                if a.get_gridspec() != g:
                    continue
                _, _, i, _ = a.get_subplotspec().get_geometry()
                if i>s:
                    i = i+1
                a.set_subplotspec(g2[i])
            ax_new_gs = g2[s+1]
        else:
            gs20 = g[s].subgridspec(1, 2)
            ax.set_subplotspec(gs20[0])
            ax_new_gs = gs20[1]

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
