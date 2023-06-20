from mpyl.utilities.s3 import S3Client


class TestS3:
    def test_create_dst_path_succeeds(self):
        bucket_path1 = S3Client.create_file_dst(root_path='root', file_path='/tmp/asVx3sd/', filename='filename.js')
        bucket_path2 = S3Client.create_file_dst(root_path='root', file_path='/tmp/asVx3sd/js', filename='filename.js')
        bucket_path3 = S3Client.create_file_dst(root_path='root', file_path='/tmp/asVx3sd/css', filename='filename.css')
        bucket_path4 = S3Client.create_file_dst(root_path='root', file_path='/tmp/asVx3sd/assets',
                                                filename='filename.jpg')
        bucket_path5 = S3Client.create_file_dst(root_path='root', file_path='/tmp/asVx3sd/assets/docs',
                                                filename='filename.pdf')

        assert bucket_path1 == 'root/filename.js'
        assert bucket_path2 == 'root/js/filename.js'
        assert bucket_path3 == 'root/css/filename.css'
        assert bucket_path4 == 'root/assets/filename.jpg'
        assert bucket_path5 == 'root/assets/docs/filename.pdf'
