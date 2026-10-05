"""Example tool declarations shipped with the package.

`synthetic` exercises every schema type, progress, cancellation and failures without any scientific dependency. Host
front-ends (Napari, Fiji) and the test suites register it to test end to end:

    labconstrictor-tools register --name synthetic --prefix <any env with numpy, pandas, tifffile> \\
        --module labconstrictor_tools.examples.synthetic
"""
