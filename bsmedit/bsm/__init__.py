try:
    import bsmplot
    import bsmplot.bsm
    pkgs = ['ulog', 'vcds', 'csvs', 'mat', 'zmqs']
    auto_load_module_external = [f"bsmplot.bsm.{pkg}" for pkg in pkgs]
except:
    auto_load_module_external = []

auto_load_module = [
    'shell', 'editor', 'graph', 'sim', 'misctools', 'debugtool'
]
