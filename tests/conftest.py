import pytest

from labeling_etl import db

DATA_DIR = db.REPO_ROOT / "data"
PAPAYA_IMAGES = DATA_DIR / "papaya" / "papaya_output_images.csv"
PAPAYA_LABELS = DATA_DIR / "papaya" / "papaya_output_labels.csv"
KUMQUAT_CSV = DATA_DIR / "kumquat" / "kumquat_output.csv"


@pytest.fixture()
def data_dir():
    return DATA_DIR


@pytest.fixture()
def conn():
    connection = db.connect(":memory:")
    db.create_schema(connection)
    yield connection
    connection.close()


@pytest.fixture()
def papaya_loaded(conn):
    from labeling_etl.loaders import PapayaLoader

    result = PapayaLoader(PAPAYA_IMAGES, PAPAYA_LABELS).run(conn)
    return conn, result


@pytest.fixture()
def fully_loaded(conn):
    from labeling_etl.dedup import deduplicate_labels
    from labeling_etl.loaders import KumquatLoader, PapayaLoader

    PapayaLoader(PAPAYA_IMAGES, PAPAYA_LABELS).run(conn)
    KumquatLoader(KUMQUAT_CSV).run(conn)
    deleted = deduplicate_labels(conn)
    return conn, deleted
