from beets.library import Item


def moss_create_track(uuid, tmpfname, path):
    """
    Uploads the file to moss. If it fails, raises an exception.
    """
    # TODO
    pass


def impala_create_track(uuid, tmpfname, path):
    """
    Creates the data corresponding to the track in impala based on metadata
    gleaned from beets. If it fails, raises an exception.
    """
    # TODO
    i = Item.from_path(tmpfname)
    pass
