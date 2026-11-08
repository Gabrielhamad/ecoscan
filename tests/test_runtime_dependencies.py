from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_requirements_only_list_imported_runtime_packages():
    requirements = (ROOT / "requirements.in").read_text()
    project = (ROOT / "pyproject.toml").read_text()
    for unused in ("matplotlib",):
        assert unused not in requirements
        assert unused not in project


def test_requirements_and_project_keep_core_runtime_packages_aligned():
    requirements = (ROOT / "requirements.in").read_text().casefold()
    project = (ROOT / "pyproject.toml").read_text().casefold()
    for package in ("pillow", "numpy", "opencv-python-headless", "scikit-image", "pywavelets",
                    "scikit-learn", "streamlit", "authlib", "supabase", "onnxruntime"):
        assert package in requirements
        assert package in project


def test_deploy_requirements_consumes_hashed_lock():
    assert (ROOT / "requirements.txt").read_text().strip() == "-r requirements.lock"
