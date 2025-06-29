import os

def test_backend_directories_exist():
    assert os.path.exists("backend/n8n_workflows")
    assert os.path.isdir("backend/n8n_workflows")
    assert os.path.exists("backend/custom_nodes")
    assert os.path.isdir("backend/custom_nodes")

def test_frontend_directory_exists():
    assert os.path.exists("frontend/react_app")
    assert os.path.isdir("frontend/react_app")

def test_database_directory_exists():
    assert os.path.exists("database")
    assert os.path.isdir("database")

def test_test_directory_exists():
    # This test will test for its own directory structure
    assert os.path.exists("tests_lifeboard")
    assert os.path.isdir("tests_lifeboard")
    assert os.path.exists("tests_lifeboard/setup")
    assert os.path.isdir("tests_lifeboard/setup")

def test_docs_directory_exists():
    assert os.path.exists("docs_lifeboard")
    assert os.path.isdir("docs_lifeboard")

def test_config_directory_exists():
    assert os.path.exists("config_lifeboard")
    assert os.path.isdir("config_lifeboard")

def test_placeholder_files_exist():
    # Verifying a few key ones as representative
    assert os.path.exists("backend/n8n_workflows/.placeholder")
    assert os.path.exists("frontend/react_app/.placeholder")
    assert os.path.exists("database/.placeholder")
    assert os.path.exists("tests_lifeboard/.placeholder")
    assert os.path.exists("docs_lifeboard/.placeholder")
    assert os.path.exists("config_lifeboard/.placeholder")
