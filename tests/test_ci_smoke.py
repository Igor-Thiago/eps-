from pathlib import Path


def test_project_entrypoints_exist():
    project_root = Path(__file__).resolve().parents[1]

    assert (project_root / "manage.py").is_file()
    assert (project_root / "pcdf" / "settings.py").is_file()
    assert (project_root / "src" / "olaseguranca.py").is_file()
