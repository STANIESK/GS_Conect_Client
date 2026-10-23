import os
import shutil
import subprocess
import glob

def run(cmd):
    print(f"+ {cmd}")
    res = subprocess.run(cmd, shell=True)
    if res.returncode != 0:
        raise RuntimeError(f"Command failed with code {res.returncode}: {cmd}")

def main():
    version = os.environ.get("VERSION", "1.4.18")
    flutter_bundle = os.path.abspath("flutter/build/linux/x64/release/bundle")
    if not os.path.exists(flutter_bundle):
        # Look for release folder
        candidates = glob.glob("flutter/build/linux/**/release/bundle", recursive=True)
        if candidates:
            flutter_bundle = os.path.abspath(candidates[0])
        else:
            raise FileNotFoundError("Could not find flutter linux release bundle")

    print(f"Using Flutter bundle from: {flutter_bundle}")
    os.makedirs("deb_output", exist_ok=True)

    # ==========================================
    # 1. BUILD gs-connect.deb (Full / Técnico)
    # ==========================================
    pkg_full = "tmpdeb_full"
    shutil.rmtree(pkg_full, ignore_errors=True)
    os.makedirs(f"{pkg_full}/usr/share/gs-connect", exist_ok=True)
    os.makedirs(f"{pkg_full}/usr/bin", exist_ok=True)
    os.makedirs(f"{pkg_full}/usr/share/applications", exist_ok=True)
    os.makedirs(f"{pkg_full}/usr/share/icons/hicolor/256x256/apps", exist_ok=True)
    os.makedirs(f"{pkg_full}/usr/share/icons/hicolor/scalable/apps", exist_ok=True)
    os.makedirs(f"{pkg_full}/usr/share/gs-connect/files/systemd", exist_ok=True)
    os.makedirs(f"{pkg_full}/DEBIAN", exist_ok=True)

    # Copy binary files
    run(f"cp -r {flutter_bundle}/* {pkg_full}/usr/share/gs-connect/")
    if os.path.exists(f"{pkg_full}/usr/share/gs-connect/rustdesk"):
        os.rename(f"{pkg_full}/usr/share/gs-connect/rustdesk", f"{pkg_full}/usr/share/gs-connect/gs-connect")
    
    # Symlink in /usr/bin
    run(f"ln -s /usr/share/gs-connect/gs-connect {pkg_full}/usr/bin/gs-connect")
    run(f"ln -s /usr/share/gs-connect/gs-connect {pkg_full}/usr/bin/rustdesk")

    # Icons
    if os.path.exists("res/128x128@2x.png"):
        shutil.copyfile("res/128x128@2x.png", f"{pkg_full}/usr/share/icons/hicolor/256x256/apps/gs-connect.png")
    if os.path.exists("res/scalable.svg"):
        shutil.copyfile("res/scalable.svg", f"{pkg_full}/usr/share/icons/hicolor/scalable/apps/gs-connect.svg")

    # Desktop shortcut
    with open(f"{pkg_full}/usr/share/applications/gs-connect.desktop", "w", encoding="utf-8") as f:
        f.write("""[Desktop Entry]
Name=GS-Connect
GenericName=Acesso Remoto Corporativo
Comment=GS Connect - Plataforma Corporativa de Acesso Remoto GSurf
Exec=/usr/share/gs-connect/gs-connect %u
Icon=gs-connect
Terminal=false
Type=Application
StartupNotify=true
Categories=Network;RemoteAccess;GTK;
Keywords=gsconnect;gsurf;remote-control;rdp;desktop;
""")

    # Systemd service
    with open(f"{pkg_full}/usr/share/gs-connect/files/systemd/gs-connect.service", "w", encoding="utf-8") as f:
        f.write("""[Unit]
Description=GS Connect Unattended Remote Support Service
After=network.target

[Service]
Type=simple
ExecStart=/usr/share/gs-connect/gs-connect --service
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
""")

    # DEBIAN/control
    with open(f"{pkg_full}/DEBIAN/control", "w", encoding="utf-8") as f:
        f.write(f"""Package: gs-connect
Section: net
Priority: optional
Version: {version}
Architecture: amd64
Maintainer: GSurf Tecnologia <suporte@gsurfnet.com>
Homepage: https://gsconnect.gsurfnet.com
Depends: libgtk-3-0t64 | libgtk-3-0, libxcb-randr0, libxdo3 | libxdo4, libxfixes3, libxcb-shape0, libxcb-xfixes0, libasound2t64 | libasound2, libsystemd0, curl, libva2, libva-drm2, libva-x11-2, libgstreamer-plugins-base1.0-0, gstreamer1.0-pipewire | gstreamer1.0-plugins-base
Recommends: libayatana-appindicator3-1
Description: GS Connect - Plataforma Corporativa Oficial de Acesso Remoto GSurf.
 Conexao remota segura de alta performance com autenticacao corporativa Google Workspace.
""")

    # DEBIAN/postinst
    with open(f"{pkg_full}/DEBIAN/postinst", "w", encoding="utf-8") as f:
        f.write("""#!/bin/bash
set -e
if [ "$1" = "configure" ]; then
    mkdir -p /usr/lib/systemd/system/
    cp /usr/share/gs-connect/files/systemd/gs-connect.service /usr/lib/systemd/system/gs-connect.service
    if command -v systemctl >/dev/null 2>&1; then
        systemctl daemon-reload || true
        systemctl enable gs-connect || true
        systemctl restart gs-connect || true
    fi
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database -q || true
    fi
fi
""")
    os.chmod(f"{pkg_full}/DEBIAN/postinst", 0o755)

    # DEBIAN/prerm
    with open(f"{pkg_full}/DEBIAN/prerm", "w", encoding="utf-8") as f:
        f.write("""#!/bin/bash
set -e
if [ "$1" = "remove" ] || [ "$1" = "upgrade" ]; then
    if command -v systemctl >/dev/null 2>&1; then
        systemctl stop gs-connect || true
        systemctl disable gs-connect || true
    fi
fi
""")
    os.chmod(f"{pkg_full}/DEBIAN/prerm", 0o755)

    run(f"dpkg-deb -b {pkg_full} deb_output/gs-connect.deb")
    print("Created deb_output/gs-connect.deb successfully!")

    # ==========================================
    # 2. BUILD gs-connect-suporte.deb (Quick Support)
    # ==========================================
    pkg_qs = "tmpdeb_qs"
    shutil.rmtree(pkg_qs, ignore_errors=True)
    os.makedirs(f"{pkg_qs}/usr/share/gs-connect-suporte", exist_ok=True)
    os.makedirs(f"{pkg_qs}/usr/bin", exist_ok=True)
    os.makedirs(f"{pkg_qs}/usr/share/applications", exist_ok=True)
    os.makedirs(f"{pkg_qs}/usr/share/icons/hicolor/256x256/apps", exist_ok=True)
    os.makedirs(f"{pkg_qs}/usr/share/icons/hicolor/scalable/apps", exist_ok=True)
    os.makedirs(f"{pkg_qs}/DEBIAN", exist_ok=True)

    # Copy binary files
    run(f"cp -r {flutter_bundle}/* {pkg_qs}/usr/share/gs-connect-suporte/")
    if os.path.exists(f"{pkg_qs}/usr/share/gs-connect-suporte/rustdesk"):
        os.rename(f"{pkg_qs}/usr/share/gs-connect-suporte/rustdesk", f"{pkg_qs}/usr/share/gs-connect-suporte/gs-connect-suporte")

    # Wrapper script in /usr/bin/gs-connect-suporte
    with open(f"{pkg_qs}/usr/bin/gs-connect-suporte", "w", encoding="utf-8") as f:
        f.write("""#!/bin/bash
exec /usr/share/gs-connect-suporte/gs-connect-suporte --quick_support "$@"
""")
    os.chmod(f"{pkg_qs}/usr/bin/gs-connect-suporte", 0o755)

    # Icons
    if os.path.exists("res/128x128@2x.png"):
        shutil.copyfile("res/128x128@2x.png", f"{pkg_qs}/usr/share/icons/hicolor/256x256/apps/gs-connect-suporte.png")
    if os.path.exists("res/scalable.svg"):
        shutil.copyfile("res/scalable.svg", f"{pkg_qs}/usr/share/icons/hicolor/scalable/apps/gs-connect-suporte.svg")

    # Desktop shortcut
    with open(f"{pkg_qs}/usr/share/applications/gs-connect-suporte.desktop", "w", encoding="utf-8") as f:
        f.write("""[Desktop Entry]
Name=GS-Connect Suporte
GenericName=Suporte Rápido GSurf
Comment=GS Connect Suporte - Atendimento Remoto Rápido GSurf
Exec=/usr/bin/gs-connect-suporte %u
Icon=gs-connect-suporte
Terminal=false
Type=Application
StartupNotify=true
Categories=Network;RemoteAccess;GTK;
Keywords=gsconnect;gsurf;suporte;quick-support;atendimento;
""")

    # DEBIAN/control
    with open(f"{pkg_qs}/DEBIAN/control", "w", encoding="utf-8") as f:
        f.write(f"""Package: gs-connect-suporte
Section: net
Priority: optional
Version: {version}
Architecture: amd64
Maintainer: GSurf Tecnologia <suporte@gsurfnet.com>
Homepage: https://gsconnect.gsurfnet.com
Depends: libgtk-3-0t64 | libgtk-3-0, libxcb-randr0, libxdo3 | libxdo4, libxfixes3, libxcb-shape0, libxcb-xfixes0, libasound2t64 | libasound2, libsystemd0, curl, libva2, libva-drm2, libva-x11-2, libgstreamer-plugins-base1.0-0, gstreamer1.0-pipewire | gstreamer1.0-plugins-base
Recommends: libayatana-appindicator3-1
Description: GS Connect Suporte - Acesso Rapido para Suporte Tecnico GSurf.
 Versao compacta somente para recepcao de suporte (Incoming-Only, sem necessidade de login Google).
""")

    # DEBIAN/postinst
    with open(f"{pkg_qs}/DEBIAN/postinst", "w", encoding="utf-8") as f:
        f.write("""#!/bin/bash
set -e
if [ "$1" = "configure" ]; then
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database -q || true
    fi
fi
""")
    os.chmod(f"{pkg_qs}/DEBIAN/postinst", 0o755)

    run(f"dpkg-deb -b {pkg_qs} deb_output/gs-connect-suporte.deb")
    print("Created deb_output/gs-connect-suporte.deb successfully!")

    # Clean tmp directories
    shutil.rmtree(pkg_full, ignore_errors=True)
    shutil.rmtree(pkg_qs, ignore_errors=True)
    run("ls -lh deb_output/")

if __name__ == "__main__":
    main()
