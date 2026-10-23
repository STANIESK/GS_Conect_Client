import os
import sys

def patch_hbb_common_config():
    config_path = os.path.join("libs", "hbb_common", "src", "config.rs")
    if not os.path.exists(config_path):
        print(f"Error: {config_path} not found", file=sys.stderr)
        return False

    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Branding
    content = content.replace('RwLock::new("RustDesk".to_owned())', 'RwLock::new("GS-Connect".to_owned())')
    # 2. Server IP
    content = content.replace('&["rs-ny.rustdesk.com"]', '&["gsconnect.gsurfnet.com"]')
    # 3. Server Public Key
    content = content.replace('OeVuKk5nlHiXp+APNn0Y3pC1Iwpwn44JGqrQCsWqmBw=', '6G5voXXb6dZwFx3tlAeJS6iXo43q7nOPKaRdi5YESDQ=')

    # 4. Inject is_qs_mode helper
    qs_helper = """
#[inline]
pub fn is_qs_mode() -> bool {
    if let Ok(name) = std::env::var("RUSTDESK_APPNAME") {
        let lower = name.to_lowercase();
        if lower.contains("suporte") || lower.contains("-qs") || lower.contains("_qs") || lower.contains("quick") {
            return true;
        }
    }
    if let Ok(exe) = std::env::current_exe() {
        let name = exe.file_name().unwrap_or_default().to_string_lossy().to_lowercase();
        if name.contains("suporte") || name.contains("-qs") || name.contains("_qs") || name.contains("quick") {
            return true;
        }
    }
    if std::env::args().any(|a| a == "--qs" || a == "--quick_support" || a == "--quick-support" || a == "--incoming-only") {
        return true;
    }
    false
}
"""

    old_incoming = """#[inline]
pub fn is_incoming_only() -> bool {
    HARD_SETTINGS
        .read()
        .unwrap()
        .get("conn-type")
        .map_or(false, |x| x == ("incoming"))
}"""

    new_incoming = f"""{qs_helper}
#[inline]
pub fn is_incoming_only() -> bool {{
    if is_qs_mode() {{
        return true;
    }}
    HARD_SETTINGS
        .read()
        .unwrap()
        .get("conn-type")
        .map_or(false, |x| x == ("incoming"))
}}"""

    if old_incoming in content:
        content = content.replace(old_incoming, new_incoming, 1)
        print("Patched is_incoming_only with QS support.")
    else:
        print("Notice: old_incoming already patched or not found")

    # 5. Disable settings in QS mode
    old_settings = """#[inline]
pub fn is_disable_settings() -> bool {
    is_some_hard_opton("disable-settings")
}"""
    new_settings = """#[inline]
pub fn is_disable_settings() -> bool {
    if is_qs_mode() {
        return true;
    }
    is_some_hard_opton("disable-settings")
}"""
    if old_settings in content:
        content = content.replace(old_settings, new_settings, 1)
        print("Patched is_disable_settings for QS mode.")

    # 6. Disable installation prompt in QS mode
    old_install = """#[inline]
pub fn is_disable_installation() -> bool {
    is_some_hard_opton("disable-installation")
}"""
    new_install = """#[inline]
pub fn is_disable_installation() -> bool {
    if is_qs_mode() {
        return true;
    }
    is_some_hard_opton("disable-installation")
}"""
    if old_install in content:
        content = content.replace(old_install, new_install, 1)
        print("Patched is_disable_installation for QS mode.")

    # 7. Numeric one-time password in QS mode
    old_opt = "pub fn option2bool(option: &str, value: &str) -> bool {"
    new_opt = """pub fn option2bool(option: &str, value: &str) -> bool {
    if is_qs_mode() && option == keys::OPTION_ALLOW_NUMERNIC_ONE_TIME_PASSWORD {
        return true;
    }"""
    if old_opt in content:
        content = content.replace(old_opt, new_opt, 1)
        print("Patched numeric one time password for QS mode.")

    with open(config_path, "w", encoding="utf-8") as f:
        f.write(content)

    print("Successfully patched libs/hbb_common/src/config.rs for GS Connect and Quick Support")
    return True

def patch_sso_enforcement():
    # 1. Rust layer: src/ui_session_interface.rs
    ui_session_path = os.path.join("src", "ui_session_interface.rs")
    if os.path.exists(ui_session_path):
        with open(ui_session_path, "r", encoding="utf-8") as f:
            content = f.read()

        old_token = '    let token = LocalConfig::get_option("access_token");\n    let key = crate::get_key(false).await;'
        new_token = '''    let token = LocalConfig::get_option("access_token");
    if token.is_empty() {
        handler.on_error("Acesso Restrito: É obrigatório autenticar com sua conta Google Workspace (@gsurf.com.br / @gsurfnet.com) no GS Connect para estabelecer conexões remotas.");
        return;
    }
    let key = crate::get_key(false).await;'''

        if old_token in content:
            content = content.replace(old_token, new_token, 1)
            with open(ui_session_path, "w", encoding="utf-8") as f:
                f.write(content)
            print("Successfully patched src/ui_session_interface.rs with Google SSO outbound connection lock.")
        else:
            print("Notice: src/ui_session_interface.rs already patched or target not found.")

    # 2. Flutter UI layer: flutter/lib/common.dart
    common_dart_path = os.path.join("flutter", "lib", "common.dart")
    if os.path.exists(common_dart_path):
        with open(common_dart_path, "r", encoding="utf-8") as f:
            dart_content = f.read()

        # Import login.dart if not present
        if "import 'common/widgets/login.dart';" not in dart_content:
            target_imp = "import 'common/widgets/overlay.dart';"
            if target_imp in dart_content:
                dart_content = dart_content.replace(target_imp, target_imp + "\nimport 'common/widgets/login.dart';")
                print("Added import of login.dart to flutter/lib/common.dart")

        # Inject SSO check in connectMainDesktop
        old_fn = "bool? isSharedPassword}) async {\n  if (isFileTransfer) {"
        new_fn = """bool? isSharedPassword}) async {
  final authToken = bind.mainGetLocalOption(key: 'access_token');
  if (authToken.isEmpty) {
    showToast("Acesso Restrito: É obrigatório autenticar com sua conta Google Workspace (@gsurf.com.br / @gsurfnet.com) para estabelecer conexões remotas.");
    loginDialog();
    return;
  }
  if (isFileTransfer) {"""

        if old_fn in dart_content:
            dart_content = dart_content.replace(old_fn, new_fn, 1)
            with open(common_dart_path, "w", encoding="utf-8") as f:
                f.write(dart_content)
            print("Successfully patched flutter/lib/common.dart with UI Google SSO lock.")
        else:
            print("Notice: flutter/lib/common.dart already patched or target not found.")

def patch_manifests():
    manifest_files = [os.path.join("res", "manifest.xml"), os.path.join("flutter", "windows", "runner", "runner.exe.manifest")]
    trust_info = """  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
    <security>
      <requestedPrivileges>
        <requestedExecutionLevel level="asInvoker" uiAccess="false" />
      </requestedPrivileges>
    </security>
  </trustInfo>
"""
    for mf in manifest_files:
        if os.path.exists(mf):
            with open(mf, "r", encoding="utf-8") as mf_f:
                mfc = mf_f.read()
            if "trustInfo" not in mfc:
                mfc = mfc.replace('<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">', '<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">\n' + trust_info)
                with open(mf, "w", encoding="utf-8") as mf_f:
                    mf_f.write(mfc)
                print(f"Patched {mf} with asInvoker trustInfo")

def main():
    patch_hbb_common_config()
    patch_sso_enforcement()
    patch_manifests()

if __name__ == "__main__":
    main()
