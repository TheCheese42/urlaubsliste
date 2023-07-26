Remove-Item __main__.dist -r -fo

nuitka `
    -o "Urlaubsliste Deluxe.exe" `
    --enable-plugin=pyqt5 `
    --standalone `
    --include-data-dir=urlaubsliste/ui=ui/ `
    --include-data-dir=urlaubsliste/icons=icons/ `
    --include-data-files=urlaubsliste/icons.qrc=icons.qrc `
    --windows-icon-from-ico=appicon.ico `
    --disable-console `
    --show-progress `
    --show-memory `
    urlaubsliste/__main__.py