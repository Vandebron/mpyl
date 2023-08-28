from src.mpyl.utilities.s3 import S3Client


class TestS3:
    def test_create_dst_path_succeeds(self):
        bucket_path1 = S3Client.create_file_dst(
            root_path="root",
            file_path="/tmp/asVx3sd/static",
            filename="filename.js",
            root_asset_location="static",
        )
        bucket_path2 = S3Client.create_file_dst(
            root_path="root",
            file_path="/tmp/asVx3sd/static/js",
            filename="filename.js",
            root_asset_location="static",
        )
        bucket_path3 = S3Client.create_file_dst(
            root_path="root",
            file_path="/tmp/asVx3sd/static/css",
            filename="filename.css",
            root_asset_location="static",
        )
        bucket_path4 = S3Client.create_file_dst(
            root_path="root",
            file_path="/tmp/asVx3sd/static/assets",
            filename="filename.jpg",
            root_asset_location="static",
        )
        bucket_path5 = S3Client.create_file_dst(
            root_path="root",
            file_path="/tmp/asVx3sd/static/assets/docs",
            filename="filename.pdf",
            root_asset_location="static",
        )

        assert bucket_path1 == "root/static/filename.js"
        assert bucket_path2 == "root/static/js/filename.js"
        assert bucket_path3 == "root/static/css/filename.css"
        assert bucket_path4 == "root/static/assets/filename.jpg"
        assert bucket_path5 == "root/static/assets/docs/filename.pdf"
