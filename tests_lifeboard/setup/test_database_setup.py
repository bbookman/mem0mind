import os

def test_database_dockerfile_exists():
    assert os.path.exists("database/Dockerfile")
    assert os.path.isfile("database/Dockerfile")

def test_database_init_sql_exists():
    assert os.path.exists("database/init.sql")
    assert os.path.isfile("database/init.sql")
