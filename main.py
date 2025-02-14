import dispatch
import graph
import image
import archive
import imgurinterface
import googleinterface


def main():
    archive.save_to_archive()
    archive.read_from_archive()
    googleinterface.update_sheet()
    graph.generate_img()
    image.final_image()
    imgurinterface.upload_image()
    dispatch.update_dispatch()


if __name__ == "__main__":
    main()
