from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_requirements_only_list_imported_runtime_packages():
    requirements = (ROOT / "requirements.txt").read_text()
    project = (ROOT / "pyproject.toml").read_text()
    for unused in ("matplotlib", "PyWavelets"):
        assert unused not in requirements
        assert unused not in project


def test_requirements_and_project_keep_core_runtime_packages_aligned():
    requirements = (ROOT / "requirements.txt").read_text().casefold()
    project = (ROOT / "pyproject.toml").read_text().casefold()
    for package in ("pillow", "numpy", "opencv-python-headless", "scikit-image",
                    "scikit-learn", "joblib", "streamlit", "authlib", "supabase", "onnxruntime"):
        assert package in requirements
        assert package in project
