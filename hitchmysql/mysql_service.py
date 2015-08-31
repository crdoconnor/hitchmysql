from hitchserve import Service
from os.path import join
import signal
import shutil
import sys



class MySQLDatabase(object):
    def __init__(self, name, owner, dump=None):
        self.name = name
        self.owner = owner
        self.dump = dump

    #def psql(self, command=None):
        #"""Run PSQL command on this database."""
        #return self.database_of.psql(command=command, database=self.name)

    #def pg_dump(self, filename=None):
        #"""Dump this database to 'filename'."""
        #return self.database_of.pg_dump(filename, database=self.name)

    @property
    def database_of(self):
        return self._database_of

    @database_of.setter
    def database_of(self, value):
        self._database_of = value

class MySQLUser(object):
    def __init__(self, username, password):
        self.username = username
        self.password = password

class MySQLService(Service):
    stop_signal = signal.SIGTERM

    def __init__(self, mysql_package, port=3306, users=None, databases=None, **kwargs):
        self.mysql_package = mysql_package
        #self.encoding = encoding
        #self.locale = locale
        self.port = port
        self.users = users
        self.databases = databases
        self.datadir = None
        kwargs['log_line_ready_checker'] = lambda line: "ready for connections" in line
        super(MySQLService, self).__init__(**kwargs)

    @property
    def databases(self):
        return self._databases

    @databases.setter
    def databases(self, value):
        self._databases = value
        if self.databases is not None:
            for database in self._databases:
                database.database_of = self

    @property
    def datadir(self):
        if self._datadir is None:
            return join(self.service_group.hitch_dir.hitch_dir, 'mysqldata')
        else:
            return self._datadir

    @datadir.setter
    def datadir(self, value):
        """Location of data directory used by MySQL for this test run."""
        self._datadir = value

    @property
    def mycnf(self):
        """Location of my.cnf required to run service."""
        return join(self.mysql_package.directory, "my.cnf")


    @Service.command.getter
    def command(self):
        if self._command is None:
            return [
                        self.mysql_package.mysqld,
                        '--defaults-file={}'.format(self.mycnf),
                        '--port={}'.format(str(self.port)),
                        '--datadir={}'.format(self.datadir),
                   ]
        else:
            return self._command

    def setup(self):
        self.log("Initializing mysql database...")
        try:
            shutil.rmtree(self.datadir, ignore_errors=True)
            self.subcommand(
                self.mysql_package.mysql_install_db,
                "--basedir={}".format(join(self.mysql_package.directory)),
                "--datadir={}".format(self.datadir),
                "--defaults-file={}".format(self.mycnf)
            ).run()
        except Exception as e:
            self.warn(str(e))
        self.log("Done initializing mysql database...")

    def poststart(self):
        self.log("Creating users and databases...")
        for user in self.users:
            self.mysql(
                """create user '{}'@'localhost' identified by '{}';""".format(user.username, user.password)
            ).run()
        for database in self.databases:
            self.mysql("""create database {};""".format(database.name)).run()
            self.mysql("""grant all on {}.* to '{}'@'localhost';""".format(database.name, database.owner.username)).run()
            #if database.dump is not None:
                #self.psql(database=database.name, filename=database.dump).run()

    def mysql(self, command=None, database=None, filename=None):
        """Run PSQL command."""
        cmd = [
                self.mysql_package.mysql, "-u", "root",
                "--port={}".format(self.port),
                "--protocol=tcp",
            ] + (
                ["-e", command, ] if command is not None else []
            ) + (
                ["-D", database, ] if database is not None else []
            )
        return self.subcommand(*tuple(cmd))

    #def pg_dump(self, filename=None, database="template1"):
        #"""Dump a database."""
        #return self.subcommand(
            #*tuple([
                #self.postgres_package.pg_dump,
                #"-d", database, "-p", str(self.port), "--host", self.pgdata,
            #] + (
                #["-f", filename, ] if filename is not None else []
            #))
        #)

    #def pg_restore(self, filename, database="template1"):
        #"""Restore a database."""
        #return self.subcommand(*tuple([
            #self.postgres_package.pg_restore, "-d", database, "-p",
            #str(self.port), "--host", self.pgdata, filename
        #]))