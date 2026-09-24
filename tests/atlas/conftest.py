import csv
from pathlib import Path

import pytest

from tests.support.paths import ATLAS_META_PATH, ATLAS_DATA_PATH


def _strip_id_column(source: Path, dest: Path) -> None:
    # data/atlas/{meta,data}.csv carry a leading surrogate `id` column
    # (a DB export artifact) that MAPPING_META_SCHEMA/MAPPING_DATA_SCHEMA
    # don't include. Positional CSV reads with an explicit schema need
    # the column dropped, so tests work from a stripped copy.
    with open(source, newline='') as src, open(dest, 'w', newline='') as dst:
        reader = csv.reader(src)
        writer = csv.writer(dst)
        for row in reader:
            writer.writerow(row[1:])


@pytest.fixture(scope='session')
def atlas_meta_path(tmp_path_factory) -> str:
    dest = tmp_path_factory.mktemp('atlas') / 'meta.csv'
    _strip_id_column(Path(ATLAS_META_PATH), dest)
    return str(dest)


@pytest.fixture(scope='session')
def atlas_data_path(tmp_path_factory) -> str:
    dest = tmp_path_factory.mktemp('atlas') / 'data.csv'
    _strip_id_column(Path(ATLAS_DATA_PATH), dest)
    return str(dest)
