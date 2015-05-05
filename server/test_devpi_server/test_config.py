from devpi_server.config import MyArgumentParser, parseoptions, get_pluginmanager
from devpi_server.main import Fatal
import pytest

class TestParser:

    def test_addoption(self):
        parser = MyArgumentParser()
        parser.addoption("--hello", type=str)
        args = parser.parse_args(["--hello", "world"])
        assert args.hello == "world"

    def test_addoption_default_added_to_help(self):
        parser = MyArgumentParser()
        opt = parser.addoption("--hello", type=str, help="x", default="world")
        assert "[world]" in opt.help

    def test_addoption_getdefault(self):
        def getter(name):
            return dict(hello="world2")[name]
        parser = MyArgumentParser(defaultget=getter)
        opt = parser.addoption("--hello", default="world", type=str, help="x")
        assert opt.default == "world2"
        assert "[world2]" in opt.help
        opt = parser.addoption("--hello2", default="world", type=str, help="x")
        assert opt.default == "world"
        assert "[world]" in opt.help

    def test_addgroup(self):
        parser = MyArgumentParser()
        group = parser.addgroup("hello")
        opt = group.addoption("--hello", default="world", type=str, help="x")
        assert opt.default == "world"
        assert "[world]" in opt.help

    def test_addsubparser(self):
        parser = MyArgumentParser()
        sub = parser.add_subparsers()
        p = sub.add_parser("hello")
        assert isinstance(p, MyArgumentParser)

class TestConfig:
    def test_parse_secret(self, tmpdir):
        p = tmpdir.join("secret")
        secret = "qwoieuqwelkj123"
        p.write(secret)
        config = parseoptions(["devpi-server", "--secretfile=%s" % p])
        assert config.secretfile == str(p)
        assert config.secret == secret
        config = parseoptions(["devpi-server", "--serverdir", tmpdir])
        assert config.secretfile == tmpdir.join(".secret")
        config.secretfile.write(secret)
        assert config.secret == config.secretfile.read()

    def test_generated_secret_if_not_exists(self,
                                            xom, tmpdir, monkeypatch):
        config = xom.config
        secfile = tmpdir.join("secret")
        monkeypatch.setattr(config, "secretfile", secfile)
        assert not secfile.check()
        assert config.secret
        assert config.secret == config.secretfile.read()
        assert config.secretfile == secfile
        #recs = caplog.getrecords()

    def test_devpi_serverdir_env(self, tmpdir, monkeypatch):
        monkeypatch.setenv("DEVPI_SERVERDIR", tmpdir)
        config = parseoptions(["devpi-server"])
        assert config.serverdir == tmpdir

    def test_role_permanence_master(self, tmpdir):
        config = parseoptions(["devpi-server", "--serverdir", str(tmpdir)])
        assert config.role == "master"
        config = parseoptions(["devpi-server", "--role=master",
                               "--serverdir", str(tmpdir)])
        assert config.role == "master"
        with pytest.raises(Fatal):
            parseoptions(["devpi-server", "--role=replica",
                          "--serverdir", str(tmpdir)])

    def test_role_permanence_replica(self, tmpdir):
        config = parseoptions(["devpi-server", "--master-url", "http://qwe",
                               "--serverdir", str(tmpdir)])
        assert config.role == "replica"
        assert not config.get_master_uuid()
        with pytest.raises(Fatal) as excinfo:
            parseoptions(["devpi-server", "--serverdir", str(tmpdir)])
        assert "specify --role=master" in str(excinfo.value)
        config = parseoptions(["devpi-server", "--serverdir", str(tmpdir),
                               "--role=master"])
        assert config.role == "master"
        with pytest.raises(Fatal):
            parseoptions(["devpi-server", "--master-url=xyz",
                          "--serverdir", str(tmpdir)])
        with pytest.raises(Fatal):
            parseoptions(["devpi-server", "--role=replica",
                          "--serverdir", str(tmpdir)])

    def test_replica_role_missing_master_url(self, tmpdir):
        with pytest.raises(Fatal) as excinfo:
            parseoptions(["devpi-server", "--role=replica",
                          "--serverdir", str(tmpdir)])
        assert "need to specify --master-url" in str(excinfo)

    def test_uuid(self, tmpdir):
        config = parseoptions(["devpi-server", "--serverdir", str(tmpdir)])
        uuid = config.nodeinfo["uuid"]
        assert uuid
        assert config.get_master_uuid() == uuid
        config = parseoptions(["devpi-server", "--serverdir", str(tmpdir)])
        assert uuid == config.nodeinfo["uuid"]
        tmpdir.remove()
        config = parseoptions(["devpi-server", "--serverdir", str(tmpdir)])
        assert config.nodeinfo["uuid"] != uuid
        assert config.get_master_uuid() != uuid

    def test_add_parser_options_called(self):
        l = []
        class Plugin:
            def devpiserver_add_parser_options(self, parser):
                l.append(parser)
        pm = get_pluginmanager()
        pm.register(Plugin())
        parseoptions(["devpi-server"], pluginmanager=pm)
        assert len(l) == 1
        assert isinstance(l[0], MyArgumentParser)

