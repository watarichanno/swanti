import dispatch
import archive
import googleinterface


def main():
    archive.save_to_archive()
    archive.read_from_archive()
    googleinterface.update_sheet()
    dispatch.update_dispatch()


if __name__ == "__main__":
    main()
