from v2ray_auto.core.os_release import parse_os_release


def test_parse_ubuntu():
    distro, family = parse_os_release('ID="ubuntu"\nID_LIKE="debian"')
    assert distro == "ubuntu"
    assert family == "debian"


def test_parse_centos():
    distro, family = parse_os_release('ID="centos"\nID_LIKE="rhel fedora"')
    assert distro == "centos"
    assert family == "redhat"


def test_parse_unknown():
    distro, family = parse_os_release('ID="arch"')
    assert distro == "arch"
    assert family == "unknown"
