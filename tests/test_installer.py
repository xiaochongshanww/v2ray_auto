import pytest

from v2ray_auto.core.installer import Installer, package_bootstrap_command


def test_debian_bootstrap_command():
    command = package_bootstrap_command("debian")
    assert "apt-get update" in command
    assert "curl" in command


def test_redhat_bootstrap_command():
    command = package_bootstrap_command("redhat")
    assert "yum install" in command
    assert "curl" in command


def test_unknown_bootstrap_command():
    with pytest.raises(RuntimeError):
        package_bootstrap_command("unknown")


def test_extract_reality_key_pair_values():
    output = "Private key: abc_private\nPublic key: xyz_public\n"
    assert Installer._extract_private_key(output) == "abc_private"
    assert Installer._extract_public_key(output) == "xyz_public"


def test_extract_reality_key_pair_new_format():
    output = "abc_private_key\nPassword (PublicKey): xyz_public_key\nHash32: somehash\n"
    assert Installer._extract_private_key(output) == "abc_private_key"
    assert Installer._extract_public_key(output) == "xyz_public_key"


def test_extract_private_key_raises_on_empty():
    with pytest.raises(RuntimeError):
        Installer._extract_private_key("")


def test_extract_private_key_actual_xray_output():
    output = (
        "PrivateKey: WOt9dOr_7Tc_e8JRrnIbVuMzAc2rlajoQnh3fEPbcng\n"
        "Password (PublicKey): eeIxe2i78ibj9RznsbiO_f-gUEd9vSc5KKCIoFNdJEE\n"
        "Hash32: GowiZ2MtzfTtPHWf1jMwTYSkVgbcz46tDDIqHWECWQU\n"
    )
    assert Installer._extract_private_key(output) == "WOt9dOr_7Tc_e8JRrnIbVuMzAc2rlajoQnh3fEPbcng"
    assert Installer._extract_public_key(output) == "eeIxe2i78ibj9RznsbiO_f-gUEd9vSc5KKCIoFNdJEE"


def test_installer_service_name_xray():
    installer = Installer(None, core="xray")  # type: ignore[arg-type]
    assert installer.service_name == "xray.service"


def test_installer_service_name_v2ray():
    installer = Installer(None, core="v2ray")  # type: ignore[arg-type]
    assert installer.service_name == "v2ray.service"


def test_installer_binary_name_xray():
    installer = Installer(None, core="xray")  # type: ignore[arg-type]
    assert installer.binary_name == "xray"


def test_installer_binary_name_v2ray():
    installer = Installer(None, core="v2ray")  # type: ignore[arg-type]
    assert installer.binary_name == "v2ray"
