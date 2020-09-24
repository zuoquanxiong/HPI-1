# type: ignore

"""
Photos and videos on your filesystem, their GPS and timestamps
"""

# reminder: facebook photos?
# reminder: google photos?

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, NamedTuple, Iterator, Iterable, List, Callable, Tuple

from ..core import PathIsh, Paths
from ..core.common import LazyLogger, mcachew, fastermime
from ..core.error import Res

# see https://github.com/seanbreckenridge/dotfiles/blob/master/.config/my/my/config/__init__.py for an example
from my.config import photos as config


log = LazyLogger(__name__)


# TODO ignore hidden dirs?
class LatLon(NamedTuple):
    lat: float
    lon: float


class Photo(NamedTuple):
    path: str
    dt: Optional[datetime]
    geo: Optional[LatLon]

    @property
    def tags(self) -> List[str]:  # TODO
        return []

    @property
    def _basename(self) -> str:
        # TODO 'canonical' or something? only makes sense for organized ones
        for bp in config.paths:
            if self.path.startswith(bp):
                return self.path[len(bp) :]
        else:
            raise RuntimeError(f"Weird path {self.path}, cant match against anything")

    @property
    def name(self) -> str:
        return self._basename.strip("/")


from .utils import get_exif_from_file, ExifTags, Exif, dt_from_path, convert_ref

Result = Res[Photo]


def _make_photo(
    photo: Path, mtype: str,
) -> Iterator[Result]:
    exif: Exif
    if any(x in mtype for x in {"image/png", "image/x-ms-bmp", "video"}):
        # TODO don't remember why..
        log.debug(f"skipping exif extraction for {photo} due to mime {mtype}")
        exif = {}
    else:
        exif = get_exif_from_file(photo)

    def _get_geo() -> Optional[LatLon]:
        meta = exif.get(ExifTags.GPSINFO, {})
        if ExifTags.LAT in meta and ExifTags.LON in meta:
            return LatLon(
                lat=convert_ref(meta[ExifTags.LAT], meta[ExifTags.LAT_REF]),
                lon=convert_ref(meta[ExifTags.LON], meta[ExifTags.LON_REF]),
            )
        return None

    # TODO aware on unaware?
    def _get_dt() -> Optional[datetime]:
        edt = exif.get(ExifTags.DATETIME, None)
        if edt is not None:
            dtimes = edt.replace(" 24", " 00")  # jeez maybe log it?
            if dtimes == "0000:00:00 00:00:00":
                log.warning(f"Bad exif timestamp {dtimes} for {photo}")
            else:
                dt = datetime.strptime(dtimes, "%Y:%m:%d %H:%M:%S")
                # TODO timezone is local, should take into account...
                return dt

        edt = dt_from_path(photo)  # ok, last try..

        if edt is None:
            return None

        if edt is not None and edt > datetime.now():
            # TODO also yield?
            log.error("datetime for %s is too far in future: %s", photo, edt)
            return None

        return edt

    geo = _get_geo()
    dt = _get_dt()

    yield Photo(str(photo), dt=dt, geo=geo)


# the user defines a list of PathIsh things in hpi config
# this just converts them to strings, so it can
# be passed to the subprocess
def _normalize_paths(paths: List[PathIsh]) -> Iterator[str]:
    for pt in paths:
        p = None
        if isinstance(pt, Path):
            p = pt
        else:
            p = Path(pt)
        yield str(p.expanduser().absolute())


# TODO exclude
def _candidates() -> Iterable[str]:
    # TODO that could be a bit slow if there are to many extra files?
    from subprocess import Popen, PIPE

    # TODO could extract this to common?
    with Popen(
        [
            "fd",
            "--follow",
            "-t",
            "file",
            ".",
            *_normalize_paths(config.paths),
        ],
        stdout=PIPE,
    ) as p:
        out = p.stdout
        assert out is not None
        for line in out:
            path = line.decode("utf8").rstrip("\n")
            mime = fastermime(path)
            tp = mime.split("/")[0]
            if tp in {"inode", "text", "application", "audio"}:
                continue
            if tp not in {"image", "video"}:
                # TODO yield error?
                log.warning("%s: unexpected mime %s", path, tp)
            # TODO return mime too? so we don't have to call it again in _photos?
            yield path


def photos() -> Iterator[Result]:
    candidates = tuple(sorted(_candidates()))
    return _photos(candidates)
    # TODO figure out how to use cachew without helper function?
    # I guess need lazy variables or something?


# TODO is there something more standard?
# @mcachew(cache_path=config.cache_path)
def _photos(candidates: Iterable[str]) -> Iterator[Result]:

    for path in map(Path, candidates):
        if config.ignored(path):
            log.info("ignoring %s due to config", path)
            continue

        print(path)

        # WHY?? dont get why we're doing this
        # parent_geo = get_geo(path.parent)
        mime = fastermime(str(path))
        yield from _make_photo(path, mime)


def print_all():
    for p in photos():
        if isinstance(p, Exception):
            print("ERROR!", p)
        else:
            print(f"{p.dt} {p.path} {p.tags}")


# TODO cachew -- improve AttributeError: type object 'tuple' has no attribute '__annotations__' -- improve errors?
# TODO cachew -- invalidate if function code changed?
