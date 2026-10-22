import os
import sys

def main():
    config_path = os.path.join("libs", "hbb_common", "src", "config.rs")
    if not os.path.exists(config_path):
        print(f"Error: {config_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Branding
    content = content.replace('RwLock::new("RustDesk".to_owned())', 'RwLock::new("GS Connect".to_owned())')
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
        print("Warning: old_incoming not found")

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

if __name__ == "__main__":
    main()
